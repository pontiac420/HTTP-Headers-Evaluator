import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import jinja2
import base64
from io import BytesIO
import os
import numpy as np

# Database operations
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'results.db')

def fetch_subdomain_data():
    conn = sqlite3.connect(DATABASE_PATH)
    query = """
    SELECT url, score, grade, header_name, status, header_value, timestamp
    FROM results
    ORDER BY score DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def generate_grade_distribution(df):
    # Get list of unique URLs
    unique_urls = df['url'].unique()
    
    # Function to get the most recent grade for a URL
    def get_latest_grade(url):
        url_data = df[df['url'] == url]
        return url_data.loc[url_data['timestamp'].idxmax(), 'grade']
    
    # Get the most recent grade for each unique URL
    latest_grades = [get_latest_grade(url) for url in unique_urls]
    
    # Count the grades
    grade_counts = pd.Series(latest_grades).value_counts().sort_index()
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create bar plot
    bars = ax.bar(grade_counts.index, grade_counts.values, edgecolor='black', alpha=0.7)
    
    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,}', ha='center', va='bottom')
    
    # Set labels and title
    ax.set_xlabel('Grade')
    ax.set_ylabel('Number of Unique URLs')
    ax.set_title('Grade Distribution for Most Recent Scans of Unique URLs')
    
    # Add grid for better readability
    ax.grid(axis='y', alpha=0.3)
    
    # Adjust y-axis to start from 0
    ax.set_ylim(bottom=0)
    
    # Rotate x-axis labels if they overlap
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=70, bbox_inches='tight')
    img_buffer.seek(0)
    return base64.b64encode(img_buffer.getvalue()).decode()

def analyze_grades(df):
    average_score = df['score'].mean()
    
    # Get the most recent scan for each unique URL
    latest_scans = df.sort_values('timestamp').groupby('url').last().reset_index()
    
    # Define grade order
    grade_order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']
    grade_to_num = {grade: i for i, grade in enumerate(grade_order)}
    
    # Sort all unique URLs by grade (A+ > A > A- > B+ > B > B- > ...) and then by score (highest to lowest)
    sorted_urls = latest_scans.sort_values(
        by=['grade', 'score'],
        key=lambda x: x.map(grade_to_num) if x.name == 'grade' else x,
        ascending=[True, False]
    )
    
    # Select only the desired columns
    columns_to_keep = ['url', 'score', 'grade']
    
    # Top 15 URLs (highest grades)
    top_urls = sorted_urls.head(15)[columns_to_keep]
    
    # Bottom 15 URLs (lowest grades)
    critical_urls = sorted_urls.tail(15).sort_values(
        by=['grade', 'score'],
        key=lambda x: x.map(grade_to_num) if x.name == 'grade' else x,
        ascending=[False, False]
    )[columns_to_keep]
    
    return average_score, top_urls, critical_urls

def generate_configuration_proposal_table():
    proposal_data = [
        ("Strict-Transport-Security", "max-age=31536000; includeSubDomains"),
        ("X-Frame-Options", "deny"),
        ("X-Content-Type-Options", "nosniff"),
        ("Content-Security-Policy", "default-src 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'; upgrade-insecure-requests; block-all-mixed-content"),
        ("X-Permitted-Cross-Domain-Policies", "none"),
        ("Referrer-Policy", "no-referrer"),
        ("Clear-Site-Data", "\"cache\",\"cookies\",\"storage\""),
        ("Cross-Origin-Embedder-Policy", "require-corp"),
        ("Cross-Origin-Opener-Policy", "same-origin"),
        ("Cross-Origin-Resource-Policy", "same-origin"),
        ("Permissions-Policy", "accelerometer=(), autoplay=(), camera=(), cross-origin-isolated=(), display-capture=(), encrypted-media=(), fullscreen=(), geolocation=(), gyroscope=(), keyboard-map=(), magnetometer=(), microphone=(), midi=(), payment=(), picture-in-picture=(), publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(self), usb=(), web-share=(), xr-spatial-tracking=(), clipboard-read=(), clipboard-write=(), gamepad=(), hid=(), idle-detection=(), interest-cohort=(), serial=(), unload=()"),
        ("Cache-Control", "no-store, max-age=0")
    ]
    
    table_html = "<table><tr><th>Header name</th><th>Proposed value</th></tr>"
    for header, value in proposal_data:
        table_html += f"<tr><td>{header}</td><td>{value}</td></tr>"
    table_html += "</table>"
    
    return table_html

def generate_comments_table():
    comments_data = [
        ("Strict-Transport-Security (HSTS)", "Can break non-HTTPS environments or development setups", "Safe in production with HTTPS"),
        ("X-Frame-Options", "Can block legitimate iframe usage", "Safe if your app doesn't use iframes"),
        ("X-Content-Type-Options", "No", "Safe for preventing MIME sniffing"),
        ("Referrer-Policy", "No", "Safe, controls how much referrer info is shared"),
        ("Content-Security-Policy", "Can block legitimate inline scripts or external content", "Requires careful configuration"),
        ("X-Permitted-Cross-Domain-Policies", "No", "Safe, controls cross-domain resource loading"),
        ("Clear-Site-Data", "Can cause data loss (e.g., cache, cookies)", "Needs to be used cautiously (e.g., for logout)"),
        ("Permissions-Policy", "Can interfere with feature access (e.g., geolocation)", "Safe if configured according to app requirements"),
        ("Cache-Control", "No", "Safe, controls caching behavior"),
        ("Cross-Origin-Embedder-Policy", "May break if not configured correctly", "Generally safe, controls embedding of resources"),
        ("Cross-Origin-Opener-Policy", "May break if not configured correctly", "Generally safe, controls opener policy"),
        ("Cross-Origin-Resource-Policy", "May break if not configured correctly", "Generally safe, controls resource policy")
    ]
    
    table_html = "<table><tr><th>Header</th><th>Can Break the App</th><th>Safe to Implement</th></tr>"
    for header, can_break, safe_to_implement in comments_data:
        table_html += f"<tr><td>{header}</td><td>{can_break}</td><td>{safe_to_implement}</td></tr>"
    table_html += "</table>"
    
    return table_html

def generate_report(grade_filter=None):
    df = fetch_subdomain_data()
    
    # Filter the dataframe based on the grade_filter
    if grade_filter:
        if isinstance(grade_filter, str):
            df = df[df['grade'] == grade_filter]
        elif isinstance(grade_filter, tuple) and len(grade_filter) == 2:
            grade_order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']
            start_index = grade_order.index(grade_filter[0])
            end_index = grade_order.index(grade_filter[1])
            selected_grades = grade_order[start_index:end_index+1]
            df = df[df['grade'].isin(selected_grades)]
    
    # Create a summary table with unique URLs
    summary_df = df.drop_duplicates(subset=['url'])[['url', 'score', 'grade']]

    grade_distribution_img = generate_grade_distribution(df)
    _, top_urls, critical_urls = analyze_grades(df)

    # Inline HTML template
    template_string = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Header Security Report</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            h1, h2, h3 { color: #2c3e50; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h1>Header Security Report</h1>
        
        <h2>Summary Table</h2>
        {{ summary_table }}
        
        <h2>Grade Distribution</h2>
        <img src="data:image/png;base64,{{ grade_distribution }}" alt="Grade Distribution">
        
        <h3>Top Performing URLs</h3>
        {{ top_urls }}
        
        <h3>Critical URLs</h3>
        {{ critical_urls }}
        
        <h2>Configuration Proposal (Some headers might break the app)</h2>
        {{ configuration_proposal }}
        
        <h2>Header Implementation Comments</h2>
        {{ comments_table }}
    </body>
    </html>
    """

    # Render the template
    template = jinja2.Template(template_string)
    html_report = template.render(
        summary_table=summary_df.to_html(classes='table table-striped', index=False),
        grade_distribution=grade_distribution_img,
        top_urls=top_urls.to_html(classes='table table-striped', index=False),
        critical_urls=critical_urls.to_html(classes='table table-striped', index=False),
        configuration_proposal=generate_configuration_proposal_table(),
        comments_table=generate_comments_table()
    )

    # Save the report
    report_path = os.path.join(SCRIPT_DIR, 'header_security_report.html')
    with open(report_path, 'w') as f:
        f.write(html_report)

    return report_path

if __name__ == '__main__':
    report_file = generate_report()
    print(f"Report generated: {report_file}")