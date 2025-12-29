# PIB Scraper Documentation

## Overview
Production-ready scraper for Press Information Bureau (PIB) of India government press releases. Successfully extracts 20+ press releases per run from official RSS feed with full content fetching.

## Status: ✓ Production Ready

### Test Results
- **Integration Test**: ✓ PASSED (100% data quality)
- **Documents Scraped**: 20 per run
- **Field Extraction**: 100% success rate
- **Storage**: MongoDB with deduplication
- **Performance**: ~18 seconds for 20 documents

## Architecture

### Data Flow
```
PIB RSS Feed → Extract PRID → Fetch Full Article → Parse Content → Store in MongoDB
```

### Key Components

#### 1. PIBScraper Class
**Location**: `backend/app/scraping/government.py`

**Main Method**: `scrape_recent_releases(days_back=7)`
- Fetches RSS feed from `https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1`
- Extracts PRID (Press Release ID) from each item
- Fetches full article from `https://pib.gov.in/PressReleasePage.aspx?PRID={prid}&Lang=1`
- Rate limiting: 0.5s delay between requests

**Helper Methods**:
- `_extract_prid(url)`: Extracts PRID using regex `r'PRID[=:](\d+)'`
- `_extract_pib_date(soup)`: Parses date from "प्रविष्टि तिथि:" label
- `_extract_pib_ministry(soup)`: Extracts ministry from heading
- `_extract_pib_content(soup)`: Extracts main content with fallback selectors

#### 2. UTF-8 BOM Handling
**Critical**: PIB RSS feed returns UTF-8 with BOM (`\xef\xbb\xbf` prefix)

```python
def fetch_page(self, url):
    response = requests.get(url, headers=self.headers, timeout=10)
    response.raise_for_status()
    
    # Handle UTF-8 BOM
    if response.content[:3] == b'\xef\xbb\xbf':
        return response.content.decode('utf-8-sig')
    
    return response.text
```

#### 3. Content Extraction Strategy
Multiple fallback selectors ensure robust content extraction:

```python
# Try multiple selectors
for selector in ['div.PdfDiv', 'div.content', 'article', 'main']:
    content_div = soup.select_one(selector)
    if content_div:
        break

# Fallback: Get all paragraphs
if not content_div:
    paragraphs = soup.find_all('p')
    content = '\n\n'.join([p.get_text() for p in paragraphs])
```

#### 4. MongoDB Storage
**Collection**: `government_reports`

**Document Schema**:
```json
{
  "source": "PIB",
  "title": "केन्द्रीय गृह एवं सहकारिता मंत्री...",
  "date": "2025-12-29 00:00:00",
  "url": "https://pib.gov.in/PressReleasePage.aspx?PRID=2209349&Lang=1",
  "body_text": "Full article content (981-9911 chars)",
  "ministry": "गृह मंत्रालय",
  "category": "general",
  "scraped_at": "2025-12-29 12:19:09"
}
```

**Deduplication**: Checks existing documents by URL before inserting

```python
existing = collection.find_one({"url": document["url"]})
if existing:
    return False  # Skip duplicate
```

## FastAPI Integration

### Endpoint
`POST /api/v1/ingest/government`

**Parameters**:
- `days_back` (optional, default=7): Number of days to scrape

**Response**:
```json
{
  "status": "success",
  "message": "Government data ingestion completed",
  "documents_ingested": 24,
  "sources": {
    "PIB": 20,
    "MEA": 2,
    "PMO": 2
  }
}
```

**Usage Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/government?days_back=7"
```

## Sample Output

### Typical Document
```
Title: केन्द्रीय गृह एवं सहकारिता मंत्री श्री अमित शाह ने आज अहमदाबाद...
Date: 2025-12-28 00:00:00
URL: https://pib.gov.in/PressReleasePage.aspx?PRID=2209301&Lang=1
Ministry: गृह मंत्रालय
Body: 6445 characters
Category: general
Scraped: 2025-12-29 12:19:09
```

### Coverage
PIB press releases include:
- Cabinet decisions
- Security announcements
- Policy changes
- Diplomatic statements
- Emergency notices
- Ministry updates
- Government schemes

## Performance Metrics

### Scraping Speed
- RSS Parsing: ~1 second
- Per Article: ~0.5-1 second
- Total (20 articles): ~18 seconds

### Data Quality (Integration Test Results)
- Documents with all required fields: 100%
- Documents with body text ≥50 chars: 100%
- Documents with valid dates: 100%
- Documents with URLs: 100%

### Storage Efficiency
- Deduplication: Prevents duplicate entries
- Average document size: ~3-7KB
- 20 documents ≈ 100KB storage

## Error Handling

### Network Errors
```python
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.RequestException as e:
    logger.error(f"Error fetching {url}: {e}")
    return None
