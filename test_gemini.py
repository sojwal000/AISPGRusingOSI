"""Quick test for Gemini AI integration"""
import sys
sys.path.insert(0, 'backend')

from dotenv import load_dotenv
load_dotenv()

from app.scoring.ai_explainer import get_ai_explainer

print("Testing Gemini AI Integration...")
print("=" * 60)

explainer = get_ai_explainer()

print(f"\nGemini AI Enabled: {explainer.enabled}")

if explainer.enabled:
    print("\n✓ Gemini API initialized successfully!")
    print("\nGenerating test explanation...")
    
    explanation = explainer.generate_risk_explanation(
        country_code="IND",
        risk_score=68.5,
        confidence_score=78.5,
        signals={
            "news": {"score": 65, "article_count": 25},
            "conflict": {"score": 72, "event_count": 18, "total_fatalities": 45, "escalation_rate": 35},
            "economic": {"score": 45},
            "government": {"score": 38, "reports_analyzed": 12}
        },
        trend="increasing"
    )
    
    print("\n" + "=" * 60)
    print("AI-Generated Explanation:")
    print("=" * 60)
    print(explanation)
    print("=" * 60)
    print("\n✓ Gemini AI is working perfectly!")
else:
    print("\n✗ Gemini AI not enabled")
    print("Check that GEMINI_API_KEY is set in .env file")
