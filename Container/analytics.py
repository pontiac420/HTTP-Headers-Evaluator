import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from tabulate import tabulate
import datetime
import logging
import os
import hashlib
from reports import generate_configuration_proposal_table, generate_comments_table
import textwrap

# Database operations
SCRIPT_DIR = os.environ.get('SCRIPT_DIR', os.path.dirname(os.path.realpath(__file__)))
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'results.db')

def connect_to_db():
    return sqlite3.connect(DATABASE_PATH)

def fetch_all_results_for_url(url):
    with connect_to_db() as conn:
        # Normalize the URL by removing the protocol if present
        normalized_url = url.split('://')[-1] if '://' in url else url
        
        query = """
        WITH latest_scan AS (
            SELECT MAX(timestamp) as max_timestamp
            FROM results
            WHERE url LIKE ? OR url LIKE ? OR url = ? OR url = ?
        )
        SELECT r.*
        FROM results r
        JOIN latest_scan ls
        WHERE (r.url LIKE ? OR r.url LIKE ? OR r.url = ? OR r.url = ?)
        AND r.timestamp = ls.max_timestamp
        """
        # Prepare search patterns for both http and https
        params = (f"http://{normalized_url}%", f"https://{normalized_url}%", 
                  f"http://{normalized_url}", f"https://{normalized_url}") * 2
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
    # Filter for both 'FAIL' and 'FAIL (present)' statuses
    vulnerabilities = df[df['status'].isin(['FAIL', 'FAIL (present)'])]
    
    # Drop duplicate headers
    unique_vulnerabilities = vulnerabilities['header_name'].drop_duplicates()
    
    summary = "Missing or Failing Headers:\n"
    for header in unique_vulnerabilities:
        # Get the status for this header
        status = vulnerabilities[vulnerabilities['header_name'] == header]['status'].iloc[0]
        
        if status == 'FAIL':
            summary += f"- {header}\n"
        elif status == 'FAIL (present)':
            summary += f"- {header} (should be removed)\n"
    
    return summary

def generate_recommendations_table(vulnerability_summary):
    # Helper function to parse HTML tables
    def parse_html_table(html_table):
        rows = html_table.split('<tr>')[2:]  # Skip header row
        return [tuple(cell.split('</td>')[0].strip() for cell in row.split('<td>')[1:]) 
                for row in rows if row.strip()]

    # Parse the HTML tables
    proposal_data = dict(parse_html_table(generate_configuration_proposal_table()))
    comments_data = {row[0].split(' ')[0]: (row[1], row[2]) for row in parse_html_table(generate_comments_table())}
    
    # List of headers that should be removed
    headers_to_remove = [
        "Server",
        "X-Powered-By",
        "X-AspNet-Version",
        "X-AspNetMvc-Version",
        "Feature-Policy",
        "Public-Key-Pins",
        "Expect-CT",
        "X-XSS-Protection"
        # Add any other headers that should be removed
    ]
    
    headers = ['Header Name', 'Recommendation', 'Can break the app', 'Safe to implement']
    cells = []
    
    for header in vulnerability_summary.split('\n')[1:]:  # Skip the first line which is the title
        header = header.strip('- ')  # Remove the leading dash and space
        if header and not header.isspace():  # Check if header is not empty or just whitespace
            if header.endswith(" (should be removed)"):
                header = header.replace(" (should be removed)", "")
                recommendation = "Remove header"
            elif header in headers_to_remove:
                recommendation = "Remove header"
            else:
                recommendation = proposal_data.get(header, "No specific recommendation")
            
            can_break, safe_to_implement = comments_data.get(header.split(' ')[0], ("Unknown", "Unknown"))
            cells.append([header, recommendation, can_break, safe_to_implement])

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=headers,
            fill_color='#4CAF50',  # A green color
            align='left',
            font=dict(color='white', size=12)
        ),
        cells=dict(
            values=list(zip(*cells)),
            fill_color='#F9F9F9',  # Very light gray, almost white
            align='left',
            font=dict(color='#333', size=11)  # Dark gray text
        )
    )])

    fig.update_layout(
        title='Recommendations',
        height=100 + (len(cells) * 30),  # Adjust height based on number of rows
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='white',  # White background for the entire figure
        plot_bgcolor='white'    # White background for the plot area
    )

    return fig

