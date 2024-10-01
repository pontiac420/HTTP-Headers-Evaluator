import sqlite3
import pandas as pd
import plotly.express as px
from tabulate import tabulate
import datetime
import logging
import os
import hashlib

# Database operations
SCRIPT_DIR = os.environ.get('SCRIPT_DIR', os.path.dirname(os.path.realpath(__file__)))
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'results.db')

def connect_to_db():
    return sqlite3.connect(DATABASE_PATH)

def fetch_all_results_for_url(url):
    with connect_to_db() as conn:
        query = """
        WITH latest_scan AS (
            SELECT MAX(timestamp) as max_timestamp
            FROM results
            WHERE url LIKE ? OR url LIKE ? OR url = ?
        )
        SELECT r.*
        FROM results r
        JOIN latest_scan ls
        WHERE (r.url LIKE ? OR r.url LIKE ? OR r.url = ?)
        AND r.timestamp = ls.max_timestamp
        """
        # Prepend http:// and https:// to the search
        params = (f"http://{url}%", f"https://{url}%", url) * 2
        return pd.read_sql_query(query, conn, params=params)

def fetch_recent_scans(limit=50):
    with connect_to_db() as conn:
        df = pd.read_sql_query(f"""
            SELECT url, score, grade, MAX(timestamp) as last_scan_time
            FROM results
            GROUP BY url
            ORDER BY last_scan_time DESC
            LIMIT {limit}
        """, conn)
    return df

# Analysis functions
def generate_url_summary(row):
    url = row['url']
    score = row['score']
    grade = row['grade']
    
    summary = f"Security Analysis for: {url}\n"
    summary += f"Score: {score:.2f}\n"
    summary += f"Grade: {grade}"
    return summary

def interpret_score_and_grade(score, grade):
    interpretation = "Interpretation:\n"
    if grade == 'A+':
        interpretation += "Excellent! Your site has top-notch security headers."
    elif grade in ['A', 'A-']:
        interpretation += "Very good. Your site has strong security headers, with minor room for improvement."
    elif grade.startswith('B'):
        interpretation += "Good, but there's room for improvement in your security headers."
    elif grade.startswith('C'):
        interpretation += "Fair. Several important security headers are missing or misconfigured."
    elif grade.startswith('D'):
        interpretation += "Poor. Many critical security headers are missing. Immediate attention is required."
    else:
        interpretation += "Critical. Your site is missing most or all important security headers."
    
    interpretation += f"\n\nThe score of {score:.2f} indicates the overall security posture based on the implemented headers."
    interpretation += "\nA higher score indicates better header security."
    return interpretation

def generate_headers_report(df):
    # Drop duplicate headers
    df = df[['header_name', 'status', 'header_value']].drop_duplicates()
    headers_table = df.values.tolist()
    return tabulate(headers_table, headers=['Header', 'Status', 'Value'], tablefmt='grid')

def generate_vulnerability_summary(df):
    vulnerabilities = df[df['status'] == 'FAIL']
    # Drop duplicate headers
    unique_vulnerabilities = vulnerabilities['header_name'].drop_duplicates()
    
    summary = "Vulnerabilities (Missing or Failing Headers):\n"
    for header in unique_vulnerabilities:
        summary += f"- {header}\n"
    
    return summary

def analyze_url(url):
    df = fetch_all_results_for_url(url)
    
    if df.empty:
        return f"No data found for URL: {url}"

    summary = generate_url_summary(df.iloc[0])
    interpretation = interpret_score_and_grade(df['score'].iloc[0], df['grade'].iloc[0])
    headers_report = generate_headers_report(df)
    vulnerability_summary = generate_vulnerability_summary(df)

    timestamp = df['timestamp'].iloc[0]
    
    return f"Most recent scan results (as of {timestamp}):\n\n{summary}\n\n{interpretation}\n\n{headers_report}\n\n{vulnerability_summary}"

