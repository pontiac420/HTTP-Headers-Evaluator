import requests
import yaml
import argparse
import csv
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

# Function to get the headers of a website
def fetch_headers_report(target_site):
    try:
        # Send a HEAD request to fetch headers
        response = requests.head(target_site, allow_redirects=True)
        return response.headers
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        exit(1)

# Function to get the HTML content from securityheaders.com for warnings
def fetch_securityheaders_warnings(target_site):
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

# Function to print all headers in a list format
def print_headers_list():
    print("\nHeaders Returned by the Site:\n")
    for header, value in response_headers.items():
        print(f"- {header}: {value}")

# Function to check security headers (headers that should be present)
def check_headers(headers, warnings, header_type="security"):
    global total_passes, total_fails
    results = []

    for header in headers:
        header_name = header['name']
        expected_condition = header['condition']
        header_found = response_headers.get(header_name)

        condition = "present" if header_found else "not_present"

        if header_name in warnings:
            warning_message = warnings[header_name]
            results.append([header_name, f"WARNING ({warning_message})", header_found])
            print(f"{header_name}: {YELLOW}WARNING{NC} ({warning_message})")
            total_fails += 1  # Treat warning as a failure
        elif condition == expected_condition:
            results.append([header_name, "PASS", header_found])
            if header_type == "security":
                print(f"{header_name}: {GREEN}PASS{NC}")
            total_passes += 1
        else:
            results.append([header_name, "FAIL", header_found])
            if header_type == "security":
                print(f"{header_name}: {RED}FAIL{NC}")
            total_fails += 1
    return results

# Function to check unwanted headers (headers that should NOT be present)
def check_unwanted_headers(headers):
    global total_passes, total_fails
    results = []

    for header in headers:
        header_name = header['name']
        header_found = response_headers.get(header_name)

        condition = "present" if header_found else "not_present"

        # If the header is present and it shouldn't be, it's a FAIL
        if condition == "present":
            results.append([header_name, "FAIL", header_found])
            print(f"{header_name}: {RED}FAIL{NC} (present)")
            total_fails += 1
        else:
            results.append([header_name, "PASS", header_found])
            print(f"{header_name}: {GREEN}PASS{NC} (not present)")
            total_passes += 1

    return results

# Function to handle upcoming headers (only mention them, no checks)
def mention_upcoming_headers():
    results = []
    for header in config['upcoming_headers']:
        header_name = header['name']
        results.append([header_name, "PASS (Upcoming header)", "N/A"])
        print(f"{LIGHT_BLUE}{header_name}{NC}: {LIGHT_BLUE}PASS (Upcoming header){NC}")
    return results

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

# Function to process a single URL
def process_single_url(target_site):
    global total_passes, total_fails
    total_passes, total_fails = 0, 0

    # Fetch headers for the provided target site
    global response_headers
    response_headers = fetch_headers_report(target_site)

    # Fetch warnings from securityheaders.com
    html_content = fetch_securityheaders_warnings(target_site)
    warnings = extract_warnings(html_content)

    # Print the headers in a list format
    print_headers_list()

    # Check security headers
    print("\nSecurity Headers (Fail if not present):")
    security_results = check_headers(config['headers'], warnings, "security")

    # Check unwanted headers
    print("\nHeaders That Should Be Removed (Fail if present):")
    unwanted_results = check_unwanted_headers(config['unwanted_headers'])

    # Mention upcoming headers
    print("\nUpcoming Headers:")
    upcoming_results = mention_upcoming_headers()

    # Calculate and print the final grade
    score, grade = calculate_final_grade()

    return score, grade, security_results + unwanted_results + upcoming_results

# Function to process multiple URLs from a text file and save to CSV
def process_bulk_urls(urls_file, output_csv):
    results = []

    with open(urls_file, 'r') as file:
        urls = [url.strip() for url in file.readlines()]

    for url in urls:
        score, grade, results_list = process_single_url(url)
        for result in results_list:
            results.append([url, score, grade] + result)

    # Save results to CSV
    with open(output_csv, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["URL", "Score", "Grade", "Header", "Status", "Value"])
        csv_writer.writerows(results)

# Main function
def main():
    # Set up argument parser to accept the target site URL or bulk file input as a command-line argument
    parser = argparse.ArgumentParser(description='Check security headers and grade the target site.')
    parser.add_argument('--target_site', type=str, help='The target site URL (e.g., https://example.com)')
    parser.add_argument('--bulk', type=str, help='Path to a text file containing a list of URLs for bulk processing')
    parser.add_argument('--output_csv', type=str, default="results.csv", help='Path to save the CSV output (default: results.csv)')
    args = parser.parse_args()

    if args.bulk:
        process_bulk_urls(args.bulk, args.output_csv)
    elif args.target_site:
        score, grade, results_list = process_single_url(args.target_site)
    else:
        print("\nPlease provide either --target_site or --bulk argument.\n")
        print("Single URL example:")
        print("python3 evaluate_headers.py --target_site https://example.com\n")
        print("For bulk processing:")
        print("python3 evaluate_headers.py --bulk urls.txt --output_csv results.csv")

if __name__ == "__main__":
    main()
