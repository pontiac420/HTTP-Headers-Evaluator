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
import ssl
from requests.exceptions import RequestException
from urllib.parse import urlparse

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

        # Calculate the timestamp for 90 days ago
        ninety_days_ago = (datetime.datetime.now() - datetime.timedelta(days=90)).isoformat()

        # Delete entries older than 90 days for the URL
        cursor.execute('DELETE FROM results WHERE url = ? AND timestamp < ?', (url, ninety_days_ago))
        logging.info(f"Deleted entries older than 90 days for {url} from the database.")

        # Insert new results
        for result in results_list:
            cursor.execute('''INSERT INTO results (url, score, grade, header_name, status, header_value, timestamp) 
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                           (url, score, grade, result[0], result[1], result[2], current_timestamp))

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
def fetch_headers_report_sync(target_site, ssl_context=None):
    try:
        with requests.Session() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = session.get(target_site, headers=headers, allow_redirects=True, timeout=10, stream=True)
            # Using stream=True to avoid downloading the entire content
            response.close()  # Close the connection immediately after getting headers
        logging.info(f"Fetched headers for {target_site}.")
        return response.headers
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while fetching headers for {target_site}: {e}")
        return None

# Async function to get the headers of a website
async def fetch_headers_report_async(session, target_site, ssl_context=None):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        async with session.get(target_site, headers=headers, allow_redirects=True, timeout=10, ssl=False) as response:
            # Read only the headers, not the body
            await response.start()
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

# Function to calculate and display the final grade
def calculate_final_grade(total_passes, total_headers):
    score = (total_passes / total_headers) * 100  # Calculate percentage

    # Determine the grade based on the score
    if 0 <= score < 20:
        grade = "F"
    elif 20 <= score < 30:
        grade = "E"
    elif 30 <= score < 40:
        grade = "D-"
    elif 40 <= score < 50:
        grade = "D"
    elif 50 <= score < 60:
        grade = "D+"
    elif 60 <= score < 65:
        grade = "C-"
    elif 65 <= score < 70:
        grade = "C"
    elif 70 <= score < 75:
        grade = "C+"
    elif 75 <= score < 80:
        grade = "B-"
    elif 80 <= score < 85:
        grade = "B"
    elif 85 <= score < 90:
        grade = "B+"
    elif 90 <= score < 95:
        grade = "A-"
    elif 95 <= score < 98:
        grade = "A"
    elif 98 <= score <= 100:
        grade = "A+"
    else:
        grade = "Not available"

    print(f"\nFinal Score: {score:.2f}%")
    print(f"Grade: {grade}")

    return score, grade

# Function to process a single URL (synchronous)
def process_single_url(target_site, config, show_full_headers=False, ssl_context=None):
    # Initialize counters
    total_headers = 0
    total_passes = 0

    # Fetch headers for the provided target site
    response_headers = fetch_headers_report_sync(target_site, ssl_context=ssl_context)
    if not response_headers:
        logging.error(f"Skipping {target_site} due to failed header fetch.")
        return None, None, []

    # Fetch warnings from securityheaders.com
    html_content = fetch_securityheaders_warnings_sync(target_site)
    warnings = extract_warnings(html_content) if html_content else {}

    # Print the headers in a list format
    print_headers_list(response_headers, show_full=show_full_headers)

    # Check security headers
    print("\nSecurity Headers:")
    security_results, sec_pass, sec_fail = check_headers(config['headers'], warnings, response_headers, "security")
    total_headers += len(config['headers'])
    total_passes += sec_pass

    # Check unwanted headers
    print("\nHeaders That Should Be Removed:")
    unwanted_results, unw_pass, unw_fail = check_unwanted_headers(config['unwanted_headers'], response_headers)
    total_headers += len(config['unwanted_headers'])
    total_passes += unw_pass

    # Check upcoming headers
    print("\nUpcoming Headers:")
    upcoming_results, up_pass, up_fail = check_headers(config.get('upcoming_headers', []), warnings, response_headers, "upcoming")
    total_headers += len(config.get('upcoming_headers', []))
    total_passes += up_pass

    # Calculate and print the final grade
    score, grade = calculate_final_grade(total_passes, total_headers)

    # Store results in the database
    store_results_in_db(target_site, score, grade, security_results + unwanted_results + upcoming_results)

    return score, grade, security_results + unwanted_results + upcoming_results

# Async function to process a single URL
async def process_single_url_async(session, target_site, config, show_full_headers=False, ssl_context=None):
    # Initialize counters
    total_headers = 0
    total_passes = 0

    # Fetch headers
    response_headers = await fetch_headers_report_async(session, target_site, ssl_context=ssl_context)
    if not response_headers:
        logging.error(f"Skipping {target_site} due to failed header fetch.")
        return None, None, []

    # Fetch warnings
    html_content = await fetch_securityheaders_warnings_async(session, target_site)
    warnings = extract_warnings(html_content) if html_content else {}

    # Print headers list
    print_headers_list(response_headers, show_full=show_full_headers)

    # Check security headers
    print("\nSecurity Headers:")
    security_results, sec_pass, sec_fail = check_headers(config['headers'], warnings, response_headers, "security")
    total_headers += len(config['headers'])
    total_passes += sec_pass

    # Check unwanted headers
    print("\nHeaders That Should Be Removed:")
    unwanted_results, unw_pass, unw_fail = check_unwanted_headers(config['unwanted_headers'], response_headers)
    total_headers += len(config['unwanted_headers'])
    total_passes += unw_pass

    # Check upcoming headers
    print("\nUpcoming Headers:")
    upcoming_results, up_pass, up_fail = check_headers(config.get('upcoming_headers', []), warnings, response_headers, "upcoming")
    total_headers += len(config.get('upcoming_headers', []))
    total_passes += up_pass

    # Calculate final grade
    score, grade = calculate_final_grade(total_passes, total_headers)

    # Store results in DB
    store_results_in_db(target_site, score, grade, security_results + unwanted_results + upcoming_results)

    return score, grade, security_results + unwanted_results + upcoming_results

# Function to determine the correct protocol (HTTP or HTTPS) for a URL
async def determine_protocol(session, url, timeout=10):
    parsed_url = urlparse(url)
    if parsed_url.scheme:
        return url  # URL already has a scheme, return as is

    url = parsed_url.netloc or parsed_url.path  # Use netloc if available, otherwise path
    
    for scheme in ['https', 'http']:
        try:
            async with session.head(f'{scheme}://{url}', timeout=timeout, allow_redirects=True, ssl=False) as response:
                logging.info(f"{scheme.upper()} connection successful for {url}")
                return str(response.url)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logging.warning(f"{scheme.upper()} connection failed for {url}: {e}")
    
    logging.error(f"Both HTTPS and HTTP connections failed for {url}")
    return None

# Function to process multiple URLs from a text file and save to database (asynchronous)
async def process_bulk_urls(urls_file, config, show_full_headers=False, ssl_context=None):
    try:
        with open(urls_file, 'r') as file:
            urls = [url.strip() for url in file if url.strip()]
    except FileNotFoundError:
        logging.error(f"URLs file {urls_file} not found.")
        return None, []

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False),
        timeout=timeout
    ) as session:
        tasks = [determine_protocol(session, url) for url in urls]
        processed_urls = await asyncio.gather(*tasks, return_exceptions=True)
        
        metrics = {
            'total_urls': len(urls),
            'successful_fetches': 0,
            'unsuccessful_fetches': 0,
            'http_urls': 0,
            'https_urls': 0,
            'unreachable_urls': 0
        }
        
        valid_urls = []
        for url in processed_urls:
            if isinstance(url, str):
                valid_urls.append(url)
                if url.startswith('https://'):
                    metrics['https_urls'] += 1
                elif url.startswith('http://'):
                    metrics['http_urls'] += 1
            else:
                metrics['unreachable_urls'] += 1

        logging.info(f"Successfully processed {len(valid_urls)} out of {metrics['total_urls']} URLs from {urls_file}.")

        tasks = [process_single_url_async(session, url, config, show_full_headers, ssl_context) for url in valid_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        detailed_results = []
        for url, result in zip(valid_urls, results):
            if isinstance(result, Exception):
                logging.error(f"Error processing {url}: {result}")
                metrics['unsuccessful_fetches'] += 1
            elif result[0] is not None:
                score, grade, _ = result
                print(f"URL: {url}, Score: {score}, Grade: {grade}")
                detailed_results.append({'URL': url, 'Score': score, 'Grade': grade})
                metrics['successful_fetches'] += 1
            else:
                logging.warning(f"No valid result for {url}")
                metrics['unsuccessful_fetches'] += 1

        # Print final metrics (for CLI output)
        print("\nFinal Metrics:")
        print(f"Total URLs processed: {metrics['total_urls']}")
        print(f"Successful header fetches: {metrics['successful_fetches']}")
        print(f"Unsuccessful header fetches: {metrics['unsuccessful_fetches']}")
        print(f"Total HTTP URLs: {metrics['http_urls']}")
        print(f"Total HTTPS URLs: {metrics['https_urls']}")
        print(f"Unreachable URLs: {metrics['unreachable_urls']}")

        if metrics['unreachable_urls'] > 0:
            print("\nUnreachable URLs:")
            for url, result in zip(urls, processed_urls):
                if not isinstance(result, str):
                    print(f"  - {url}")

        return metrics, detailed_results

# Modify the main function to return the results while still printing for CLI
def main():
    init_db()  # Initialize the SQLite database

    # Set up argument parser to accept the target site URL or bulk file input as a command-line argument
    parser = argparse.ArgumentParser(description='Check security headers and grade the target site.')
    parser.add_argument('--target_site', type=str, help='The target site URL (e.g., https://example.com)')
    parser.add_argument('--bulk', type=str, help='Path to a text file containing a list of URLs for bulk processing')
    parser.add_argument('--config', type=str, default=CONFIG_PATH_DEFAULT, help='Path to the headers configuration YAML file')
    parser.add_argument('--show_full_headers', action='store_true', help='Display full header values without truncation')
    parser.add_argument('--disable-ssl-verify', action='store_true', help='Disable SSL certificate verification (use with caution, for testing only)')
    args = parser.parse_args()

    config = load_config(args.config)

    if args.disable_ssl_verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        ssl_context = False
        logging.warning("SSL verification is disabled. Use this option with caution and only for testing purposes.")
    else:
        ssl_context = None

    # Always disable SSL verification for aiohttp
    aiohttp.ClientSession.ssl = False

    if args.bulk:
        # Run the asynchronous bulk processing and return the results
        metrics, detailed_results = asyncio.run(process_bulk_urls(args.bulk, config, show_full_headers=args.show_full_headers, ssl_context=ssl_context))
        return metrics, detailed_results
    elif args.target_site:
        # Process a single URL synchronously
        score, grade, results = process_single_url(args.target_site, config, show_full_headers=args.show_full_headers, ssl_context=ssl_context)
        return {'score': score, 'grade': grade}, [{'URL': args.target_site, 'Score': score, 'Grade': grade}]
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
else:
    # This allows the script to be imported as a module without running main()
    pass