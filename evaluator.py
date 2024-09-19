#!/usr/bin/env python3

import asyncio
import aiohttp
import argparse
import logging
import sqlite3
import sys
import yaml
import requests
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
from tabulate import tabulate
from tqdm import tqdm
import os
import textwrap
import datetime  # Added to handle timestamps

# Initialize colorama for cross-platform color support
init(autoreset=True)

# Determine the directory where the script resides
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# Define paths for configuration, database, and log files relative to SCRIPT_DIR
CONFIG_PATH_DEFAULT = os.path.join(SCRIPT_DIR, 'headers_config.yml')
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'results.db')
LOG_FILE_PATH = os.path.join(SCRIPT_DIR, 'app.log')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)

# Define color constants using colorama
RED = Fore.RED
GREEN = Fore.GREEN
YELLOW = Fore.YELLOW
LIGHT_BLUE = Fore.CYAN
NC = Style.RESET_ALL  # No color

# Initialize SQLite database and create table if it doesn't exist
def init_db():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Create the results table with an additional 'timestamp' column
        cursor.execute('''CREATE TABLE IF NOT EXISTS results (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            url TEXT NOT NULL,
                            score REAL,
                            grade TEXT,
                            header_name TEXT,
                            status TEXT,
                            header_value TEXT,
                            timestamp TEXT  -- Added timestamp column
                         )''')
        
        # Optional: Create an index on the 'url' column to optimize DELETE operations
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON results (url)')

        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        sys.exit(1)

