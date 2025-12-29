"""
Test script for PIB and MEA scrapers
Run this to verify scraper implementation
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.scraping.government import PIBScraper, MEAScraper
from app.core.logging import setup_logger

logger = setup_logger(__name__)


def test_pib_scraper():
    """Test PIB scraper"""
    print("\n" + "=" * 80)
    print("TESTING PIB SCRAPER")
    print("=" * 80 + "\n")
    
    try:
        scraper = PIBScraper()
        documents = scraper.scrape_recent_releases(days_back=7, max_items=10)
        
        print(f"\n✓ PIB Scraper Results: {len(documents)} documents\n")
        
        for i, doc in enumerate(documents[:3], 1):
            print(f"Document {i}:")
            print(f"  Title: {doc.get('title', 'N/A')[:80]}...")
            print(f"  URL: {doc.get('url', 'N/A')}")
            print(f"  Date: {doc.get('date', 'N/A')}")
            print(f"  Ministry: {doc.get('ministry', 'N/A')[:50]}")
            print(f"  Body Length: {len(doc.get('body_text', ''))} chars")
            print()
        
        # Verify minimum criteria
        if len(documents) >= 10:
            print("✓ SUCCESS: PIB scraper met minimum criteria (≥10 items)")
            return True
        else:
            print(f"⚠ WARNING: PIB scraper returned {len(documents)} items (expected ≥10)")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: PIB scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mea_scraper():
    """Test MEA scraper"""
    print("\n" + "=" * 80)
    print("TESTING MEA SCRAPER")
    print("=" * 80 + "\n")
    
    try:
        scraper = MEAScraper()
        documents = scraper.scrape_recent_statements(days_back=7, max_items=10)
        
        print(f"\n✓ MEA Scraper Results: {len(documents)} documents\n")
        
        for i, doc in enumerate(documents[:3], 1):
            print(f"Document {i}:")
            print(f"  Title: {doc.get('title', 'N/A')[:80]}...")
            print(f"  URL: {doc.get('url', 'N/A')}")
            print(f"  Date: {doc.get('date', 'N/A')}")
            print(f"  Type: {doc.get('doc_type', 'N/A')}")
            print(f"  Body Length: {len(doc.get('body_text', ''))} chars")
            print()
        
        # Verify minimum criteria
        if len(documents) >= 10:
            print("✓ SUCCESS: MEA scraper met minimum criteria (≥10 items)")
            return True
        else:
            print(f"⚠ WARNING: MEA scraper returned {len(documents)} items (expected ≥10)")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: MEA scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("GOVERNMENT SCRAPER TEST SUITE")
    print("=" * 80)
    
    pib_success = test_pib_scraper()
    mea_success = test_mea_scraper()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"PIB Scraper: {'✓ PASSED' if pib_success else '✗ FAILED'}")
    print(f"MEA Scraper: {'✓ PASSED' if mea_success else '✗ FAILED'}")
    print("=" * 80 + "\n")
    
    sys.exit(0 if (pib_success and mea_success) else 1)
