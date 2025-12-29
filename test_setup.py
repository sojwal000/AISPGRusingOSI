"""
Quick test script to verify system setup.
Run this after installation to check if everything is configured correctly.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test if all required packages are installed"""
    print("\n[1/5] Testing Python package imports...")
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import pymongo
        import pandas
        import feedparser
        import requests
        print("  ✓ All required packages imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        print("  → Run: pip install -r requirements.txt")
        return False


def test_config():
    """Test if configuration is set up"""
    print("\n[2/5] Testing configuration...")
    try:
        from app.core.config import get_settings
        settings = get_settings()
        
        if not settings.POSTGRES_PASSWORD:
            print("  ⚠ POSTGRES_PASSWORD not set in .env")
            return False
        
        print("  ✓ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"  ✗ Configuration error: {e}")
        print("  → Create .env file from .env.example")
        return False


def test_postgres():
    """Test PostgreSQL connection"""
    print("\n[3/5] Testing PostgreSQL connection...")
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print("  ✓ PostgreSQL connection successful")
        return True
    except Exception as e:
        print(f"  ✗ PostgreSQL connection failed: {e}")
        print("  → Check if PostgreSQL is running")
        print("  → Verify credentials in .env")
        print("  → Run: psql -U postgres -c \"CREATE DATABASE geopolitical_risk;\"")
        return False


def test_mongodb():
    """Test MongoDB connection"""
    print("\n[4/5] Testing MongoDB connection...")
    try:
        from app.core.database import mongo_client
        
        # Ping MongoDB
        mongo_client.admin.command('ping')
        
        print("  ✓ MongoDB connection successful")
        return True
    except Exception as e:
        print(f"  ✗ MongoDB connection failed: {e}")
        print("  → Check if MongoDB is running")
        print("  → Verify connection string in .env")
        return False


def test_database_schema():
    """Test if database schema is initialized"""
    print("\n[5/5] Testing database schema...")
    try:
        from app.core.database import SessionLocal
        from app.models.sql_models import Country
        
        db = SessionLocal()
        country_count = db.query(Country).count()
        db.close()
        
        if country_count > 0:
            print(f"  ✓ Database schema initialized ({country_count} countries found)")
            return True
        else:
            print("  ⚠ Database schema exists but no countries found")
            print("  → Run: python setup_db.py")
            return False
    except Exception as e:
        print(f"  ✗ Database schema test failed: {e}")
        print("  → Run: python setup_db.py")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("  GEOPOLITICAL RISK ANALYSIS SYSTEM - VERIFICATION TEST")
    print("=" * 70)
    
    results = {
        "imports": test_imports(),
        "config": test_config(),
        "postgres": test_postgres(),
        "mongodb": test_mongodb(),
        "schema": test_database_schema()
    }
    
    print("\n" + "=" * 70)
    print("  TEST RESULTS")
    print("=" * 70)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {test_name.upper():.<30} {status}")
    
    print("=" * 70)
    print(f"  Overall: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n✅ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. Run pipeline: python run_pipeline.py")
        print("  2. Start API: python run_api.py")
    else:
        print("\n⚠ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  • Install dependencies: pip install -r requirements.txt")
        print("  • Configure .env: copy .env.example .env")
        print("  • Initialize database: python setup_db.py")
        print("  • Start services: PostgreSQL and MongoDB")
    
    print()
    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
