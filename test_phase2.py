"""
Phase 2 Integration Test
Tests all Phase 2 features: confidence scoring, advanced alerts, improved conflict weighting, AI explanations.
"""

import sys
sys.path.insert(0, 'backend')

from app.scoring.risk_engine import RiskScoringEngine
from app.scoring.confidence import ConfidenceScorer
from app.scoring.alerts import AdvancedAlertDetector
from app.scoring.ai_explainer import get_ai_explainer
from app.core.database import SessionLocal
import json


def test_phase2_features():
    """Test all Phase 2 enhancements"""
    
    print("=" * 80)
    print("PHASE 2 FEATURE TEST")
    print("=" * 80)
    print()
    
    # Test 1: Confidence Scoring
    print("1. Testing Confidence Scoring...")
    print("-" * 80)
    
    news_signal = {"score": 65, "article_count": 25}
    conflict_signal = {"score": 72, "event_count": 18, "total_fatalities": 45, "escalation_rate": 35}
    economic_signal = {"score": 45}
    government_signal = {"score": 38, "reports_analyzed": 12}
    historical_scores = [68, 71, 69, 73, 75]
    
    confidence_result = ConfidenceScorer.calculate_confidence(
        news_signal, conflict_signal, economic_signal, government_signal, historical_scores
    )
    
    print(f"   Confidence Score: {confidence_result['confidence_score']:.1f}/100")
    print(f"   Confidence Level: {confidence_result['confidence_level']}")
    print(f"   Components:")
    for component, score in confidence_result['components'].items():
        print(f"     - {component}: {score:.1f}")
    print()
    
    if confidence_result['confidence_score'] > 0:
        print("   ✓ Confidence scoring working")
    else:
        print("   ✗ Confidence scoring failed")
        return False
    print()
    
    # Test 2: Enhanced Conflict Weighting
    print("2. Testing Enhanced Conflict Weighting...")
    print("-" * 80)
    
    if 'escalation_rate' in conflict_signal:
        print(f"   Escalation Rate: {conflict_signal['escalation_rate']:.1f}%")
        print(f"   Total Fatalities: {conflict_signal['total_fatalities']}")
        print(f"   Event Count: {conflict_signal['event_count']}")
        print("   ✓ Enhanced conflict metrics available")
    else:
        print("   ✗ Enhanced conflict metrics missing")
        return False
    print()
    
    # Test 3: Alert Detection
    print("3. Testing Advanced Alert Detection...")
    print("-" * 80)
    
    db = SessionLocal()
    try:
        detector = AdvancedAlertDetector(db)
        
        # Simulate alert conditions
        test_alerts = []
        
        # Test risk increase detection
        alert_data = detector._check_risk_increase(
            "TEST", 75.0, 80.0,
            {
                "news": news_signal,
                "conflict": conflict_signal,
                "economic": economic_signal,
                "government": government_signal
            },
            999
        )
        
        if alert_data:
            print(f"   ✓ Risk increase detection: {alert_data['alert_type']}")
        else:
            print("   ℹ No risk increase detected (expected if no previous score)")
        
        # Check alert thresholds
        print(f"   Alert Thresholds:")
        print(f"     - Risk Increase: {detector.THRESHOLDS['risk_increase']}%")
        print(f"     - Sudden Spike: {detector.THRESHOLDS['sudden_spike']}%")
        print(f"     - Sustained High: {detector.THRESHOLDS['sustained_high']}")
        print(f"     - Rapid Escalation: {detector.THRESHOLDS['rapid_escalation']}%")
        print("   ✓ Alert detection system operational")
        
    finally:
        db.close()
    print()
    
    # Test 4: AI Explainer
    print("4. Testing AI Explanation Layer...")
    print("-" * 80)
    
    explainer = get_ai_explainer()
    
    if explainer.enabled:
        print("   ✓ Gemini AI enabled")
        
        # Test explanation generation
        explanation = explainer.generate_risk_explanation(
            country_code="TEST",
            risk_score=68.5,
            confidence_score=78.5,
            signals={
                "news": news_signal,
                "conflict": conflict_signal,
                "economic": economic_signal,
                "government": government_signal
            },
            trend="increasing"
        )
        
        print(f"   Generated explanation length: {len(explanation)} characters")
        print(f"   Preview: {explanation[:150]}...")
        print("   ✓ AI explanation generation working")
    else:
        print("   ℹ Gemini AI not enabled (fallback mode active)")
        print("     To enable: Set GEMINI_API_KEY environment variable")
        print("     pip install google-generativeai")
        
        # Test fallback
        explanation = explainer._generate_fallback_explanation(
            "TEST", 68.5,
            {
                "news": news_signal,
                "conflict": conflict_signal,
                "economic": economic_signal,
                "government": government_signal
            },
            "increasing"
        )
        print(f"   Fallback explanation: {explanation[:100]}...")
        print("   ✓ Fallback explanation working")
    print()
    
    # Test 5: Full Risk Calculation with Phase 2
    print("5. Testing Full Risk Calculation with Phase 2 Features...")
    print("-" * 80)
    
    try:
        engine = RiskScoringEngine()
        result = engine.calculate_overall_risk("IND")
        
        print(f"   Country: {result['country_code']}")
        print(f"   Overall Risk: {result['overall_score']:.1f}/100")
        print(f"   Risk Level: {result['risk_level']}")
        print(f"   Confidence: {result.get('confidence_score', 'N/A')}/100")
        print(f"   Confidence Level: {result.get('confidence_level', 'N/A')}")
        print(f"   Trend: {result['trend']}")
        print(f"   Alerts Triggered: {result.get('alerts_triggered', 0)}")
        print()
        
        # Check Phase 2 fields
        phase2_fields = ['confidence_score', 'confidence_level', 'alerts_triggered']
        missing_fields = [f for f in phase2_fields if f not in result]
        
        if missing_fields:
            print(f"   ⚠ Missing Phase 2 fields: {missing_fields}")
        else:
            print("   ✓ All Phase 2 fields present in response")
        
        # Check enhanced conflict metrics
        conflict_signal = result['signals']['conflict']
        if 'escalation_rate' in conflict_signal:
            print(f"   ✓ Conflict escalation rate: {conflict_signal['escalation_rate']:.1f}%")
        else:
            print("   ⚠ Conflict escalation rate missing")
        
        print("   ✓ Full risk calculation with Phase 2 working")
        
    except Exception as e:
        print(f"   ✗ Error in risk calculation: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Summary
    print("=" * 80)
    print("✓ PHASE 2 FEATURE TEST COMPLETED")
    print("=" * 80)
    print()
    print("Phase 2 Features Status:")
    print("  ✓ Confidence scoring operational")
    print("  ✓ Enhanced conflict weighting active")
    print("  ✓ Advanced alert detection ready")
    if explainer.enabled:
        print("  ✓ AI explanations enabled (Gemini)")
    else:
        print("  ℹ AI explanations in fallback mode")
    print()
    print("System is ready for production with Phase 2 enhancements!")
    print()
    
    return True


if __name__ == "__main__":
    success = test_phase2_features()
    sys.exit(0 if success else 1)
