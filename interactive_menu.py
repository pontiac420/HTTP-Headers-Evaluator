#!/usr/bin/env python3

import sqlite3
import sys
import os
from tabulate import tabulate
import urllib.parse
import colorama
from colorama import Fore, Style, init  
import subprocess

# Define the path to the SQLite database
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'results.db')

# Define color constants for better readability
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    LIGHT_BLUE = Fore.CYAN
    NC = Style.RESET_ALL  # No color
except ImportError:
    # If colorama is not installed, define color codes as empty strings
    RED = GREEN = YELLOW = LIGHT_BLUE = NC = ''

def connect_db():
    if not os.path.exists(DATABASE_PATH):
        print(f"{RED}Error: Database file {DATABASE_PATH} does not exist.{NC}")
        sys.exit(1)
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        return conn
    except sqlite3.Error as e:
        print(f"{RED}Database connection error: {e}{NC}")
        sys.exit(1)

def search_by_grade(conn):
    grade = input("Enter the grade to search (e.g., A, B, C): ").strip().upper()
    if not grade:
        print(f"{RED}Grade cannot be empty.{NC}")
        return
    cursor = conn.cursor()
    query = '''
        SELECT DISTINCT url, AVG(score) as avg_score, grade 
        FROM results 
        WHERE grade = ?
        GROUP BY url
    '''
    cursor.execute(query, (grade,))
    rows = cursor.fetchall()
    if not rows:
        print(f"{YELLOW}No URLs found with grade: {grade}{NC}")
        return
    headers = ["URL", "Average Score", "Grade"]
    print(f"\nURLs with Grade: {grade}\n")
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print()