def generate_overall_summary():
    with connect_to_db() as conn:
        df = pd.read_sql_query("""
            WITH base_urls AS (
                SELECT 
                    CASE 
                        WHEN url LIKE 'http://%' THEN SUBSTR(url, 8)
                        WHEN url LIKE 'https://%' THEN SUBSTR(url, 9)
                        ELSE url
                    END AS base_url,
                    url,
                    timestamp,
                    score,
                    grade
                FROM results
            ),
            latest_scans AS (
                SELECT base_url, MAX(timestamp) as max_timestamp
                FROM base_urls
                GROUP BY base_url
            )
            SELECT DISTINCT bu.base_url, bu.url, bu.score, bu.grade
            FROM base_urls bu
            JOIN latest_scans ls ON bu.base_url = ls.base_url AND bu.timestamp = ls.max_timestamp
        """, conn)
    
    total_urls = len(df)
    average_score = df['score'].mean()
    average_grade = calculate_grade(average_score)
    grade_distribution = df['grade'].value_counts().sort_index(ascending=False)
    
    summary = f"Total unique URLs analyzed: {total_urls}\n"
    summary += f"Average Security Score: {average_score:.2f}\n"
    summary += f"Average Grade: {average_grade}\n\n"
    
    # Create a table for grade distribution
    grade_table = []
    for grade, count in grade_distribution.items():
        percentage = (count / total_urls) * 100
        # Pad the grade to align the letters
        padded_grade = grade.rjust(2) if len(grade) == 1 else grade
        grade_table.append([padded_grade, count, f"{percentage:.2f}%"])
    
    summary += "Grade Distribution:\n"
    summary += tabulate(grade_table, headers=['Grade', 'Count', 'Percentage'], 
                        tablefmt='pretty', colalign=('left', 'right', 'right'))
    
    return summary

def calculate_grade(score):
    if -100 <= score <= -88.89:
        return "F-"
    elif -88.89 < score <= -77.78:
        return "F"
    elif -77.78 < score <= -66.67:
        return "F+"
    elif -66.67 < score <= -55.56:
        return "E-"
    elif -55.56 < score <= -44.45:
        return "E"
    elif -44.45 < score <= -33.34:
        return "E+"
    elif -33.34 < score <= -22.23:
        return "D-"
    elif -22.23 < score <= -11.12:
        return "D"
    elif -11.12 < score <= -0.01:
        return "D+"
    elif 0 < score <= 11.11:
        return "C-"
    elif 11.11 < score <= 22.22:
        return "C"
    elif 22.22 < score <= 33.33:
        return "C+"
    elif 33.33 < score <= 44.44:
        return "B-"
    elif 44.44 < score <= 55.55:
        return "B"
    elif 55.55 < score <= 66.66:
        return "B+"
    elif 66.66 < score <= 77.77:
        return "A-"
    elif 77.77 < score <= 88.88:
        return "A"
    elif 88.88 < score <= 100:
        return "A+"
    else:
        return "Not available"