# Function to store results in the SQLite database
def store_results_in_db(url, score, grade, results_list):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Capture the current timestamp
        current_timestamp = datetime.datetime.now().isoformat()

        # Delete existing entries for the URL to keep only the latest results
        cursor.execute('DELETE FROM results WHERE url = ?', (url,))
        logging.info(f"Deleted previous entries for {url} from the database.")

        # Insert new results
        for result in results_list:
            cursor.execute('''INSERT INTO results (url, score, grade, header_name, status, header_value, timestamp) 
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                           (url, score, grade, result[0], result[1], result[2], current_timestamp))  # Included timestamp

        conn.commit()
        conn.close()
        logging.info(f"New results stored in database for {url}.")
    except sqlite3.Error as e:
        logging.error(f"Database error while storing results for {url}: {e}")

# Function to load configuration file
def load_config(config_path):
    try:
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
        if not config:
            logging.error("Error: Configuration file is empty or not loaded properly.")
            sys.exit(1)
        logging.info(f"Configuration loaded from {config_path}.")
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file {config_path} not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {config_path}: {e}")
        sys.exit(1)

# Function to get the headers of a website (synchronous)
def fetch_headers_report_sync(target_site):
    try:
        response = requests.head(target_site, allow_redirects=True, timeout=10)
        logging.info(f"Fetched headers for {target_site}.")
        return response.headers
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while fetching headers for {target_site}: {e}")
        return None

# Async function to get the headers of a website
async def fetch_headers_report_async(session, target_site):
    try:
        async with session.head(target_site, allow_redirects=True, timeout=10) as response:
            headers = response.headers
            logging.info(f"Fetched headers for {target_site}.")
            return headers
    except Exception as e:
        logging.error(f"An error occurred while fetching headers for {target_site}: {e}")
        return None

# Function to get the HTML content from securityheaders.com for warnings (synchronous)
def fetch_securityheaders_warnings_sync(target_site):
    try:
        url = f"https://securityheaders.com/?q={target_site}&hide=on&followRedirects=on"
        response = requests.get(url, timeout=10)
        logging.info(f"Fetched security headers warnings for {target_site}.")
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while fetching security headers warnings for {target_site}: {e}")
        return None

# Async function to get the HTML content from securityheaders.com for warnings
async def fetch_securityheaders_warnings_async(session, target_site):
    try:
        url = f"https://securityheaders.com/?q={target_site}&hide=on&followRedirects=on"
        async with session.get(url, timeout=10) as response:
            html_content = await response.text()
            logging.info(f"Fetched security headers warnings for {target_site}.")
            return html_content
    except Exception as e:
        logging.error(f"An error occurred while fetching security headers warnings for {target_site}: {e}")
        return None

# Function to extract warnings from HTML response
def extract_warnings(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    warnings = {}

    warning_section = soup.find('div', class_='reportTitle', string='Warnings')
    if warning_section:
        warning_body = warning_section.find_next('div', class_='reportBody')
        if warning_body:
            rows = warning_body.find_all('tr', class_='tableRow')
            for row in rows:
                header_name_tag = row.find('th', class_='tableLabel')
                warning_message_tag = row.find('td', class_='tableCell')
                if header_name_tag and warning_message_tag:
                    header_name = header_name_tag.text.strip()
                    warning_message = warning_message_tag.text.strip()
                    warnings[header_name] = warning_message
    return warnings

# Function to print all headers in a key-value list format with optional truncation
def print_headers_list(headers, show_full=False, max_length=100):
    if not headers:
        logging.warning("No headers to display.")
        return

    print("\nHeaders Returned by the Site:\n")
    for header, value in headers.items():
        if not show_full and len(value) > max_length:
            display_value = value[:max_length] + "..."
        else:
            display_value = value
        print(f"{header}: {display_value}")
    print()  # Add an extra newline for better readability

# Function to check security headers (headers that should be present)
def check_headers(headers, warnings, response_headers, header_type="security"):
    total_passes = 0
    total_fails = 0
    results = []

    for header in headers:
        header_name = header['name']
        expected_condition = header.get('condition', 'present')  # Default to 'present' if not specified
        header_found = response_headers.get(header_name)

        condition = "present" if header_found else "not_present"

        if header_name in warnings:
            warning_message = warnings[header_name]
            results.append([header_name, f"WARNING ({warning_message})", header_found])
            print(f"{header_name}: {YELLOW}WARNING{NC} ({warning_message})")
            total_fails += 1  # Treat warning as a failure
        elif condition == expected_condition:
            results.append([header_name, "PASS", header_found])
            print(f"{header_name}: {GREEN}PASS{NC}")
            total_passes += 1
        else:
            results.append([header_name, "FAIL", header_found])
            print(f"{header_name}: {RED}FAIL{NC}")
            total_fails += 1

    return results, total_passes, total_fails

# Function to check unwanted headers (headers that should NOT be present)
def check_unwanted_headers(headers, response_headers):
    total_passes = 0
    total_fails = 0
    results = []

    for header in headers:
        header_name = header['name']
        header_found = response_headers.get(header_name)

        condition = "present" if header_found else "not_present"

        if condition == "present":
            results.append([header_name, "FAIL (present)", header_found])
            print(f"{header_name}: {RED}FAIL{NC} (present)")
            total_fails += 1
        else:
            results.append([header_name, "PASS (not present)", header_found])
            print(f"{header_name}: {GREEN}PASS{NC} (not present)")
            total_passes += 1

    return results, total_passes, total_fails

# Function to handle upcoming headers (only mention them, no checks)
def mention_upcoming_headers(upcoming_headers):
    results = []
    for header in upcoming_headers:
        header_name = header['name']
        results.append([header_name, "PASS (Upcoming header)", "N/A"])
        print(f"{LIGHT_BLUE}{header_name}{NC}: {LIGHT_BLUE}PASS (Upcoming header){NC}")
    return results

# Function to calculate and display the final grade
def calculate_final_grade(total_passes, total_fails):
    score = (100 / 17) * (total_passes - total_fails)

    # Determine the grade based on the score
    if -100 <= score <= -88.89:
        grade = "F-"
    elif -88.89 < score <= -77.78:
        grade = "F"
    elif -77.78 < score <= -66.67:
        grade = "F+"
    elif -66.67 < score <= -55.56:
        grade = "E-"
    elif -55.56 < score <= -44.45:
        grade = "E"
    elif -44.45 < score <= -33.34:
        grade = "E+"
    elif -33.34 < score <= -22.23:
        grade = "D-"
    elif -22.23 < score <= -11.12:
        grade = "D"
    elif -11.12 < score <= -0.01:
        grade = "D+"
    elif 0 < score <= 11.11:
        grade = "C-"
    elif 11.11 < score <= 22.22:
        grade = "C"
    elif 22.22 < score <= 33.33:
        grade = "C+"
    elif 33.33 < score <= 44.44:
        grade = "B-"
    elif 44.44 < score <= 55.55:
        grade = "B"
    elif 55.55 < score <= 66.66:
        grade = "B+"
    elif 66.66 < score <= 77.77:
        grade = "A-"
    elif 77.77 < score <= 88.88:
        grade = "A"
    elif 88.88 < score <= 100:
        grade = "A+"
    else:
        grade = "Not available"

    print(f"\nFinal Score: {score:.2f}")
    print(f"Grade: {grade}")

    return score, grade

# Function to process a single URL (synchronous)
def process_single_url(target_site, config, show_full_headers=False):
    total_passes = 0
    total_fails = 0

    # Fetch headers for the provided target site
    response_headers = fetch_headers_report_sync(target_site)
    if not response_headers:
        logging.error(f"Skipping {target_site} due to failed header fetch.")
        return None, None, []

    # Fetch warnings from securityheaders.com
    html_content = fetch_securityheaders_warnings_sync(target_site)
    warnings = extract_warnings(html_content) if html_content else {}

    # Print the headers in a list format
    print_headers_list(response_headers, show_full=show_full_headers)

    # Check security headers
    print("\nSecurity Headers (Fail if not present):")
    security_results, sec_pass, sec_fail = check_headers(config['headers'], warnings, response_headers, "security")
    total_passes += sec_pass
    total_fails += sec_fail

    # Check unwanted headers
    print("\nHeaders That Should Be Removed (Fail if present):")
    unwanted_results, unw_pass, unw_fail = check_unwanted_headers(config['unwanted_headers'], response_headers)
    total_passes += unw_pass
    total_fails += unw_fail

    # Mention upcoming headers
    print("\nUpcoming Headers:")
    upcoming_results = mention_upcoming_headers(config.get('upcoming_headers', []))

    # Calculate and print the final grade
    score, grade = calculate_final_grade(total_passes, total_fails)

    # Store results in the database
    store_results_in_db(target_site, score, grade, security_results + unwanted_results + upcoming_results)

    return score, grade, security_results + unwanted_results + upcoming_results

# Async function to process a single URL
async def process_single_url_async(session, target_site, config, show_full_headers=False):
    total_passes = 0
    total_fails = 0

    # Fetch headers
    response_headers = await fetch_headers_report_async(session, target_site)
    if not response_headers:
        logging.error(f"Skipping {target_site} due to failed header fetch.")
        return None, None, []

    # Fetch warnings
    html_content = await fetch_securityheaders_warnings_async(session, target_site)
    warnings = extract_warnings(html_content) if html_content else {}

    # Print headers list
    print_headers_list(response_headers, show_full=show_full_headers)

    # Check security headers
    print("\nSecurity Headers (Fail if not present):")
    security_results, sec_pass, sec_fail = check_headers(config['headers'], warnings, response_headers, "security")
    total_passes += sec_pass
    total_fails += sec_fail

    # Check unwanted headers
    print("\nHeaders That Should Be Removed (Fail if present):")
    unwanted_results, unw_pass, unw_fail = check_unwanted_headers(config['unwanted_headers'], response_headers)
    total_passes += unw_pass
    total_fails += unw_fail

    # Mention upcoming headers
    print("\nUpcoming Headers:")
    upcoming_results = mention_upcoming_headers(config.get('upcoming_headers', []))

    # Calculate final grade
    score, grade = calculate_final_grade(total_passes, total_fails)

    # Store results in DB
    store_results_in_db(target_site, score, grade, security_results + unwanted_results + upcoming_results)

    return score, grade, security_results + unwanted_results + upcoming_results

# Function to process multiple URLs from a text file and save to database (asynchronous)
async def process_bulk_urls(urls_file, config, show_full_headers=False):
    try:
        with open(urls_file, 'r') as file:
            urls = [url.strip() for url in file if url.strip()]
        logging.info(f"Loaded {len(urls)} URLs from {urls_file}.")
    except FileNotFoundError:
        logging.error(f"URLs file {urls_file} not found.")
        return

    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
            tasks.append(process_single_url_async(session, url, config, show_full_headers))

        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing URLs"):
            await f

# Main function
def main():
    init_db()  # Initialize the SQLite database

    # Set up argument parser to accept the target site URL or bulk file input as a command-line argument
    parser = argparse.ArgumentParser(description='Check security headers and grade the target site.')
    parser.add_argument('--target_site', type=str, help='The target site URL (e.g., https://example.com)')
    parser.add_argument('--bulk', type=str, help='Path to a text file containing a list of URLs for bulk processing')
    parser.add_argument('--config', type=str, default=CONFIG_PATH_DEFAULT, help='Path to the headers configuration YAML file')
    parser.add_argument('--show_full_headers', action='store_true', help='Display full header values without truncation')
    args = parser.parse_args()

    config = load_config(args.config)

    if args.bulk:
        # Run the asynchronous bulk processing
        asyncio.run(process_bulk_urls(args.bulk, config, show_full_headers=args.show_full_headers))
    elif args.target_site:
        # Process a single URL synchronously
        process_single_url(args.target_site, config, show_full_headers=args.show_full_headers)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