```

### XML Parsing Errors
- UTF-8 BOM automatically detected and handled
- Malformed XML: Skips item and continues
- Missing PRID: Skips item and continues

### Content Extraction Failures
- Multiple fallback selectors
- Empty content: Logs warning, stores document anyway
- Missing date/ministry: Stores as "Unknown"

## Maintenance

### Regular Monitoring
1. Check scraper success rate: Should be 100% for PIB
2. Monitor document counts: Should get 20+ per run
3. Verify dates are recent (within days_back parameter)
4. Check body_text lengths: Should be 500+ chars average

### Troubleshooting

**Issue**: No documents scraped
- **Check**: PIB RSS feed availability: `https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1`
- **Solution**: Verify network connectivity and RSS feed format

**Issue**: XML parse errors
- **Check**: UTF-8 BOM handling in `fetch_page()`
- **Solution**: Ensure `decode('utf-8-sig')` is used for BOM detection

**Issue**: Empty body_text
- **Check**: PIB changed HTML structure
- **Solution**: Update content extraction selectors in `_extract_pib_content()`

**Issue**: All duplicates (0 new documents)
- **Check**: Last scrape time and days_back parameter
- **Solution**: Increase days_back or clean old documents

## Testing

### Unit Test
```bash
python test_scrapers.py
```
**Expected**: ≥10 PIB documents with all fields

### Integration Test
```bash
python test_integration.py
```
**Expected**: 100% quality rate, all 4 steps pass

### Manual Test
```python
from backend.app.scraping.government import PIBScraper
from backend.app.core.database import get_mongo_db

scraper = PIBScraper(get_mongo_db())
documents = scraper.scrape_recent_releases(days_back=7)
print(f"Scraped {len(documents)} documents")
```

## Configuration

### Rate Limiting
Current: 0.5s delay between requests
- **Recommended**: Keep at 0.5s to be respectful
- **Minimum**: 0.25s (risk of being blocked)
- **Maximum**: 1.0s (slower but safer)

### Days Back
Default: 7 days
- **Recommended**: 7 days for daily runs
- **Initial Load**: 30 days for first-time setup
- **Maximum**: 90 days (RSS feed typically contains ~20-30 items)

### Request Timeout
Current: 10 seconds
- Sufficient for PIB server response times
- Increase to 15s if frequent timeout errors

## Future Enhancements

### Potential Improvements
1. **Language Selection**: Add English feed support (`&Lang=2`)
2. **Ministry Filtering**: Filter by specific ministry codes
3. **Priority Scoring**: Flag high-priority announcements (security, emergency)
4. **Image Extraction**: Save embedded images/documents
5. **Related Documents**: Extract linked press releases
6. **Caching**: Store RSS feed temporarily to reduce requests

### Alternative Sources
If PIB RSS becomes unavailable:
- Direct HTML scraping from PIB homepage
- PIB API (if officially released)
- Twitter/X feed monitoring (@PIB_India)
- Republished content from news aggregators

## Integration with Risk Engine

### Signal Extraction
PIB documents feed into government_signal_score calculation:

1. **Security Announcements**: High weight (0.8-1.0)
2. **Diplomatic Statements**: Medium weight (0.5-0.7)
3. **Policy Changes**: Medium weight (0.4-0.6)
4. **Cabinet Decisions**: Variable weight (0.3-0.8)
5. **Routine Updates**: Low weight (0.1-0.3)

### Keywords for Risk Scoring
- **High Risk**: "आतंकवाद", "सुरक्षा", "सीमा", "संघर्ष", "आपातकाल"
- **Medium Risk**: "राजनयिक", "संबंध", "व्यापार", "प्रतिबंध"
- **Low Risk**: "योजना", "कार्यक्रम", "समारोह", "जयंती"

## Production Checklist

- [x] UTF-8 BOM handling implemented
- [x] Rate limiting configured (0.5s)
- [x] Deduplication working
- [x] Error handling comprehensive
- [x] Logging configured
- [x] MongoDB storage tested
- [x] FastAPI endpoint integrated
- [x] Integration test passing (100%)
- [x] Documentation complete
- [ ] Monitoring dashboard setup (future)
- [ ] Alert system for scraper failures (future)

## Contact
For PIB scraper issues or questions, refer to:
- Technical Docs: `TECHNICAL_DOCS.md`
- Setup Guide: `SETUP_GUIDE.md`
- Main README: `README.md`

---

**Last Updated**: December 29, 2025
**Status**: Production Ready ✓
**Maintainer**: AI System for Predicting Geopolitical Risk
