---

# Security Headers Evaluation Tool

This Python script evaluates the HTTP security headers of websites, checks for unwanted headers, and calculates a security score. It supports single URL checks and bulk processing of multiple URLs, saving the results to a CSV file.

## Features

- **Security Headers Check**: Verifies the presence of essential security headers such as `Strict-Transport-Security`, `X-Frame-Options`, and more.
- **Unwanted Headers Check**: Ensures headers like `Server`, `X-Powered-By`, and others that should not be exposed are absent.
- **Warning Detection**: Fetches warnings from [securityheaders.com](https://securityheaders.com) and includes them in the evaluation.
- **Grading System**: Grades the website based on the security headers' presence, warnings, and the number of unwanted headers.
- **Bulk Processing**: Accepts a list of URLs in a text file and processes them all, saving the results to a CSV file.

## Installation

1. Clone the repository or download the script files.
2. Install the required Python packages by running:

   ```bash
   pip install -r requirements.txt
   ```

3. The script uses a configuration file (`headers_config.yml`) to define the headers and conditions for passing or failing. Ensure this file is in the same directory as the script.

## Usage

### Single URL Evaluation

To check the security headers of a single website, use the `--target_site` argument followed by the website's URL:

```bash
python3 evaluate_headers.py --target_site https://example.com
```

### Bulk URL Processing

To evaluate multiple URLs, provide a text file containing the URLs (one URL per line) with the `--bulk` argument. Use the `--output_csv` argument to specify the CSV output file:

```bash
python3 evaluate_headers.py --bulk urls.txt --output_csv results.csv
```

Where `urls.txt` contains:
```
https://example1.com
https://example2.com
https://example3.com
```

This will process each URL and save the results to `results.csv`.

### Example Output

For each website, the script will output:

- **Score and Grade**: Based on the presence or absence of security headers and unwanted headers.
- **Security Headers**: `PASS`, `FAIL`, or `WARNING` (with the warning message).
- **Unwanted Headers**: Check whether unwanted headers like `Server` and `X-Powered-By` are exposed.

Sample output:

```bash
Security Headers (Fail if not present):
Strict-Transport-Security: PASS
X-Frame-Options: PASS
X-Content-Type-Options: PASS
Referrer-Policy: PASS
Content-Security-Policy: WARNING (This policy contains 'unsafe-inline' which is dangerous in the script-src directive.)
X-Permitted-Cross-Domain-Policies: FAIL
Clear-Site-Data: FAIL
Permissions-Policy: PASS
Cache-Control: PASS

Headers That Should Be Removed (Fail if present):
Server: FAIL (present)
X-Powered-By: PASS (not present)

Upcoming Headers:
Cross-Origin-Embedder-Policy: PASS (Upcoming header)
Cross-Origin-Opener-Policy: PASS (Upcoming header)
Cross-Origin-Resource-Policy: PASS (Upcoming header)

Final Score: 52.94
Grade: B
```

### Configuration

The `headers_config.yml` file contains the configuration for the security and unwanted headers:

```yaml
# Security Headers
headers:
  - name: Strict-Transport-Security
    condition: "present"
  - name: X-Frame-Options
    condition: "present"
  # Add more headers as needed...

# Unwanted Headers
unwanted_headers:
  - name: Server
    condition: "not_present"
  - name: X-Powered-By
    condition: "not_present"
  # Add more headers as needed...

# Upcoming Headers (Not considered in grading)
upcoming_headers:
  - name: Cross-Origin-Embedder-Policy
  - name: Cross-Origin-Opener-Policy
  - name: Cross-Origin-Resource-Policy
```

### Grading

The grading system is based on the following:

- Each header `PASS`: +5.88 points (for a total of 17 headers)
- Each header `FAIL` or `WARNING`: Subtracted from the score

The grade ranges are:

| Score Range   | Grade |
| ------------- | ----- |
| 88.88 - 100   | A+    |
| 77.77 - 88.87 | A     |
| 66.66 - 77.76 | A-    |
| 55.55 - 66.65 | B+    |
| 44.44 - 55.54 | B     |
| 33.33 - 44.43 | B-    |
| 22.22 - 33.32 | C+    |
| 11.11 - 22.21 | C     |
|  0.00 - 11.10 | C-    |
| -0.01 - -11.11| D+    |
| -11.12 - -22.22| D    |
| ... | F    |

### License

This project is licensed under the MIT License.

---

