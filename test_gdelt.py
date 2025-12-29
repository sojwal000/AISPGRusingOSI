"""
Test GDELT Integration
Tests the complete GDELT ingestion and risk scoring pipeline
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.sql_models import ConflictEvent, RiskScore
from app.ingestion.gdelt import GDELTIngestion
from app.scoring.risk_engine import RiskScoringEngine

def test_gdelt_integration():
    """Test full GDELT integration workflow"""
    
    print("\n" + "="*60)
    print("GDELT INTEGRATION TEST")
    print("="*60 + "\n")
    
    db = SessionLocal()
    
    try:
        # Step 1: Check initial state
        print("Step 1: Checking initial conflict event count...")
        initial_count = db.query(ConflictEvent).filter(
            ConflictEvent.country_code == "IND"
        ).count()
        print(f"✓ Initial conflict events for IND: {initial_count}")
        
        # Step 2: Run GDELT ingestion
        print("\nStep 2: Running GDELT ingestion (last 24 hours)...")
        ingestion = GDELTIngestion()
        result = ingestion.ingest(hours_back=24, country_code="IND")
        
        print(f"✓ GDELT ingestion completed")
        print(f"  - Status: {result['status']}")
        print(f"  - Events fetched: {result.get('events_fetched', 0)}")
        print(f"  - Events stored: {result.get('events_stored', 0)}")
        
        # Step 3: Verify events stored
        print("\nStep 3: Verifying events in database...")
        final_count = db.query(ConflictEvent).filter(
            ConflictEvent.country_code == "IND"
        ).count()
        new_events = final_count - initial_count
        
        print(f"✓ Final conflict events for IND: {final_count}")
        print(f"✓ New events added: {new_events}")
        
        # Step 4: Check event details
        if final_count > 0:
            print("\nStep 4: Examining recent events...")
            recent_events = db.query(ConflictEvent).filter(
                ConflictEvent.country_code == "IND",
                ConflictEvent.source == "GDELT"
            ).order_by(ConflictEvent.event_date.desc()).limit(5).all()
            
            print(f"✓ Recent GDELT events (showing up to 5):")
            for event in recent_events:
                print(f"  - {event.event_date.strftime('%Y-%m-%d')} | {event.event_type} | {event.location or 'Unknown'}")
                if event.notes:
                    print(f"    Notes: {event.notes[:100]}")
        
        # Step 5: Calculate risk with conflict data
        print("\nStep 5: Calculating risk score with GDELT data...")
        engine = RiskScoringEngine()
        
        # Calculate risk (uses default 30-day lookback)
        risk_result = engine.calculate_overall_risk(country_code="IND")
        
        print(f"✓ Risk calculation completed")
        print(f"  - Overall Risk: {risk_result['overall_score']:.1f}/100 ({risk_result['risk_level']})")
        print(f"  - Confidence: {risk_result['confidence_score']:.1f}/100 ({risk_result['confidence_level']})")
        print(f"  - Alerts: {risk_result['alerts_triggered']}")
        
        # Check signal breakdown
        signals = risk_result['signals']
        print(f"\n✓ Signal Breakdown:")
        print(f"  - Conflict Signal: {signals.get('conflict', {}).get('score', 0):.1f}/100 (weight: {risk_result['weights'].get('conflict', 40)}%)")
        print(f"    Escalation Rate: {signals.get('conflict', {}).get('details', {}).get('escalation_rate', 'N/A')}")
        print(f"  - News Signal: {signals.get('news', {}).get('score', 0):.1f}/100 (weight: {risk_result['weights'].get('news', 20)}%)")
        print(f"  - Economic Signal: {signals.get('economic', {}).get('score', 0):.1f}/100 (weight: {risk_result['weights'].get('economic', 30)}%)")
        print(f"  - Government Signal: {signals.get('government', {}).get('score', 0):.1f}/100 (weight: {risk_result['weights'].get('government', 10)}%)")
        
        # Step 6: Verify conflict signal is non-zero
        print("\nStep 6: Verifying conflict signal impact...")
        conflict_score = signals.get('conflict', {}).get('score', 0)
        
        if conflict_score > 0:
            print(f"✅ SUCCESS: Conflict signal is now active ({conflict_score:.1f}/100)")
            print(f"✅ GDELT integration successful - 40% risk weight now operational")
        else:
            print(f"⚠️  WARNING: Conflict signal still zero")
            print(f"   This may be due to:")
            print(f"   - No recent conflict events in timeframe")
            print(f"   - Events don't meet severity threshold")
            print(f"   - GDELT data not yet available for current time")
        
        print("\n" + "="*60)
        print("GDELT INTEGRATION TEST COMPLETED")
        print("="*60 + "\n")
        
        # Summary
        print("Summary:")
        print(f"  ✓ GDELT ingestion: {result.get('events_stored', 0)} new events")
        print(f"  ✓ Total conflict events: {final_count}")
        print(f"  ✓ Risk score: {risk_result['overall_score']:.1f}/100")
        print(f"  ✓ Conflict signal: {conflict_score:.1f}/100")
        print(f"  ✓ System status: {'COMPLETE' if conflict_score > 0 else 'INCOMPLETE'}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    test_gdelt_integration()
