import requests
import yaml
import re
import argparse
from bs4 import BeautifulSoup

# Colors for terminal output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
LIGHT_BLUE = '\033[0;36m'
NC = '\033[0m'  # No color

# Load the configuration file
with open('headers_config.yml', 'r') as config_file:
    config = yaml.safe_load(config_file)

if not config:
    print("Error: Configuration file is empty or not loaded properly.")
    exit()

# Grading variables
total_passes = 0
total_fails = 0

# Function to get the HTML content from securityheaders.com
def fetch_headers_report(target_site):
    url = f"https://securityheaders.com/?q={target_site}&hide=on&followRedirects=on"
    response = requests.get(url)
    return response.text

# Function to extract warnings from HTML response
def extract_warnings(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    warnings = {}

    warning_section = soup.find('div', class_='reportTitle', string='Warnings')
    if warning_section:
        warning_body = warning_section.find_next('div', class_='reportBody')
        rows = warning_body.find_all('tr', class_='tableRow')
        for row in rows:
            header_name = row.find('th', class_='tableLabel').text.strip()
            warning_message = row.find('td', class_='tableCell').text.strip()
            warnings[header_name] = warning_message
    return warnings

# Function to check headers (both security and unwanted headers)
def check_headers(headers, warnings, html_content, header_type="security"):
    global total_passes, total_fails
    soup = BeautifulSoup(html_content, 'html.parser')

    for header in headers:
        header_name = header['name']
        expected_condition = header['condition']
        header_found = soup.find(string=re.compile(f"{header_name}", re.IGNORECASE))
        condition = "present" if header_found else "not_present"

        if condition == expected_condition:
            # Check for warnings and treat them as FAIL
            if header_name in warnings:
                warning_message = warnings[header_name]
                print(f"{header_name}: {YELLOW}WARNING{NC} ({warning_message})")
                total_fails += 1  # Treat warning as a failure
            else:
                print(f"{header_name}: {GREEN}PASS{NC}")
                total_passes += 1
        else:
            print(f"{header_name}: {RED}FAIL{NC}")
            total_fails += 1

# Function to handle upcoming headers (only mention them, no checks)
def mention_upcoming_headers():
    for header in config['upcoming_headers']:
        header_name = header['name']
        # We only mention the upcoming headers
        print(f"{LIGHT_BLUE}{header_name}{NC}: {LIGHT_BLUE}PASS{NC} (Upcoming header)")

# Function to calculate and display the final grade
def calculate_final_grade():
    global total_passes, total_fails
    # Total number of headers considered (security + unwanted) is 17
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
        grade = "-C"
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

# Main function
def main():
    # Set up argument parser to accept the target site URL as a command-line argument
    parser = argparse.ArgumentParser(description='Check security headers and grade the target site.')
    parser.add_argument('target_site', type=str, nargs='?', help='The target site URL (e.g., https://example.com)')
    args = parser.parse_args()

    # Check if target site is provided as command-line argument; if not, enter interactive mode
    if args.target_site:
        target_site = args.target_site
    else:
        target_site = input("Enter the target site URL (e.g., https://example.com): ")

    # Fetch HTML report for the provided target site
    html_content = fetch_headers_report(target_site)

    # Extract warnings from the HTML response
    warnings = extract_warnings(html_content)

    # Check security headers
    print("\nSecurity Headers:")
    check_headers(config['headers'], warnings, html_content, "security")

    # Check unwanted headers
    print("\nHeaders That Should Be Removed:")
    check_headers(config['unwanted_headers'], warnings, html_content, "unwanted")

    # Mention upcoming headers
    print("\nUpcoming Headers:")
    mention_upcoming_headers()

    # Calculate and print the final grade
    calculate_final_grade()

if __name__ == "__main__":
    main()
