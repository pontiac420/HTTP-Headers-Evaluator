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

# Database operations
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'results.db')

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Run Scan", "Analytics Dashboard", "Database Management", "Generate Report"])

if page == "Run Scan":
    st.title("HTTP Header Security Scanner")
    
    scan_type = st.radio("Select scan type", ["Single URL", "Bulk URLs"])
    
    # Configuration options with smaller header
    st.markdown("#### Additional options")
    show_full_headers = st.checkbox("Show full headers")
    disable_ssl_verify = st.checkbox("Disable SSL verification")
    
    if scan_type == "Single URL":
        url = st.text_input("Enter URL to scan")
        if st.button("Scan"):
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
        if st.button("Scan Bulk"):
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
        st.text(analytics.generate_overall_summary())
        
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

        # Move Search by URL functionality to the end
        st.header("Search by URL")
        search_url = st.text_input("Enter a URL to analyze:")
        if st.button("Analyze"):
            if search_url:
                result = analytics.analyze_url(search_url)
                st.text(result)
            else:
                st.warning("Please enter a URL to analyze.")

    except Exception as e:
        st.error(f"An error occurred while generating analytics: {str(e)}")

elif page == "Database Management":
    st.title("Database Management")
    
    try:
        st.header("Recent Scans")
        recent_scans = analytics.fetch_recent_scans()
        if not recent_scans.empty:
            st.dataframe(recent_scans)
        else:
            st.info("No recent scans found in the database.")
        
        st.header("Database Cleanup")
        st.info("Note: The cleanup process automatically removes data older than 90 days. This helps maintain database performance and focuses on more recent scan results.")
        if st.button("Clean up old entries"):
            deleted_count = analytics.cleanup_old_entries()
            st.success(f"Cleaned up {deleted_count} entries older than 90 days from the database.")
    except Exception as e:
        st.error(f"An error occurred during database management: {str(e)}")

elif page == "Generate Report":
    st.title("Generate Header Security Report")
    st.write("Click the button below to generate a comprehensive Header Security Report.")

    if st.button("Generate Report"):
        with st.spinner("Generating report..."):
            report_file = generate_report()
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

