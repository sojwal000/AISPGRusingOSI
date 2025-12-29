"""Quick diagnostic script to check actual PIB RSS and MEA HTML structure"""
import requests
from bs4 import BeautifulSoup

# Test PIB RSS
print("=" * 80)
print("PIB RSS STRUCTURE TEST")
print("=" * 80)

try:
    response = requests.get(
        "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1",
        timeout=30,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"First 500 chars:")
    print(response.text[:500])
    print()
except Exception as e:
    print(f"Error: {e}\n")

# Test MEA
print("=" * 80)
print("MEA PRESS RELEASES STRUCTURE TEST")
print("=" * 80)

try:
    response = requests.get(
        "https://www.mea.gov.in/press-releases.htm?dtl",
        timeout=30,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.mea.gov.in/',
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find various link patterns
    dtl_links = soup.find_all('a', href=lambda x: x and 'dtl' in x.lower())
    print(f"Links with 'dtl': {len(dtl_links)}")
    
    if dtl_links:
        print("Sample dtl links:")
        for link in dtl_links[:5]:
            print(f"  {link.get('href')}")
    else:
        print("No dtl links found")
        all_links = soup.find_all('a', href=True)
        print(f"Total links found: {len(all_links)}")
        if all_links:
            print("Sample links:")
            for link in all_links[:10]:
                href = link.get('href', '')
                print(f"  {href[:80]}")
    
except Exception as e:
    print(f"Error: {e}")
