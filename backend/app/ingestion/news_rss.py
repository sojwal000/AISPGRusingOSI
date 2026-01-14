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
    
    # India-focused and international RSS feeds
    RSS_FEEDS = [
        # India sources
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
        # Pakistan sources
        {
            "url": "https://www.dawn.com/feeds/home",
            "source": "Dawn Pakistan",
            "country": "PAK"
        },
        {
            "url": "https://tribune.com.pk/feed",
            "source": "Express Tribune Pakistan",
            "country": "PAK"
        },
        {
            "url": "https://www.geo.tv/rss/1/1",
            "source": "Geo News Pakistan",
            "country": "PAK"
        },
        {
            "url": "https://nation.com.pk/rss",
            "source": "The Nation Pakistan",
            "country": "PAK"
        },
        {
            "url": "https://arynews.tv/feed/",
            "source": "ARY News Pakistan",
            "country": "PAK"
        },
        {
            "url": "https://www.thenews.com.pk/rss",
            "source": "The News Pakistan",
            "country": "PAK"
        },
        # China sources
        {
            "url": "https://www.scmp.com/rss/91/feed",
            "source": "South China Morning Post",
            "country": "CHN"
        },
        # Bangladesh sources
        {
            "url": "https://www.dhakatribune.com/feed",
            "source": "Dhaka Tribune",
            "country": "BGD"
        },
        {
            "url": "https://www.thedailystar.net/frontpage/rss.xml",
            "source": "The Daily Star Bangladesh",
            "country": "BGD"
        },
        # Russia sources
        {
            "url": "https://www.themoscowtimes.com/rss/news",
            "source": "Moscow Times",
            "country": "RUS"
        },
        {
            "url": "https://tass.com/rss/v2.xml",
            "source": "TASS Russian News",
            "country": "RUS"
        },
        {
            "url": "https://www.rt.com/rss/",
            "source": "RT News",
            "country": "RUS"
        },
        {
            "url": "https://ria.ru/export/rss2/archive/index.xml",
            "source": "RIA Novosti",
            "country": "RUS"
        },
        # International sources for broader coverage
        {
            "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
            "source": "BBC World",
            "country": "GLOBAL"
        },
        {
            "url": "http://rss.cnn.com/rss/cnn_world.rss",
            "source": "CNN World",
            "country": "GLOBAL"
        },
        {
            "url": "https://www.aljazeera.com/xml/rss/all.xml",
            "source": "Al Jazeera",
            "country": "GLOBAL"
        },
        {
            "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "source": "New York Times World",
            "country": "GLOBAL"
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
            "IND": ["india", "indian", "delhi", "mumbai", "bangalore", "kolkata", "new delhi"],
            "PAK": ["pakistan", "pakistani", "islamabad", "karachi", "lahore"],
            "CHN": ["china", "chinese", "beijing", "shanghai", "hong kong"],
            "USA": ["america", "american", "united states", "washington", "new york", "u.s.", "us "],
            "RUS": ["russia", "russian", "moscow", "kremlin", "putin"],
            "BGD": ["bangladesh", "bangladeshi", "dhaka", "bengali"],
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
            
            # Extract countries mentioned in text
            full_text = f"{article['title']} {article.get('summary', '')}"
            countries = self.extract_countries(full_text)
            
            # For country-specific sources, ALWAYS tag with that country
            if default_country != "GLOBAL" and default_country != "IND":
                # Force-tag articles from country-specific sources
                if default_country not in countries:
                    countries.append(default_country)
            elif default_country == "IND" or default_country == "GLOBAL":
                # For India and Global sources, use keyword extraction
                if default_country not in countries and default_country != "GLOBAL":
                    countries.append(default_country)
            
            # Ensure we have at least one country
            if not countries:
                countries = ["IND"]  # Default fallback
            
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
