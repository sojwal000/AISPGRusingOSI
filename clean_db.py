"""Clean up test/sample data from MongoDB"""
import sys
sys.path.insert(0, 'backend')

from app.core.database import get_mongo_db
from datetime import datetime, timedelta

def clean_test_data():
    """Remove all sample test documents and old format documents"""
    db = get_mongo_db()
    collection = db['government_reports']
    
    # Delete all documents with sample URLs
    result1 = collection.delete_many({'url': {'$regex': '^sample'}})
    print(f"✓ Deleted {result1.deleted_count} sample documents")
    
    # Delete documents with old field names (content instead of body_text)
    result2 = collection.delete_many({'content': {'$exists': True}, 'body_text': {'$exists': False}})
    print(f"✓ Deleted {result2.deleted_count} old format documents")
    
    # Delete documents older than 10 days
    cutoff_date = datetime.now() - timedelta(days=10)
    result3 = collection.delete_many({'scraped_at': {'$lt': cutoff_date}})
    print(f"✓ Deleted {result3.deleted_count} documents older than 10 days")
    
    # Show current counts
    pib_count = collection.count_documents({'source': 'PIB'})
    mea_count = collection.count_documents({'source': 'MEA'})
    pmo_count = collection.count_documents({'source': 'PMO'})
    
    print(f"\nCurrent document counts:")
    print(f"  PIB: {pib_count}")
    print(f"  MEA: {mea_count}")
    print(f"  PMO: {pmo_count}")
    print(f"  Total: {pib_count + mea_count + pmo_count}")
    
    # Show sample of real PIB documents
    print(f"\nSample PIB documents:")
    docs = list(collection.find(
        {'source': 'PIB'},
        {'title': 1, 'date': 1, 'url': 1, 'body_text': 1, '_id': 0}
    ).sort('scraped_at', -1).limit(3))
    
    for i, doc in enumerate(docs, 1):
        title = doc.get('title', 'N/A')[:60]
        date = doc.get('date', 'N/A')
        body_len = len(doc.get('body_text', ''))
        url = doc.get('url', 'N/A')[:50]
        print(f"  {i}. {title}... | {date} | {body_len} chars | {url}...")

if __name__ == '__main__':
    clean_test_data()
