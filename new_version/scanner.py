import requests
import re
from urllib.parse import urlparse
from datetime import datetime
from typing import List, Union

def clean_urls(input_urls: Union[str, List[str]]) -> List[str]:
    """
    Clean input URLs by removing protocol and path.
    
    Args:
        input_urls: A single URL, a list of URLs, or a file path containing URLs.
    
    Returns:
        A list of cleaned URLs.
    """
    if isinstance(input_urls, str):
        if input_urls.endswith('.txt'):
            with open(input_urls, 'r') as f:
                urls = f.read().splitlines()
        else:
            urls = [input_urls]
    else:
        urls = input_urls
    
    cleaned_urls = []
    for url in urls:
        parsed = urlparse(url)
        cleaned_url = parsed.netloc or parsed.path.split('/')[0]
        cleaned_urls.append(cleaned_url)
    
    return cleaned_urls

def fetch_headers(input_urls: Union[str, List[str]]) -> None:
    """
    Fetch headers for given URLs and print the results.
    
    Args:
        input_urls: A single URL, a list of URLs, or a file path containing URLs.
    """
    cleaned_urls = clean_urls(input_urls)
    
    for url in cleaned_urls:
        result = fetch_single_url(url)
        print("****************************************************")
        print(f"Initial URL: {url}")
        print(f"Final URL: {result['final_url']}")
        print(f"Status Code: {result['status_code']}")
        print(f"Protocol: {result['protocol']}")
        print("Headers:")
        for header, value in result['headers'].items():
            print(f"  {header}: {value}")
        print(f"Timestamp: {result['timestamp']}")
        print("-" * 50)

def fetch_single_url(url: str) -> dict:
    """
    Fetch headers for a single URL.
    
    Args:
        url: A single URL to fetch.
    
    Returns:
        A dictionary containing the fetch results.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    for protocol in ['https://', 'http://']:
        try:
            response = requests.get(f"{protocol}{url}", headers=headers, allow_redirects=True, timeout=10)
            return {
                'final_url': response.url,
                'status_code': response.status_code,
                'protocol': protocol.rstrip('://'),
                'headers': dict(response.headers),
                'timestamp': datetime.now().isoformat()
            }
        except requests.RequestException:
            continue
    
    return {
        'final_url': url,
        'status_code': 0,
        'protocol': '',
        'headers': {},
        'timestamp': datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Example usage
    urls = [
        "support.schoox.com",
        "https://design.schoox.com",
        "http://support.schoox.com",
        "https://support.schoox.com/hc/en-us",
        "http://app.schoox.com"
    ]
    fetch_headers(urls)
