from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient
from .config import get_settings

settings = get_settings()

# PostgreSQL
engine = create_engine(settings.postgres_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# MongoDB
mongo_client = MongoClient(settings.mongodb_url)
mongo_db = mongo_client[settings.MONGODB_DB]


def get_mongo_db():
    """Get MongoDB database instance"""
    return mongo_db
