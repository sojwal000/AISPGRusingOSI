"""Debug RSS encoding"""
import requests

response = requests.get("https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1", timeout=30)
print(f"Encoding: {response.encoding}")
print(f"Apparent encoding: {response.apparent_encoding}")
print(f"First 10 bytes (hex): {response.content[:10].hex()}")
print(f"First 200 chars raw:")
print(repr(response.text[:200]))
print()
print("Decoded properly:")
# Force UTF-8 with BOM handling
content = response.content.decode('utf-8-sig')
print(content[:200])
