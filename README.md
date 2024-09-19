# Web Security Header Analysis Tool

This repository contains a suite of tools for analyzing web security headers. It includes a command-line interface (CLI) tool for evaluating individual URLs or bulk URL lists, and an interactive menu-driven application for comprehensive analysis and reporting.

## Files in the Repository

### evaluator.py

This is the core CLI tool for evaluating web security headers. It can be used independently or called from the interactive menu.

**Functionality:**
- Evaluate security headers for a single URL
- Process a list of URLs from a file
- Generate detailed reports on header compliance and security scores

**Usage:**
```
python3 evaluator.py --target_site <url>
python3 evaluator.py --bulk <file_path>
```

### interactive_menu.py

This is the full suite application providing an interactive menu-driven interface for comprehensive header analysis.

**Functionality:**
1. Search results by grade
2. List all results
3. Show best and worst performing headers overall
4. Show best and worst performing URLs
5. Show the overall header health of a domain
6. Run the Evaluator tool (calls evaluator.py)
7. Exit the program

**Usage:**
```
python3 interactive_menu.py
```

### results.db

SQLite database file storing the results of header evaluations. This is used by both `evaluator.py` and `interactive_menu.py` to persist and retrieve analysis data.

## Dependencies

- Python 3.x
- SQLite3
- Additional Python libraries (specified in `requirements.txt`)

## Setup and Installation

1. Clone the repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Ensure `evaluator.py` and `interactive_menu.py` are in the same directory

## Usage

- For quick evaluations of URLs, use `evaluator.py` directly.
- For comprehensive analysis and reporting, run `interactive_menu.py` and use the menu options.

**Note:** Option 6 in the interactive menu (Run Evaluator) depends on `evaluator.py` being present in the same directory.

## Contributing

Contributions to improve the tool are welcome. Please submit pull requests or open issues for any bugs or feature requests.