def analyze_url(url):
    df = fetch_all_results_for_url(url)
    
    if df.empty:
        return f"No data found for URL: {url}", None

    summary = generate_url_summary(df.iloc[0])
    interpretation = interpret_score_and_grade(df['score'].iloc[0], df['grade'].iloc[0])
    headers_report = generate_headers_report(df)
    vulnerability_summary = generate_vulnerability_summary(df)
    recommendations_fig = generate_recommendations_table(vulnerability_summary)

    timestamp = df['timestamp'].iloc[0]
    
    result = f"""Most recent scan results (as of {timestamp}):

{summary}

{interpretation}

{headers_report}

{vulnerability_summary}

Recommendations:
"""
    return result, recommendations_fig

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
    
    if df.empty:
        return "NO_DATA"
    
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
    if 0 <= score < 20:
        return "F"
    elif 20 <= score < 30:
        return "E"
    elif 30 <= score < 40:
        return "D-"
    elif 40 <= score < 50:
        return "D"
    elif 50 <= score < 60:
        return "D+"
    elif 60 <= score < 65:
        return "C-"
    elif 65 <= score < 70:
        return "C"
    elif 70 <= score < 75:
        return "C+"
    elif 75 <= score < 80:
        return "B-"
    elif 80 <= score < 85:
        return "B"
    elif 85 <= score < 90:
        return "B+"
    elif 90 <= score < 95:
        return "A-"
    elif 95 <= score < 98:
        return "A"
    elif 98 <= score <= 100:
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
            WITH base_urls AS (
                SELECT 
                    CASE 
                        WHEN url LIKE 'http://%' THEN SUBSTR(url, 8)
                        WHEN url LIKE 'https://%' THEN SUBSTR(url, 9)
                        ELSE url
                    END AS base_url,
                    url,
                    score,
                    grade,
                    ROW_NUMBER() OVER (PARTITION BY 
                        CASE 
                            WHEN url LIKE 'http://%' THEN SUBSTR(url, 8)
                            WHEN url LIKE 'https://%' THEN SUBSTR(url, 9)
                            ELSE url
                        END 
                    ORDER BY 
                        CASE grade
                            WHEN 'F' THEN 1
                            WHEN 'F+' THEN 2
                            WHEN 'F-' THEN 3
                            WHEN 'D-' THEN 4
                            WHEN 'D' THEN 5
                            WHEN 'D+' THEN 6
                            WHEN 'C-' THEN 7
                            WHEN 'C' THEN 8
                            WHEN 'C+' THEN 9
                            WHEN 'B-' THEN 10
                            WHEN 'B' THEN 11
                            WHEN 'B+' THEN 12
                            WHEN 'A-' THEN 13
                            WHEN 'A' THEN 14
                            WHEN 'A+' THEN 15
                            ELSE 16
                        END ASC,
                        score ASC
                    ) as row_num
                FROM results
            )
            SELECT url, score, grade
            FROM base_urls
            WHERE row_num = 1
            ORDER BY 
                CASE grade
                    WHEN 'F' THEN 1
                    WHEN 'F+' THEN 2
                    WHEN 'F-' THEN 3
                    WHEN 'D-' THEN 4
                    WHEN 'D' THEN 5
                    WHEN 'D+' THEN 6
                    WHEN 'C-' THEN 7
                    WHEN 'C' THEN 8
                    WHEN 'C+' THEN 9
                    WHEN 'B-' THEN 10
                    WHEN 'B' THEN 11
                    WHEN 'B+' THEN 12
                    WHEN 'A-' THEN 13
                    WHEN 'A' THEN 14
                    WHEN 'A+' THEN 15
                    ELSE 16
                END ASC,
                score ASC
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

from urllib.parse import urlparse

def normalize_url(url):
    parsed = urlparse(url)
    normalized = parsed.netloc + parsed.path.rstrip('/')
    return normalized.lower()

def search_by_grade(grade):
    with connect_to_db() as conn:
        # First, let's check if there are any results for this grade
        check_query = "SELECT COUNT(*) as count FROM results WHERE grade = ?"
        count = pd.read_sql_query(check_query, conn, params=(grade,))['count'].iloc[0]
        
        if count == 0:
            print(f"Debug: No results found for grade {grade}")
            return f"No URLs found with grade {grade}"
        
        # If we have results, let's fetch them all
        query = """
        SELECT url, grade, score, timestamp
        FROM results
        WHERE grade = ?
        ORDER BY timestamp DESC
        """
        df = pd.read_sql_query(query, conn, params=(grade,))
    
    print(f"Debug: Found {len(df)} results for grade {grade}")
    
    # Group by URL and keep only the most recent result for each
    df = df.sort_values('timestamp', ascending=False).groupby('url').first().reset_index()
    
    print(f"Debug: After grouping, have {len(df)} unique URLs")
    
    # Format the results
    results = [f"{row['url']} (Score: {row['score']:.2f}, Timestamp: {row['timestamp']})" for _, row in df.iterrows()]
    
    if not results:
        return f"No URLs currently have grade {grade}"
    
    return results

# Example usage:
# urls_with_grade_b = search_by_grade('B')
# for url in urls_with_grade_b:
#     print(url)