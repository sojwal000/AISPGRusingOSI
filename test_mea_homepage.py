"""Find actual working MEA press release URLs"""
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Start from homepage
response = requests.get("https://www.mea.gov.in/index.htm", headers=headers, timeout=30)
soup = BeautifulSoup(response.text, 'html.parser')

print("Finding Press Release links from MEA Homepage...")
print()

# Find navigation/menu items
nav_links = soup.find_all('a', text=lambda x: x and ('press' in x.lower() or 'release' in x.lower() or 'statement' in x.lower() or 'briefing' in x.lower()))

print(f"Found {len(nav_links)} navigation links with press/release/statement/briefing:")
for link in nav_links:
    print(f"  Text: '{link.get_text(strip=True)}'")
    print(f"  Href: {link.get('href', 'N/A')}")
    print()

# Look for actual press release entries on homepage
print("\nLooking for actual press release entries...")
all_links = soup.find_all('a', href=True)
press_related = [l for l in all_links if any(term in l.get_text().lower() for term in ['minister', 'statement', 'meeting', 'visit', 'bilateral'])]

print(f"Found {len(press_related[:10])} content links:")
for i, link in enumerate(press_related[:10], 1):
    href = link.get('href', '')
    text = link.get_text(strip=True)[:70]
    print(f"{i}. {text}")
    print(f"   {href}")
    print()
