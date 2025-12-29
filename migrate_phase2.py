"""
Phase 2 Database Migration
Adds new columns for confidence scoring and AI explanations.

Run with: python migrate_phase2.py
"""

import sys
sys.path.insert(0, 'backend')

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.core.logging import setup_logger

logger = setup_logger(__name__)


def migrate_phase2():
    """Add Phase 2 columns to existing tables"""
    
    print("=" * 80)
    print("PHASE 2 DATABASE MIGRATION")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    
    try:
        # 1. Add confidence_score to risk_scores table
        print("1. Adding confidence_score column to risk_scores...")
        try:
            db.execute(text("""
                ALTER TABLE risk_scores 
                ADD COLUMN confidence_score FLOAT DEFAULT 0.0
            """))
            db.commit()
            print("   ✓ confidence_score column added")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("   ℹ confidence_score column already exists")
                db.rollback()
            else:
                raise
        
        # 2. Add confidence_score to alerts table
        print("2. Adding confidence_score column to alerts...")
        try:
            db.execute(text("""
                ALTER TABLE alerts 
                ADD COLUMN confidence_score FLOAT DEFAULT 0.0
            """))
            db.commit()
            print("   ✓ confidence_score column added")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("   ℹ confidence_score column already exists")
                db.rollback()
            else:
                raise
        
        # 3. Add change_percentage to alerts table
        print("3. Adding change_percentage column to alerts...")
        try:
            db.execute(text("""
                ALTER TABLE alerts 
                ADD COLUMN change_percentage FLOAT
            """))
            db.commit()
            print("   ✓ change_percentage column added")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("   ℹ change_percentage column already exists")
                db.rollback()
            else:
                raise
        
        # 4. Add ai_explanation to alerts table
        print("4. Adding ai_explanation column to alerts...")
        try:
            db.execute(text("""
                ALTER TABLE alerts 
                ADD COLUMN ai_explanation TEXT
            """))
            db.commit()
            print("   ✓ ai_explanation column added")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("   ℹ ai_explanation column already exists")
                db.rollback()
            else:
                raise
        
        print()
        print("=" * 80)
        print("✓ PHASE 2 MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()
        print("New features enabled:")
        print("  • Confidence scoring for risk assessments")
        print("  • Advanced alert detection (spike, sustained, escalation)")
        print("  • Change percentage tracking")
        print("  • AI-generated explanations (requires Gemini API)")
        print()
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        print()
        print("✗ MIGRATION FAILED")
        print(f"Error: {e}")
        print()
        sys.exit(1)
    
    finally:
        db.close()


if __name__ == "__main__":
    migrate_phase2()
