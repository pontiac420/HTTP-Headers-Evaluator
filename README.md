# HTTP Header Security Scanner

## Overview

The HTTP Header Security Scanner is a powerful tool designed to analyze and evaluate the security headers of websites. It provides both single URL and bulk URL scanning capabilities, along with an analytics dashboard for comprehensive security insights.

## Features

- **Single URL Scan**: Quickly analyze the security headers of a single website.
- **Bulk URL Scan**: Process multiple URLs simultaneously for efficient large-scale analysis.
- **Analytics Dashboard**: Visualize security trends, vulnerabilities, and adoption rates of security headers.
- **Database Management**: View recent scans and perform database cleanup operations.
- **Customizable Configuration**: Easily adjust security header requirements via a YAML configuration file.

#### Single Scan:
<img width="790" alt="εικόνα" src="https://github.com/user-attachments/assets/d66d28ff-aab6-4c16-ad4f-2cbedeba25c5">

#### URL Analyze:
<img width="781" alt="εικόνα" src="https://github.com/user-attachments/assets/f693548f-049f-406d-a6bf-671146409c55">



## Installation and Usage

### Prerequisites

- Docker

### Docker Deployment

1. Clone the repository:
   ```
   git clone https://github.com/pontiac420/HTTP-Headers-Scanner.git
   ```

2. Build the Docker image:
   ```
   docker build -t http-header-scanner .
   ```

3. Run the container:
   ```
   docker run -p 8501:8501 http-header-scanner
   ```

4. Open your web browser and navigate to `http://localhost:8501` to access the application.
   

### Using the Scanner

1. **Single URL Scan**: 
   - Enter a URL in the text input field.
   - Click "Scan" to analyze the security headers.

2. **Bulk URL Scan**:
   - Upload a text file containing URLs or enter URLs manually (one per line).
   - Click "Scan Bulk" to process multiple URLs.

3. **Retrieve URL data from database**:
   - Use the search functionality to find and retrieve data for specific URLs.   

3. **Analytics Dashboard**:
   - View overall security posture, trends, and vulnerabilities.
   - Analyze security header adoption rates and recent changes.

4. **Database Management**:
   - View recent scans and perform database cleanup operations.

5. **Generate Report**:
   - Use the "Generate Report" button to create a detailed HTML report of the scan results.

## Configuration

The `headers_config.yml` file in the Docker image contains the security header requirements and scoring criteria. To modify this, you'll need to update the file and rebuild the Docker image.

## Contributing

Contributions to the HTTP Header Security Scanner are welcome! Please feel free to submit pull requests, create issues or spread the word.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- This project uses [Streamlit](https://streamlit.io/) for the web interface.
- Security header recommendations are based on industry best practices and [OWASP](https://owasp.org/) guidelines.
