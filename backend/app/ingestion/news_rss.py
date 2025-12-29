import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.core.logging import setup_logger
from app.core.database import get_mongo_db
from app.models.mongo_models import create_news_article_document, COLLECTIONS
import re

logger = setup_logger(__name__)


class NewsRSSIngestion:
    """Fetches news from RSS feeds"""
    
    # India-focused RSS feeds
    RSS_FEEDS = [
        {
            "url": "https://www.thehindu.com/news/national/feeder/default.rss",
            "source": "The Hindu - National",
            "country": "IND"
        },
        {
            "url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
            "source": "Times of India - India",
            "country": "IND"
        },
        {
            "url": "https://indianexpress.com/section/india/feed/",
            "source": "Indian Express - India",
            "country": "IND"
        },
        {
            "url": "https://www.ndtv.com/india/rss",
            "source": "NDTV India",
            "country": "IND"
        },
        {
            "url": "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
            "source": "BBC India",
            "country": "IND"
        },
    ]
    
    def __init__(self):
        self.mongo_db = get_mongo_db()
        self.collection = self.mongo_db[COLLECTIONS["news_articles"]]
    
    def fetch_feed(self, feed_url: str, source: str) -> List[Dict]:
        """Fetch and parse a single RSS feed"""
        try:
            logger.info(f"Fetching RSS feed from {source}...")
            feed = feedparser.parse(feed_url)
            
            articles = []
            for entry in feed.entries:
                article = {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", ""),
                    "source": source
                }
                articles.append(article)
            
            logger.info(f"Fetched {len(articles)} articles from {source}")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching feed from {source}: {e}")
            return []
    
    def parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        try:
            # Try parsing common RSS date formats
            from dateutil import parser
            return parser.parse(date_string)
        except Exception as e:
            logger.warning(f"Could not parse date: {date_string}")
            return datetime.utcnow()
    
    def extract_countries(self, text: str) -> List[str]:
        """Extract country mentions from text (basic implementation)"""
        # Simple keyword matching for Phase 1
        country_keywords = {
            "IND": ["india", "indian", "delhi", "mumbai", "bangalore", "kolkata"],
            "PAK": ["pakistan", "islamabad", "karachi"],
            "CHN": ["china", "chinese", "beijing"],
            "USA": ["america", "united states", "washington"],
        }
        
        text_lower = text.lower()
        found_countries = []
        
        for country_code, keywords in country_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                found_countries.append(country_code)
        
        return found_countries if found_countries else ["IND"]  # Default to India
    
    def store_article(self, article: Dict, default_country: str = "IND") -> bool:
        """Store article in MongoDB"""
        try:
            # Parse published date
            published_date = self.parse_date(article.get("published", ""))
            
            # Extract countries mentioned
            full_text = f"{article['title']} {article.get('summary', '')}"
            countries = self.extract_countries(full_text)
            if default_country not in countries:
                countries.append(default_country)
            
            # Create document
            doc = create_news_article_document(
                title=article["title"],
                content=article.get("summary", ""),
                url=article["url"],
                source=article["source"],
                published_date=published_date,
                countries=countries,
                summary=article.get("summary", "")
            )
            
            # Insert or update
            self.collection.update_one(
                {"url": article["url"]},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            logger.error(f"Error storing article: {e}")
            return False
    
    def ingest_all_feeds(self, days_back: int = 7) -> Dict[str, int]:
        """Ingest articles from all configured RSS feeds"""
        logger.info("Starting news RSS ingestion...")
        
        total_fetched = 0
        total_stored = 0
        
        for feed_config in self.RSS_FEEDS:
            articles = self.fetch_feed(feed_config["url"], feed_config["source"])
            total_fetched += len(articles)
            
            for article in articles:
                if self.store_article(article, feed_config["country"]):
                    total_stored += 1
        
        logger.info(f"News ingestion complete. Fetched: {total_fetched}, Stored: {total_stored}")
        
        return {
            "fetched": total_fetched,
            "stored": total_stored,
            "sources": len(self.RSS_FEEDS)
        }
    
    def get_recent_articles(self, country_code: str = "IND", days: int = 7) -> List[Dict]:
        """Get recent articles for a country"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        articles = self.collection.find({
            "countries": country_code,
            "published_date": {"$gte": cutoff_date}
        }).sort("published_date", -1).limit(100)
        
        return list(articles)


if __name__ == "__main__":
    # Test ingestion
    ingestion = NewsRSSIngestion()
    result = ingestion.ingest_all_feeds()
    print(f"Ingestion result: {result}")
