# Phase 2 - Quick Reference Card

## Installation

```bash
# Database migration (required)
python migrate_phase2.py

# AI features (optional)
pip install google-generativeai
set GEMINI_API_KEY=your_api_key_here  # Windows
export GEMINI_API_KEY=your_api_key_here  # Linux/Mac
```

## Testing

```bash
# Full Phase 2 test
python test_phase2.py
```

## New Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `scoring/confidence.py` | Confidence scoring | ✅ Ready |
| `scoring/alerts.py` | Advanced alerts | ✅ Ready |
| `scoring/ai_explainer.py` | AI explanations | ✅ Ready (fallback) |

## Alert Types

| Type | Threshold | Severity | Detection Window |
|------|-----------|----------|------------------|
| risk_increase | >15% | Medium-Critical | 7 days |
| sudden_spike | >30% | High-Critical | 24 hours |
| sustained_high | >70 | Critical | 48 hours |
| rapid_escalation | >50% | Critical | 6 hours |

## Confidence Components

| Component | Weight | What it measures |
|-----------|--------|------------------|
| Data Source Count | 30% | # of active data sources |
| Data Freshness | 25% | Recency of data |
| Signal Consistency | 25% | Agreement between signals |
| Historical Validation | 20% | Pattern stability |

## API Response (New Fields)

```json
{
  "confidence_score": 77.0,      // NEW: 0-100
  "confidence_level": "high",     // NEW: very_low/low/medium/high/very_high
  "alerts_triggered": 0,          // NEW: Count of alerts
  "signals": {
    "conflict": {
      "escalation_rate": 0.0,     // NEW: % change
      "high_casualty_events": 0   // NEW: Count
    }
  }
}
```

## Usage

### Calculate Risk with Confidence
```python
from backend.app.scoring.risk_engine import RiskScoringEngine

engine = RiskScoringEngine()
result = engine.calculate_overall_risk("IND")
# Now includes confidence_score, confidence_level, alerts_triggered
```

### Get AI Explanation
```python
from backend.app.scoring.ai_explainer import get_ai_explainer

explainer = get_ai_explainer()
text = explainer.generate_risk_explanation(
    "IND", 68.5, 78.0, signals, "increasing"
)
```

### Detect Alerts
```python
from backend.app.scoring.alerts import AdvancedAlertDetector

detector = AdvancedAlertDetector(db)
alerts = detector.detect_all_alerts(
    "IND", 75.5, 82.0, signals, risk_id
)
```

## Database Columns Added

**risk_scores**:
- `confidence_score` FLOAT

**alerts**:
- `confidence_score` FLOAT
- `change_percentage` FLOAT
- `ai_explanation` TEXT

## Performance

- Confidence: ~5-10ms
- Alerts: ~15-25ms
- AI (Gemini): ~500-1500ms
- **Total**: <50ms (without AI)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Confidence always 50 | Need 7+ days history |
| AI not working | Install google-generativeai + set API key |
| No alerts | Normal if no previous scores |
| Escalation 0 | Normal for stable situations |

## Files

- 📄 Full docs: `PHASE2_IMPLEMENTATION.md`
- 📄 Summary: `PHASE2_SUMMARY.md`
- 🧪 Tests: `test_phase2.py`
- 🔧 Migration: `migrate_phase2.py`

## Status: ✅ Production Ready
