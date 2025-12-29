"""
MongoDB collections schema documentation.

Collections:
1. news_articles - Raw news articles from RSS feeds
2. government_reports - Government and international reports
3. raw_data_cache - Cache of raw API responses
"""

from datetime import datetime
from typing import Optional, List, Dict


# news_articles collection
def create_news_article_document(
    title: str,
    content: str,
    url: str,
    source: str,
    published_date: datetime,
    countries: List[str],
    keywords: Optional[List[str]] = None,
    summary: Optional[str] = None
) -> Dict:
    """Create a news article document for MongoDB"""
    return {
        "title": title,
        "content": content,
        "url": url,
        "source": source,
        "published_date": published_date,
        "countries": countries,  # List of country codes mentioned
        "keywords": keywords or [],
        "summary": summary,
        "ingested_at": datetime.utcnow(),
        "metadata": {
            "word_count": len(content.split()) if content else 0,
            "language": "en",  # Can be detected later
        }
    }


# government_reports collection
def create_government_report_document(
    title: str,
    content: str,
    url: str,
    source: str,
    report_type: str,
    published_date: datetime,
    countries: List[str],
    document_format: str = "html"
) -> Dict:
    """Create a government report document for MongoDB"""
    return {
        "title": title,
        "content": content,
        "url": url,
        "source": source,
        "report_type": report_type,  # "press_release", "advisory", "report", etc.
        "published_date": published_date,
        "countries": countries,
        "document_format": document_format,  # "pdf", "html", "text"
        "ingested_at": datetime.utcnow(),
    }


# raw_data_cache collection
def create_raw_cache_document(
    source_name: str,
    data_type: str,
    raw_data: Dict,
    fetch_timestamp: datetime
) -> Dict:
    """Create a raw data cache document"""
    return {
        "source_name": source_name,  # "ACLED", "WorldBank", "RSSFeed"
        "data_type": data_type,
        "raw_data": raw_data,
        "fetch_timestamp": fetch_timestamp,
        "created_at": datetime.utcnow(),
    }


# MongoDB collection names
COLLECTIONS = {
    "news_articles": "news_articles",
    "government_reports": "government_reports",
    "raw_data_cache": "raw_data_cache",
}
