---

# Security Headers Checker

This Python script checks for the presence of security headers on a given website and provides a grade based on the headers' configuration. It uses the [securityheaders.com](https://securityheaders.com/) API to fetch and analyze the headers, and applies a scoring system to determine the security rating of the website.

## Features

- **Check Security Headers**: Evaluate common security headers like `Strict-Transport-Security`, `X-Frame-Options`, `Content-Security-Policy`, and more.
- **Warnings Detection**: Detect warnings (e.g., unsafe configurations) in the headers.
- **Upcoming Headers**: Display upcoming headers without affecting the grade.
- **Scoring and Grading**: Score the site based on the number of passes and fails.
- **Interactive Mode**: If no URL is provided as a command-line argument, the script will prompt for input interactively.
- **Command-Line Usage**: Can be run with a target site URL passed as a command-line argument.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/your-username/security-headers-checker.git
    cd security-headers-checker
    ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Ensure you have the following in your `requirements.txt`:

    ```
    requests
    PyYAML
    beautifulsoup4
    ```

## Usage

You can run the script in two ways: by passing the target URL as a command-line argument or entering interactive mode.

### Command-Line Argument Mode

```bash
python check_headers.py https://example.com
```

This will check the security headers of `https://example.com` and display the results along with the final score and grade.

### Interactive Mode

If you don’t provide the URL as a command-line argument, the script will prompt you for one:

```bash
python check_headers.py
```

The script will then ask you to enter a URL:

```
Enter the target site URL (e.g., https://example.com): example.com  
```

### Example Output

```
Security Headers:
Strict-Transport-Security: PASS
X-Frame-Options: PASS
X-Content-Type-Options: PASS
Referrer-Policy: PASS
Content-Security-Policy: WARNING (Contains 'unsafe-inline')
X-Permitted-Cross-Domain-Policies: FAIL
Clear-Site-Data: FAIL
Permissions-Policy: PASS
Cache-Control: PASS

Headers That Should Be Removed:
Server: FAIL (present)
X-Powered-By: PASS (not present)
X-AspNet-Version: PASS (not present)
X-AspNetMvc-Version: PASS (not present)
Feature-Policy: PASS (not present)
Public-Key-Pins: PASS (not present)
Expect-CT: PASS (not present)
X-XSS-Protection: PASS (not present)

Upcoming Headers:
Cross-Origin-Embedder-Policy: PASS (Upcoming header)
Cross-Origin-Opener-Policy: PASS (Upcoming header)
Cross-Origin-Resource-Policy: PASS (Upcoming header)

Final Score: 23.53
Grade: C
```

### Grading System

The grading system is based on the following formula:

```
Score = (100 / 17) * (Total Passes - Total Fails)
```

The grade is assigned based on the final score:
```
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
```

## Configuration

The headers to be tested are stored in a YAML configuration file `headers_config.yml`. It contains three sections:

1. **Security Headers**: Headers that should be present for security purposes.
2. **Unwanted Headers**: Headers that should be removed for security reasons.
3. **Upcoming Headers**: Headers that will be displayed but not evaluated in the grading process.

### Example `headers_config.yml`

```yaml
# Security Headers
headers:
  - name: Strict-Transport-Security
    condition: "present"
  - name: X-Frame-Options
    condition: "present"
  - name: X-Content-Type-Options
    condition: "present"
  - name: Referrer-Policy
    condition: "present"
  - name: Content-Security-Policy
    condition: "present"
  - name: X-Permitted-Cross-Domain-Policies
    condition: "present"
  - name: Clear-Site-Data
    condition: "present"
  - name: Permissions-Policy
    condition: "present"
  - name: Cache-Control
    condition: "present"

# Headers That Should Be Removed
unwanted_headers:
  - name: Server
    condition: "not_present"
  - name: X-Powered-By
    condition: "not_present"
  - name: X-AspNet-Version
    condition: "not_present"
  - name: X-AspNetMvc-Version
    condition: "not_present"
  - name: Feature-Policy
    condition: "not_present"
  - name: Public-Key-Pins
    condition: "not_present"
  - name: Expect-CT
    condition: "not_present"
  - name: X-XSS-Protection
    condition: "not_present"

# Upcoming Headers
upcoming_headers:
  - name: Cross-Origin-Embedder-Policy
  - name: Cross-Origin-Opener-Policy
  - name: Cross-Origin-Resource-Policy
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributions

Contributions are welcome! Please feel free to open an issue or submit a pull request for any bugs or enhancements.

---
