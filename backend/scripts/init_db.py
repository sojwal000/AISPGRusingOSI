"""
Database initialization script.
Creates tables and initial seed data.
"""
from app.core.database import engine, Base, get_mongo_db
from app.models.sql_models import Country, RiskScore, Alert, EconomicIndicator, ConflictEvent
from app.models.mongo_models import COLLECTIONS
from app.core.logging import setup_logger

logger = setup_logger(__name__)


def init_postgres():
    """Initialize PostgreSQL database"""
    logger.info("Creating PostgreSQL tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("PostgreSQL tables created successfully")


def init_mongodb():
    """Initialize MongoDB collections and indexes"""
    logger.info("Setting up MongoDB collections...")
    db = get_mongo_db()
    
    # Create collections if they don't exist
    existing_collections = db.list_collection_names()
    
    for collection_name in COLLECTIONS.values():
        if collection_name not in existing_collections:
            db.create_collection(collection_name)
            logger.info(f"Created collection: {collection_name}")
    
    # Create indexes
    db.news_articles.create_index([("url", 1)], unique=True)
    db.news_articles.create_index([("published_date", -1)])
    db.news_articles.create_index([("countries", 1)])
    
    db.government_reports.create_index([("url", 1)], unique=True)
    db.government_reports.create_index([("published_date", -1)])
    
    db.raw_data_cache.create_index([("source_name", 1), ("fetch_timestamp", -1)])
    
    logger.info("MongoDB indexes created successfully")


def seed_countries():
    """Seed initial country data"""
    from app.core.database import SessionLocal
    
    logger.info("Seeding country data...")
    db = SessionLocal()
    
    try:
        # Check if countries already exist
        existing_count = db.query(Country).count()
        if existing_count > 0:
            logger.info(f"Countries already seeded ({existing_count} records)")
            return
        
        # Initial countries (focusing on India and neighbors)
        countries = [
            {"code": "IND", "name": "India", "region": "South Asia"},
            {"code": "PAK", "name": "Pakistan", "region": "South Asia"},
            {"code": "CHN", "name": "China", "region": "East Asia"},
            {"code": "BGD", "name": "Bangladesh", "region": "South Asia"},
            {"code": "NPL", "name": "Nepal", "region": "South Asia"},
            {"code": "LKA", "name": "Sri Lanka", "region": "South Asia"},
            {"code": "MMR", "name": "Myanmar", "region": "Southeast Asia"},
            {"code": "AFG", "name": "Afghanistan", "region": "South Asia"},
            {"code": "USA", "name": "United States", "region": "North America"},
            {"code": "RUS", "name": "Russia", "region": "Eastern Europe"},
        ]
        
        for country_data in countries:
            country = Country(**country_data)
            db.add(country)
        
        db.commit()
        logger.info(f"Seeded {len(countries)} countries")
        
    except Exception as e:
        logger.error(f"Error seeding countries: {e}")
        db.rollback()
    finally:
        db.close()


def init_database():
    """Initialize both databases"""
    logger.info("Starting database initialization...")
    init_postgres()
    init_mongodb()
    seed_countries()
    logger.info("Database initialization completed")


if __name__ == "__main__":
    init_database()