def analyze_trends(days=30):
    with connect_to_db() as conn:
        df = pd.read_sql_query(f"""
            SELECT DATE(timestamp) as date, AVG(score) as avg_score
            FROM results
            WHERE timestamp >= DATE('now', '-{days} days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, conn)
    return df

def top_vulnerabilities():
    with connect_to_db() as conn:
        df = pd.read_sql_query("""
            SELECT header_name, COUNT(*) as count
            FROM (
                SELECT *
                FROM results
                WHERE timestamp IN (
                    SELECT MAX(timestamp)
                    FROM results
                    GROUP BY url
                )
            ) AS latest_results
            WHERE status LIKE 'FAIL%'
            GROUP BY header_name
            ORDER BY count DESC
            LIMIT 10
        """, conn)
    return df

def urls_requiring_attention():
    with connect_to_db() as conn:
        df = pd.read_sql_query("""
            SELECT url, score, grade
            FROM results
            WHERE grade IN ('F', 'D', 'C')
            GROUP BY url
            HAVING timestamp = MAX(timestamp)
            ORDER BY score ASC
            LIMIT 20
        """, conn)
    return df

def header_adoption_rates():
    with connect_to_db() as conn:
        total_urls = pd.read_sql_query("SELECT COUNT(DISTINCT url) as count FROM results", conn)['count'].iloc[0]
        df = pd.read_sql_query(f"""
            SELECT header_name, 
                   SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / {total_urls} as adoption_rate
            FROM results
            GROUP BY header_name
            ORDER BY adoption_rate DESC
        """, conn)
    return df

def recent_changes(days=30):
    with connect_to_db() as conn:
        df = pd.read_sql_query(f"""
            WITH base_urls AS (
                SELECT 
                    CASE 
                        WHEN url LIKE 'http://%' THEN SUBSTR(url, 8)
                        WHEN url LIKE 'https://%' THEN SUBSTR(url, 9)
                        ELSE url
                    END AS base_url,
                    url,
                    timestamp,
                    score,
                    grade,
                    ROW_NUMBER() OVER (PARTITION BY url ORDER BY timestamp DESC) as rn
                FROM results
                WHERE timestamp >= DATE('now', '-{days} days')
            )
            SELECT 
                new.base_url,
                new.url as new_url,
                new.score as new_score,
                new.grade as new_grade,
                old.url as old_url,
                old.score as old_score,
                old.grade as old_grade
            FROM base_urls new
            LEFT JOIN base_urls old ON new.base_url = old.base_url AND old.rn = 2
            WHERE new.rn = 1 AND (new.grade != old.grade OR old.grade IS NULL)
            ORDER BY (new.score - COALESCE(old.score, new.score)) DESC
        """, conn)
    return df

def generate_overall_summary():
    with connect_to_db() as conn:
        df = pd.read_sql_query("""
            WITH base_urls AS (
                SELECT 
                    CASE 
                        WHEN url LIKE 'http://%' THEN SUBSTR(url, 8)
                        WHEN url LIKE 'https://%' THEN SUBSTR(url, 9)
                        ELSE url
                    END AS base_url,
                    url,
                    timestamp,
                    score,
                    grade
                FROM results
            ),
            latest_scans AS (
                SELECT base_url, MAX(timestamp) as max_timestamp
                FROM base_urls
                GROUP BY base_url
            )
            SELECT DISTINCT bu.base_url, bu.url, bu.score, bu.grade
            FROM base_urls bu
            JOIN latest_scans ls ON bu.base_url = ls.base_url AND bu.timestamp = ls.max_timestamp
        """, conn)
    
    total_urls = len(df)
    average_score = df['score'].mean()
    average_grade = calculate_grade(average_score)
    grade_distribution = df['grade'].value_counts().sort_index(ascending=False)
    
    summary = f"Total unique URLs analyzed: {total_urls}\n"
    summary += f"Average Security Score: {average_score:.2f}\n"
    summary += f"Average Grade: {average_grade}\n\n"
    
    # Create a table for grade distribution
    grade_table = []
    for grade, count in grade_distribution.items():
        percentage = (count / total_urls) * 100
        # Pad the grade to align the letters
        padded_grade = grade.rjust(2) if len(grade) == 1 else grade
        grade_table.append([padded_grade, count, f"{percentage:.2f}%"])
    
    summary += "Grade Distribution:\n"
    summary += tabulate(grade_table, headers=['Grade', 'Count', 'Percentage'], 
                        tablefmt='pretty', colalign=('left', 'right', 'right'))
    
    return summary

def cleanup_old_entries(days=90):
    with connect_to_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM results WHERE timestamp < date('now', '-{days} days')")
        deleted_count = cursor.rowcount
        conn.commit()
    return deleted_count

def delete_url(url):
    with connect_to_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM results WHERE url = ?", (url,))
        deleted_count = cursor.rowcount
        conn.commit()
    return deleted_count

# You can call this function periodically, e.g., once a day
# cleanup_old_entries()

def find_subdomains_with_same_headers():
    with connect_to_db() as conn:
        # Query to get headers and their configurations for each subdomain
        query = """
        WITH base_urls AS (
            SELECT 
                CASE 
                    WHEN url LIKE 'http://%' THEN SUBSTR(url, 8)
                    WHEN url LIKE 'https://%' THEN SUBSTR(url, 9)
                    ELSE url
                END AS base_url,
                url,
                timestamp,
                header_name,
                header_value,
                grade
            FROM results
        ),
        latest_scans AS (
            SELECT base_url, MAX(timestamp) as max_timestamp
            FROM base_urls
            GROUP BY base_url
        )
        SELECT DISTINCT bu.base_url, bu.url, bu.header_name, bu.header_value, bu.grade
        FROM base_urls bu
        JOIN latest_scans ls ON bu.base_url = ls.base_url AND bu.timestamp = ls.max_timestamp
        WHERE bu.url LIKE '%.%'  -- Ensure we are only looking at subdomains
        """
        df = pd.read_sql_query(query, conn)

        # Create a new column for the subdomain (without protocol and path)
        df['subdomain'] = df['url'].str.extract(r'^(?:https?://)?([^/]+)')[0]

        # Get unique URLs
        unique_urls = df['url'].unique()

        # Create a dictionary to hold hashes and their corresponding subdomains and grades
        hash_dict = {}

        for url in unique_urls:
            # Get the headers for the current URL
            headers = df[df['url'] == url][['header_name', 'header_value']]
            # Create a frozenset of header configurations
            header_set = frozenset(zip(headers['header_name'], headers['header_value']))
            # Create a hash of the frozenset
            hash_value = hashlib.md5(str(header_set).encode()).hexdigest()

            # Get the subdomains and grade for the current URL
            subdomains = df[df['url'] == url]['subdomain'].unique()
            grade = df[df['url'] == url]['grade'].iloc[0]  # Assuming the grade is the same for all headers of the same URL

            # Add the subdomain and grade to the hash dictionary
            if hash_value in hash_dict:
                hash_dict[hash_value]['subdomains'].extend(subdomains)
            else:
                hash_dict[hash_value] = {
                    'subdomains': list(subdomains),
                    'grade': grade
                }

        # Convert the hash dictionary to a DataFrame
        result = pd.DataFrame(hash_dict.items(), columns=['Header Configuration Hash', 'Details'])

        # Expand the details into separate columns
        result['Subdomains'] = result['Details'].apply(lambda x: ', '.join(set(x['subdomains'])))
        result['Total Subdomains'] = result['Details'].apply(lambda x: len(set(x['subdomains'])))
        result['Grade'] = result['Details'].apply(lambda x: x['grade'])

        # Drop the 'Details' column as it's no longer needed
        result = result.drop(columns=['Details'])

        # Define a custom ranking for grades
        grade_order = {
            'A+': 1, 'A': 2, 'A-': 3,
            'B+': 4, 'B': 5, 'B-': 6,
            'C+': 7, 'C': 8, 'C-': 9,
            'D+': 10, 'D': 11, 'D-': 12,
            'F+': 13, 'F': 14, 'F-': 15,
            'Not available': 16, 'Critical': 17
        }

        # Map grades to their ranks and sort by Grade
        result['Grade Rank'] = result['Grade'].map(grade_order)
        result = result.sort_values(by='Grade Rank')

        # Drop the Grade Rank column
        result = result.drop(columns=['Grade Rank'])

        # Center the Total Subdomains values for display
        result['Total Subdomains'] = result['Total Subdomains'].astype(str).str.center(5)

        return result

def search_by_grade(grade):
    with connect_to_db() as conn:
        query = """
        SELECT url, score, grade
        FROM results
        WHERE grade = ?
        GROUP BY url
        HAVING timestamp = MAX(timestamp)
        ORDER BY score DESC
        """
        df = pd.read_sql_query(query, conn, params=(grade,))
    
    if df.empty:
        return f"No URLs found with grade {grade}"
    
    # Format the results as a list of strings
    results = []
    for _, row in df.iterrows():
        results.append(f"{row['url']} (Score: {row['score']:.2f})")
    
    return results

# Example usage:
# urls_with_grade_b = search_by_grade('B')
# for url in urls_with_grade_b:
#     print(url)