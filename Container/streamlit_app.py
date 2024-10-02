# streamlit_app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import evaluator
import analytics
import asyncio
import tempfile
import os
from reports import generate_report
import plotly.graph_objects as go

# Use the environment variable for SCRIPT_DIR
SCRIPT_DIR = os.environ.get('SCRIPT_DIR', os.path.dirname(os.path.realpath(__file__)))
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'results.db')

# Initialize the database
try:
    evaluator.init_db()
except Exception as e:
    st.error(f"Failed to initialize database: {e}")
    st.stop()

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Run Scan", "Search", "Analytics Dashboard", "Database Management", "Generate Report"])

if page == "Run Scan":
    st.title("HTTP Header Security Scanner")
    
    scan_type = st.radio("Select scan type", ["Single URL", "Bulk URLs"])
    
    # Configuration options with smaller header
    st.markdown("#### Additional options")
    show_full_headers = st.checkbox("Show full headers")
    disable_ssl_verify = st.checkbox("Disable SSL verification")
    
    if scan_type == "Single URL":
        url = st.text_input("Enter URL to scan (e.g https://target_site.com)")
        if st.button("Scan", key="scan_single_url_button"):  # Unique key for this button
            try:
                config = evaluator.load_config(evaluator.CONFIG_PATH_DEFAULT)
                result = evaluator.process_single_url(url, config, show_full_headers=show_full_headers, ssl_context=None if disable_ssl_verify else False)
                if result:
                    score, grade, details = result
                    st.success(f"Scan completed for {url}")
                    st.write(f"Score: {score}")
                    st.write(f"Grade: {grade}")
                    st.write("Details:", details)
                else:
                    st.error(f"Failed to scan {url}")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    else:
        uploaded_file = st.file_uploader("Upload file with URLs", type="txt")
        bulk_urls = st.text_area("Or enter URLs (one per line)")
        if st.button("Scan Bulk", key="scan_bulk_urls_button"):  # Unique key for this button
            try:
                config = evaluator.load_config(evaluator.CONFIG_PATH_DEFAULT)
                
                # Create a temporary file to store the URLs
                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp_file:
                    if uploaded_file:
                        temp_file.write(uploaded_file.getvalue().decode())
                    elif bulk_urls:
                        temp_file.write(bulk_urls)
                    else:
                        st.warning("Please provide URLs either by file upload or text input.")
                        st.stop()
                    temp_file_path = temp_file.name

                with st.spinner('Running bulk scan...'):
                    metrics, detailed_results = asyncio.run(evaluator.process_bulk_urls(temp_file_path, config, show_full_headers=show_full_headers, ssl_context=None if disable_ssl_verify else False))
                
                # Remove the temporary file
                os.unlink(temp_file_path)

                st.success("Bulk scan completed")
                st.write("Metrics:", metrics)
                st.write("Detailed Results:", detailed_results)
            except Exception as e:
                st.error(f"An error occurred during bulk scan: {str(e)}")

elif page == "Analytics Dashboard":
    st.title("HTTP Header Security Analytics Dashboard")
    
    try:
        st.header("Overall Security Posture")
        summary = analytics.generate_overall_summary()
        if summary == "NO_DATA":
            st.info("No data available. Please run some scans to populate the database.")
        else:
            st.text(summary)
        
        if summary != "NO_DATA":
            st.header("Security Score Trend")
            trend_data = analytics.analyze_trends()
            fig = px.line(trend_data, x='date', y='avg_score', title='Average Security Score Over Time')
            st.plotly_chart(fig)

            st.header("Worst performing headers")
            vuln_data = analytics.top_vulnerabilities()
            fig = px.bar(vuln_data, x='header_name', y='count', title='Top 10 worst performing headers')
            st.plotly_chart(fig)

            st.header("URLs Requiring Immediate Attention")
            attention_urls = analytics.urls_requiring_attention()
            st.table(attention_urls)

            st.header("Security Header Adoption Rates")
            adoption_rates = analytics.header_adoption_rates()
            fig = px.bar(adoption_rates, x='header_name', y='adoption_rate', title='Security Header Adoption Rates')
            st.plotly_chart(fig)

            st.header("Recent Changes (Last 30 Days)")
            changes = analytics.recent_changes()
            st.table(changes)

            st.header("Subdomains with Same Header Configuration")
            same_header_subdomains = analytics.find_subdomains_with_same_headers()
            if not same_header_subdomains.empty:
                st.table(same_header_subdomains)
            else:
                st.info("No subdomains found with the same header configuration.")

    except Exception as e:
        st.error(f"An error occurred while generating analytics: {str(e)}")