def list_all_results(conn):
    cursor = conn.cursor()
    query = '''
        SELECT DISTINCT url, AVG(score) as avg_score, grade 
        FROM results
        GROUP BY url
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    if not rows:
        print(f"{YELLOW}No results available in the database.{NC}")
        return
    headers = ["URL", "Average Score", "Grade"]
    print("\nAll Results:\n")
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print()
    # Calculate cumulative percentages
    cursor.execute('SELECT COUNT(DISTINCT url) FROM results')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT grade, COUNT(DISTINCT url) FROM results GROUP BY grade')
    grade_counts = cursor.fetchall()
    print("Grade Distribution:")
    grade_distribution = [(grade, count, f"{(count/total)*100:.2f}%") for grade, count in grade_counts]
    print(tabulate(grade_distribution, headers=["Grade", "Count", "Percentage"], tablefmt="grid"))
    print()

def best_worst_headers_overall(conn):
    cursor = conn.cursor()
    
    # Define the maximum number of headers to display in each category
    MAX_N = 15
    
    # Fetch all unique headers
    cursor.execute('SELECT DISTINCT header_name FROM results WHERE status IN ("PASS", "PASS (not present)", "FAIL", "FAIL (present)", "WARNING")')
    all_headers = [row[0] for row in cursor.fetchall()]
    
    # Initialize dictionaries to count PASS and FAIL/WARNING for each header
    pass_counts = {header: 0 for header in all_headers}
    fail_warning_counts = {header: 0 for header in all_headers}
    
    # Count PASS, FAIL, and WARNING statuses for each header
    cursor.execute('''
        SELECT header_name, status, COUNT(*) 
        FROM results 
        WHERE status IN ('PASS', 'PASS (not present)', 'FAIL', 'FAIL (present)', 'WARNING')
        GROUP BY header_name, status
    ''')
    for header_name, status, count in cursor.fetchall():
        if status in ['PASS', 'PASS (not present)']:
            pass_counts[header_name] += count
        elif status in ['FAIL', 'FAIL (present)', 'WARNING']:
            fail_warning_counts[header_name] += count
    
    # Calculate ratio and create a list of tuples (header, ratio, pass_count, fail_warning_count)
    header_ratios = []
    for header in all_headers:
        pass_count = pass_counts[header]
        fail_warning_count = fail_warning_counts[header]
        total_count = pass_count + fail_warning_count
        if total_count > 0:
            ratio = pass_count / total_count
        else:
            ratio = 0
        header_ratios.append((header, ratio, pass_count, fail_warning_count))
    
    # Sort headers by ratio (descending for best, ascending for worst)
    sorted_headers = sorted(header_ratios, key=lambda x: x[1], reverse=True)
    
    # Determine how many headers to show in each category
    n_to_show = min(MAX_N, len(sorted_headers) // 2)
    
    # Split into best and worst performing
    best_headers = sorted_headers[:n_to_show]
    worst_headers = sorted_headers[-n_to_show:]  # Take from the end
    
    print(f"\n{LIGHT_BLUE}Best Performing Headers (Top {n_to_show}):{NC}\n")
    if best_headers:
        best_data = [(header, f"{ratio:.2%}", pass_count, fail_warning_count) for header, ratio, pass_count, fail_warning_count in best_headers]
        print(tabulate(best_data, headers=["Header Name", "Pass Ratio", "Pass Count", "Fail/Warning Count"], tablefmt="grid"))
    else:
        print(f"{YELLOW}No header data found.{NC}")
    
    print(f"\n{LIGHT_BLUE}Worst Performing Headers (Bottom {n_to_show}):{NC}\n")
    if worst_headers:
        worst_data = [(header, f"{ratio:.2%}", pass_count, fail_warning_count) for header, ratio, pass_count, fail_warning_count in worst_headers]  # Remove [::-1]
        print(tabulate(worst_data, headers=["Header Name", "Pass Ratio", "Pass Count", "Fail/Warning Count"], tablefmt="grid"))
    else:
        print(f"{YELLOW}No header data found.{NC}")
    
    if len(sorted_headers) <= MAX_N:
        print(f"\n{YELLOW}Note: Only {len(sorted_headers)} unique header(s) found in the database.{NC}")
    
    print()

def best_worst_urls(conn):
    cursor = conn.cursor()
    
    # Define the maximum number of URLs to display in each category
    MAX_N = 15
    
    # Fetch all unique URLs with their grades and scores
    cursor.execute('''
        SELECT DISTINCT url, score, grade 
        FROM results 
        ORDER BY score DESC
    ''')
    all_urls = cursor.fetchall()
    
    total_urls = len(all_urls)
    
    # Determine how many URLs to show in each category
    n_to_show = min(MAX_N, total_urls // 2)
    
    # Split into best and worst performing
    best_urls = all_urls[:n_to_show]
    worst_urls = all_urls[-n_to_show:]  # No need to reverse here
    
    print(f"\nBest Performing URLs (Top {n_to_show}):\n")
    if best_urls:
        print(tabulate(best_urls, headers=["URL", "Score", "Grade"], tablefmt="grid"))
    else:
        print(f"{YELLOW}No records found.{NC}")
    
    print(f"\nWorst Performing URLs (Bottom {n_to_show}):\n")
    if worst_urls:
        print(tabulate(worst_urls, headers=["URL", "Score", "Grade"], tablefmt="grid"))
    else:
        print(f"{YELLOW}No records found.{NC}")
    
    if total_urls <= MAX_N:
        print(f"\n{YELLOW}Note: Only {total_urls} unique URL(s) found in the database.{NC}")
    
    print()

def overall_header_health(conn):
    def get_grade(score):
        grade_ranges = [
            (-100, -88.89, "F-"), (-88.89, -77.78, "F"), (-77.78, -66.67, "F+"),
            (-66.67, -55.56, "E-"), (-55.56, -44.45, "E"), (-44.45, -33.34, "E+"),
            (-33.34, -22.23, "D-"), (-22.23, -11.12, "D"), (-11.12, -0.01, "D+"),
            (0, 11.11, "C-"), (11.11, 22.22, "C"), (22.22, 33.33, "C+"),
            (33.33, 44.44, "B-"), (44.44, 55.55, "B"), (55.55, 66.66, "B+"),
            (66.66, 77.77, "A-"), (77.77, 88.88, "A"), (88.88, 100, "A+")
        ]
        
        for low, high, grade in grade_ranges:
            if low <= score <= high:
                return grade
        return "Not available"

    domain_input = input("Enter the domain (e.g., example.com): ").strip().lower()
    if not domain_input:
        print(f"{RED}Domain cannot be empty.{NC}")
        return
    
    cursor = conn.cursor()
    
    # Use wildcard matching for subdomains and ensure distinct URLs
    query = '''
        SELECT DISTINCT url, score, grade 
        FROM results 
        WHERE url LIKE ?
    '''
    like_pattern = f"%{domain_input}"
    cursor.execute(query, (like_pattern,))
    rows = cursor.fetchall()
    if not rows:
        print(f"{YELLOW}No results found for domain: {domain_input}{NC}")
        return
    
    headers = ["URL", "Score", "Grade"]
    print(f"\nHeader Health for Domain: {domain_input}\n")
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print()
    
    # Calculate grade distribution
    cursor.execute('''
        SELECT grade, COUNT(DISTINCT url) 
        FROM results 
        WHERE url LIKE ? 
        GROUP BY grade
    ''', (like_pattern,))
    grade_counts = cursor.fetchall()
    total = sum(count for _, count in grade_counts)
    grade_distribution = [(grade, count, f"{(count/total)*100:.2f}%") for grade, count in grade_counts]
    print("Grade Distribution:")
    print(tabulate(grade_distribution, headers=["Grade", "Count", "Percentage"], tablefmt="grid"))
    print()
    
    # Calculate average score
    cursor.execute('''
        SELECT AVG(score) 
        FROM results 
        WHERE url LIKE ?
    ''', (like_pattern,))
    average_score = cursor.fetchone()[0]
    
    if average_score is not None:
        average_grade = get_grade(average_score)
        print(f"Average Score for Domain: {average_score:.2f}")
        print(f"Average Grade for Domain: {average_grade}")
    else:
        print(f"{YELLOW}No scores available to calculate average.{NC}")
    
    print()

def run_evaluator(conn):
    print("\nRun Evaluator:")
    print("1. Single URL")
    print("2. List of URLs")
    choice = input("Enter your choice (1 or 2): ")

    if choice == '1':
        url = input("Enter the URL (e.g., example.com or https://example.com): ").strip()
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        command = ['python3', 'evaluator.py', '--target_site', url]
    elif choice == '2':
        file_path = input("Enter the path to the file containing URLs: ").strip()
        if not os.path.exists(file_path):
            print(f"{RED}File not found: {file_path}{NC}")
            return
        
        command = ['python3', 'evaluator.py', '--bulk', file_path]
    else:
        print(f"{RED}Invalid choice. Please enter 1 or 2.{NC}")
        return

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error running evaluator.py: {e}{NC}")
    except FileNotFoundError:
        print(f"{RED}Error: evaluator.py not found in the current directory.{NC}")

def display_menu():
    menu_options = [
        "1. Search by Grade",
        "2. List all results",
        "3. Show best and worst performing headers overall",
        "4. Show best and worst performing URLs",
        "5. Show the overall header health of a domain",
        "6. Run Evaluator",
        "7. Exit"
    ]
    print("\n" + "="*50)
    print("Web Security Header Analysis Menu")
    print("="*50)
    for option in menu_options:
        print(option)
    print("="*50)

def clear_screen():
    # Clear the terminal screen
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    conn = connect_db()
    while True:
        clear_screen()
        display_menu()
        choice = input("Enter your choice (1-7): ").strip()
        
        if choice == '1':
            search_by_grade(conn)
        elif choice == '2':
            list_all_results(conn)
        elif choice == '3':
            best_worst_headers_overall(conn)
        elif choice == '4':
            best_worst_urls(conn)
        elif choice == '5':
            overall_header_health(conn)
        elif choice == '6':
            run_evaluator(conn)
        elif choice == '7':
            print("Exiting the program. Goodbye!")
            conn.close()
            sys.exit(0)
        else:
            print(f"{RED}Invalid choice. Please enter a number between 1 and 7.{NC}")
        
        # Prompt user to continue after every option
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
