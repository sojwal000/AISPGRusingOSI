"""Detailed MEA HTML structure analysis"""
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.mea.gov.in/',
}

url = "https://www.mea.gov.in/press-releases.htm"
response = requests.get(url, headers=headers, timeout=30)

soup = BeautifulSoup(response.text, 'html.parser')

print("=" * 80)
print("MEA Press Releases Page Analysis")
print("=" * 80)
print(f"Status: {response.status_code}")
print(f"URL: {response.url}")
print()

# Find all links
all_links = soup.find_all('a', href=True)
print(f"Total links: {len(all_links)}")
print()

# Categorize links
internal_links = [l for l in all_links if 'mea.gov.in' in l.get('href', '') or l.get('href', '').startswith('/')]
print(f"Internal links: {len(internal_links)}")

# Check for press release patterns
press_links = [l for l in all_links if 'press' in l.get('href', '').lower() and 'dtl' in l.get('href', '').lower()]
print(f"Links with 'press' and 'dtl': {len(press_links)}")

# Check for common ID patterns
id_patterns = [l for l in all_links if any(pat in l.get('href', '') for pat in ['?id=', '?dtl=', '/dtl/', 'PRID'])]
print(f"Links with ID patterns: {len(id_patterns)}")

# Sample some links
print("\nSample internal links (first 20):")
for i, link in enumerate(internal_links[:20], 1):
    href = link.get('href', '')
    text = link.get_text(strip=True)[:60]
    print(f"{i}. {href[:80]} | {text}")

# Check for content containers
print("\n" + "=" * 80)
print("Content Containers")
print("=" * 80)

tables = soup.find_all('table')
print(f"Tables: {len(tables)}")

divs_with_content = soup.find_all('div', class_=lambda x: x and ('content' in x.lower() or 'view' in x.lower() or 'list' in x.lower()))
print(f"Divs with content/view/list classes: {len(divs_with_content)}")

# Try to find listing pattern
print("\nSearching for listing patterns...")
for div in divs_with_content[:3]:
    links_in_div = div.find_all('a', href=True)
    print(f"Div class='{div.get('class')}' has {len(links_in_div)} links")
    if links_in_div:
        print(f"  Sample: {links_in_div[0].get('href', '')}")