elif page == "Search":
    st.title("Search (Local Database)")

    search_type = st.radio("Select search type", ["Search by URL", "Search by Grade"])

    if search_type == "Search by URL":
        st.header("Search by URL")
        search_url = st.text_input("Enter a URL to analyze:")
        if st.button("Analyze", key="search_analyze_url_button"):
            result, recommendations_fig = analytics.analyze_url(search_url)
            
            # Display the text result
            st.text(result)
            
            # Display the Plotly figure only if it exists
            if recommendations_fig is not None:
                st.plotly_chart(recommendations_fig)
            else:
                st.warning("No recommendations available. The database might be empty or the URL hasn't been scanned yet.")

    elif search_type == "Search by Grade":
        st.header("Search by Grade")
        grade = st.selectbox("Select a grade:", 
                             ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"])
        if st.button("Search by Grade", key="search_by_grade_button"):  # Add a unique key here
            results = analytics.search_by_grade(grade)
            if isinstance(results, list):
                st.subheader(f"URLs with grade {grade}:")
                for url in results:
                    st.write(url)
            else:
                st.info(results)  # This will display the "No URLs found" message if applicable

elif page == "Database Management":
    st.title("Database Management")
    
    try:
        st.header("Recent Scans")
        recent_scans = analytics.fetch_recent_scans()
        if recent_scans.empty:
            st.info("No recent scans found in the database. Run some scans to populate the database.")
        else:
            st.dataframe(recent_scans)
        
        st.header("Database Cleanup")
        
        # Option to choose how many days old data should be deleted
        days_to_keep = st.slider("Keep data from the last X days:", min_value=1, max_value=365, value=90)
        st.info(f"Note: The cleanup process will remove data older than {days_to_keep} days. This helps maintain database performance and focuses on more recent scan results.")
        if st.button("Clean up old entries"):
            deleted_count = analytics.cleanup_old_entries(days=days_to_keep)
            st.success(f"Cleaned up {deleted_count} entries older than {days_to_keep} days from the database.")
        
        # Option to delete specific URLs
        st.header("Delete Specific URLs")
        url_to_delete = st.text_input("Enter the exact URL to delete:")
        if st.button("Delete URL"):
            if url_to_delete:
                deleted_count = analytics.delete_url(url_to_delete)
                if deleted_count > 0:
                    st.success(f"Deleted {deleted_count} entries for URL: {url_to_delete}")
                else:
                    st.warning(f"No entries found for URL: {url_to_delete}")
            else:
                st.warning("Please enter a URL to delete.")
        
    except Exception as e:
        st.error(f"An error occurred during database management: {str(e)}")

elif page == "Generate Report":
    st.title("Generate Header Security Report")
    st.write("Select the options for your report:")

    filter_type = st.selectbox("Filter type", ["No filter", "Specific grade", "Grade range", "Above grade", "Below grade"])

    if filter_type == "Specific grade":
        grade = st.selectbox("Select grade", ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'])
        grade_filter = grade
    elif filter_type == "Grade range":
        start_grade = st.selectbox("Start grade", ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'])
        end_grade = st.selectbox("End grade", ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'])
        grade_filter = (start_grade, end_grade)
    elif filter_type == "Above grade":
        grade = st.selectbox("Select grade", ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'])
        grade_filter = ('A+', grade)
    elif filter_type == "Below grade":
        grade = st.selectbox("Select grade", ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'])
        grade_filter = (grade, 'F')
    else:
        grade_filter = None

    if st.button("Generate Report"):
        with st.spinner("Generating report..."):
            report_file = generate_report(grade_filter)
        st.success(f"Report generated: {report_file}")
        
        with open(report_file, "rb") as file:
            st.download_button(
                label="Download Report",
                data=file,
                file_name="header_security_report.html",
                mime="text/html"
            )

# Implement shared database operations in a separate module
# database_operations.py

