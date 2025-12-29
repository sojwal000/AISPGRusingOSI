"""
Database initialization runner.
Sets up PostgreSQL and MongoDB schemas with seed data.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.scripts.init_db import init_database


if __name__ == "__main__":
    print("Initializing databases...")
    init_database()
    print("Database initialization complete!")
