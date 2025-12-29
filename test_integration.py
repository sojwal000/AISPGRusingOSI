"""
End-to-end integration test for PIB government data ingestion
Tests: Scrape → Store → Retrieve via MongoDB
"""

import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.ingestion.government_data import GovernmentDataIngestion
from app.core.database import get_mongo_db
from app.models.mongo_models import COLLECTIONS
from app.core.logging import setup_logger

logger = setup_logger(__name__)


def test_full_pipeline():
    """Test complete ingestion and retrieval pipeline"""
    
    print("\n" + "=" * 80)
    print("FULL PIPELINE INTEGRATION TEST")
    print("=" * 80 + "\n")
    
    # Step 1: Trigger ingestion
    print("Step 1: Triggering PIB ingestion...")
    try:
        ingestion = GovernmentDataIngestion()
        result = ingestion.ingest_all_sources(days_back=7)
        
        print(f"✓ Ingestion completed")
        print(f"  Total documents: {result.get('total_documents', 0)}")
        print(f"  By source: {result.get('by_source', {})}")
        print()
        
        if result.get('total_documents', 0) < 10:
            print(f"⚠ WARNING: Only {result.get('total_documents', 0)} documents ingested (expected ≥10)")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Verify MongoDB storage
    print("Step 2: Verifying MongoDB storage...")
    try:
        mongo_db = get_mongo_db()
        collection = mongo_db[COLLECTIONS["government_reports"]]
        
        # Count documents from PIB
        pib_count = collection.count_documents({"source": "PIB"})
        print(f"✓ MongoDB storage verified")
        print(f"  PIB documents in DB: {pib_count}")
        print()
        
        if pib_count == 0:
            print("✗ ERROR: No PIB documents found in database")
            return False
        
        # Sample a document
        sample = collection.find_one({"source": "PIB"})
        if sample:
            print("Sample document:")
            print(f"  Title: {sample.get('title', 'N/A')[:70]}...")
            print(f"  Date: {sample.get('date', 'N/A')}")
            print(f"  URL: {sample.get('url', 'N/A')}")
            print(f"  Body length: {len(sample.get('body_text', ''))} chars")
            print(f"  Ministry: {sample.get('ministry', 'N/A')[:50]}")
            print()
            
    except Exception as e:
        print(f"✗ ERROR: MongoDB verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Test data retrieval
    print("Step 3: Testing data retrieval...")
    try:
        # Get recent documents
        recent_docs = list(collection.find(
            {"source": "PIB"},
            {"title": 1, "date": 1, "url": 1, "_id": 0}
        ).sort("date", -1).limit(5))
        
        print(f"✓ Retrieved {len(recent_docs)} recent PIB documents:")
        for i, doc in enumerate(recent_docs, 1):
            print(f"  {i}. {doc.get('title', 'N/A')[:60]}... ({doc.get('date', 'N/A')})")
        print()
        
    except Exception as e:
        print(f"✗ ERROR: Data retrieval failed: {e}")
        return False
    
    # Step 4: Verify data quality
    print("Step 4: Verifying data quality...")
    try:
        # Check required fields
        docs_with_issues = 0
        total_checked = 0
        
        for doc in collection.find({"source": "PIB"}).limit(20):
            total_checked += 1
            issues = []
            
            if not doc.get('title'):
                issues.append("missing title")
            if not doc.get('url'):
                issues.append("missing URL")
            if not doc.get('body_text') or len(doc.get('body_text', '')) < 50:
                issues.append("insufficient body text")
            if not doc.get('date'):
                issues.append("missing date")
            
            if issues:
                docs_with_issues += 1
                if docs_with_issues <= 3:  # Show first 3
                    print(f"  ⚠ Quality issue in: {doc.get('title', 'Unknown')[:50]}")
                    print(f"     Issues: {', '.join(issues)}")
        
        quality_rate = ((total_checked - docs_with_issues) / total_checked * 100) if total_checked > 0 else 0
        print(f"\n✓ Data quality check complete")
        print(f"  Documents checked: {total_checked}")
        print(f"  Documents with issues: {docs_with_issues}")
        print(f"  Quality rate: {quality_rate:.1f}%")
        print()
        
        if quality_rate < 80:
            print(f"⚠ WARNING: Quality rate below 80%")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: Quality verification failed: {e}")
        return False
    
    print("=" * 80)
    print("✓ PIPELINE INTEGRATION TEST PASSED")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
