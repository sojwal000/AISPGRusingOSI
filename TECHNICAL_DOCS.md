# Phase 1 Implementation - Technical Documentation

## Overview

Phase 1 implements the core data ingestion and deterministic risk scoring pipeline for India-focused geopolitical risk analysis using open-source intelligence (OSINT).

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Sources                             │
│  • News RSS Feeds (India-focused)                           │
│  • ACLED Conflict Events API                                │
│  • World Bank Economic Indicators API                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Ingestion Layer                             │
│  • news_rss.py - RSS feed parser                            │
│  • acled.py - Conflict event ingestion                      │
│  • worldbank.py - Economic indicator fetcher                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Storage Layer                               │
│  • PostgreSQL - Structured data (scores, events, indicators)│
│  • MongoDB - Unstructured data (news articles)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               Risk Scoring Engine                            │
│  • Deterministic weighted algorithm                         │
│  • Signal extraction and normalization                      │
│  • Explainable score calculation                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Output Layer                                │
│  • REST API (FastAPI)                                       │
│  • Console Display                                          │
│  • JSON Export                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### PostgreSQL Tables

#### countries

- Stores country master data
- Fields: id, code (ISO 3-letter), name, region, created_at

#### risk_scores

- Historical risk scores for each country
- Fields: country_code, date, overall_score, signal scores, trend, metadata
- Indexes: country_code, date, (country_code, date)

#### alerts

- Generated alerts for threshold breaches
- Fields: country_code, alert_type, severity, title, description, risk_score, triggered_at, status

#### conflict_events

- ACLED conflict and protest events
- Fields: external_id, country_code, event_date, event_type, actors, location, fatalities
- Indexes: country_code, event_date, (country_code, event_date)

#### economic_indicators

- World Bank economic indicators over time
- Fields: country_code, indicator_code, indicator_name, date, value, source
- Indexes: country_code, indicator_code, date, (country_code, indicator_code, date)

### MongoDB Collections

#### news_articles

- Raw news articles from RSS feeds
- Fields: title, content, url, source, published_date, countries[], keywords[], metadata
- Indexes: url (unique), published_date, countries

#### government_reports

- Government and international reports (Phase 2)
- Fields: title, content, url, source, report_type, published_date, countries[]

#### raw_data_cache

- Cache of raw API responses for debugging
- Fields: source_name, data_type, raw_data, fetch_timestamp

---

## Risk Scoring Algorithm

### Signal Weights

```python
WEIGHTS = {
    "news_signal": 0.20,      # 20% weight
    "conflict_signal": 0.40,   # 40% weight (highest)
    "economic_signal": 0.30,   # 30% weight
    "government_signal": 0.10  # 10% weight (Phase 2)
}
```

### Overall Score Calculation

```
Overall Score = (News Score × 0.20) +
                (Conflict Score × 0.40) +
                (Economic Score × 0.30) +
                (Government Score × 0.10)
```

---

## Signal Calculation Details

### 1. News Signal (0-100)

**Data Source:** RSS feeds from 5 India-focused news sources

**Calculation:**

```
Volume Score = min(article_count / 20.0 × 50, 50)
Negative Score = (negative_count / article_count) × 50
News Score = Volume Score + Negative Score
```

**Negative Keywords:**

- protest, riot, violence, conflict, crisis
- terrorism, attack, strike, unrest, tension
- war, emergency, threat, sanction

**Time Window:** Last 7 days

**Interpretation:**

- High volume + negative content = Higher risk
- Detects emerging tensions through media coverage

---

### 2. Conflict Signal (0-100)

**Data Source:** ACLED conflict events database

**Event Type Severity Weights:**

- Battles: 10
- Violence against civilians: 10
- Explosions/Remote violence: 9
- Riots: 7
- Protests: 3
- Strategic developments: 2

**Calculation:**

```
Frequency Score = min(event_count / 10.0 × 40, 40)
Severity Score = (avg_severity / 10.0) × 30
Fatality Score = min(total_fatalities / 50.0 × 30, 30)
Conflict Score = Frequency Score + Severity Score + Fatality Score
```

**Time Window:** Last 30 days

**Interpretation:**

- More frequent, severe, deadly events = Higher risk
- Highest-weighted signal due to direct impact

---

### 3. Economic Signal (0-100)

**Data Source:** World Bank API indicators

**Indicators Used:**

1. GDP Growth Rate
2. Inflation (CPI)
3. Unemployment Rate
4. Foreign Reserves (optional)
5. Government Debt (optional)

**Sub-Score Calculations:**

**GDP Growth Score:**

- Negative growth: 100
- 0-2%: 70
- 2-4%: 40
- 4-6%: 20
- > 6%: 10

**Inflation Score:**

- > 10%: 100
- 7-10%: 70
- 5-7%: 40
- 3-5%: 20
- <3%: 10

**Unemployment Score:**

- > 15%: 100
- 10-15%: 70
- 7-10%: 50
- 5-7%: 30
- <5%: 10

**Economic Score = (GDP Score × 0.4) + (Inflation Score × 0.4) + (Unemployment Score × 0.2)**

**Time Window:** Last 2 years

**Interpretation:**

- Economic stress often precedes instability
- Slower-moving but important signal

---

### 4. Government Signal (0-100)

**Status:** Placeholder in Phase 1

**Planned for Phase 2:**

- Analysis of government press releases
- Emergency declarations
- Election announcements
- Diplomatic actions

---

## Risk Level Classification

| Score Range | Risk Level | Color Code  | Alert Threshold |
| ----------- | ---------- | ----------- | --------------- |
| 75-100      | Critical   | Red         | Yes             |
| 60-74       | High       | Orange      | Yes             |
| 40-59       | Medium     | Yellow      | No              |
| 20-39       | Low        | Light Green | No              |
| 0-19        | Minimal    | Green       | No              |

---

## API Endpoints Reference

### GET /api/v1/countries

Returns list of all countries in the system.

**Response:**

```json
[
  {
    "id": 1,
    "code": "IND",
    "name": "India",
    "region": "South Asia"
  }
]
```

---

### GET /api/v1/risk-score/{country_code}

Returns latest risk score for specified country.

**Response:**

```json
{
  "country_code": "IND",
  "overall_score": 45.23,
  "risk_level": "medium",
  "trend": "stable",
  "date": "2025-12-25T10:30:00",
  "signals": {
    "news": 38.5,
    "conflict": 52.0,
    "economic": 41.2,
    "government": 0.0
  }
}
```

---

### GET /api/v1/signals/{country_code}

Returns detailed signal breakdown with calculation metadata.

**Response:**

```json
{
  "country_code": "IND",
  "calculated_at": "2025-12-25T10:30:00",
  "overall_score": 45.23,
  "signals": {
    "news": {
      "score": 38.5,
      "weight": 0.2,
      "details": {
        "article_count": 42,
        "negative_count": 15,
        "days_analyzed": 7
      }
    },
    "conflict": {
      "score": 52.0,
      "weight": 0.4,
      "details": {
        "event_count": 23,
        "total_fatalities": 8,
        "avg_severity": 5.2,
        "days_analyzed": 30
      }
    }
  }
}
```

---

## Data Flow

### Pipeline Execution Flow

```
1. run_pipeline.py invoked
   ↓
2. NewsRSSIngestion.ingest_all_feeds()
   - Fetches from 5 RSS sources
   - Parses articles
   - Stores in MongoDB
   ↓
3. ACLEDIngestion.ingest_country("IND")
   - Fetches conflict events via API
   - Stores in PostgreSQL
   ↓
4. WorldBankIngestion.ingest_country("IND")
   - Fetches 5 economic indicators
   - Stores in PostgreSQL
   ↓
5. RiskScoringEngine.calculate_overall_risk("IND")
   - Calculates news signal
   - Calculates conflict signal
   - Calculates economic signal
   - Combines with weights
   - Stores risk_score in PostgreSQL
   - Checks alert thresholds
   - Creates alerts if needed
   ↓
6. Display results to console
```

---

## Configuration

### Environment Variables (.env)

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=geopolitical_risk
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# MongoDB
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DB=geopolitical_risk

# ACLED API (optional - uses sample data if not provided)
ACLED_API_KEY=your_key
ACLED_EMAIL=your_email

# World Bank (no key required)
WORLD_BANK_BASE_URL=https://api.worldbank.org/v2

# System
LOG_LEVEL=INFO
INDIA_COUNTRY_CODE=IND
```

---

## Key Design Principles

### 1. Deterministic Scoring

- No machine learning models in Phase 1
- All calculations use explicit rules and weights
- Completely reproducible results
- Easy to audit and explain

### 2. Source Transparency

- All data sources are documented
- Raw data is preserved
- Calculation metadata stored with each score

### 3. Explainability

- Each score includes detailed breakdown
- Signal contributions are visible
- Evidence is traceable to source

### 4. Fallback Mechanisms

- System generates sample data if APIs unavailable
- Graceful degradation if data sources fail
- Continues with partial data

---

## Error Handling

### Ingestion Failures

- Logged but don't stop pipeline
- Sample data used as fallback
- Partial ingestion is acceptable

### Scoring Failures

- Missing data results in neutral scores (50)
- System continues with available signals
- Metadata indicates data gaps

### Database Failures

- Connection errors logged
- Transaction rollbacks on errors
- Graceful shutdown

---

## Performance Considerations

### Data Volume (India)

- News: ~50-100 articles/day
- Conflict events: ~10-30 events/month
- Economic indicators: 5 indicators/year

### Processing Time

- News ingestion: ~10-30 seconds
- ACLED ingestion: ~5-15 seconds
- World Bank ingestion: ~10-20 seconds
- Risk scoring: <5 seconds

**Total Pipeline:** ~1-2 minutes

### Storage Requirements

- PostgreSQL: <100 MB/year
- MongoDB: <500 MB/year

---

## Testing

### Manual Testing

```bash
# Test individual components
cd backend
python -m app.ingestion.news_rss
python -m app.ingestion.acled
python -m app.ingestion.worldbank
python -m app.scoring.risk_engine

# Test full pipeline
python run_pipeline.py

# Test API
python run_api.py
# Visit http://localhost:8000/docs
```

### Validation Checks

1. **Data Ingestion:**

   - Verify counts match expectations
   - Check for duplicate prevention
   - Validate date parsing

2. **Risk Scoring:**

   - Verify score is 0-100
   - Check signal weights sum to 1.0
   - Validate trend calculation

3. **API Responses:**
   - Test all endpoints
   - Verify JSON structure
   - Check error handling

---

## Limitations (Phase 1)

1. **No Authentication:** API is publicly accessible
2. **No Caching:** Each request recalculates
3. **No Real-time Updates:** Manual pipeline execution required
4. **Limited NLP:** Basic keyword matching for news analysis
5. **Single Country Focus:** Optimized for India
6. **No Frontend:** Console and API only
7. **No AI Assistant:** Phase 3 feature

---

## Future Enhancements (Phase 2+)

1. **Automated Scheduling:** Cron jobs for daily ingestion
2. **Advanced NLP:** Sentiment analysis, entity extraction
3. **Real-time Monitoring:** WebSocket updates
4. **Frontend Dashboard:** React-based visualization
5. **Multi-country Comparison:** Regional analysis
6. **AI Assistant:** Gemini + LangChain explanations
7. **Authentication:** User management and API keys
8. **Alert System:** Email/SMS notifications

---

## Maintenance

### Daily Tasks

- None (Phase 1 is manual)

### Weekly Tasks

- Run pipeline for updated scores
- Review alerts
- Check data quality

### Monthly Tasks

- Database backup
- Performance review
- Update RSS feeds if needed

---

## Troubleshooting

### Common Issues

**1. Database Connection Failed**

- Check PostgreSQL/MongoDB services are running
- Verify credentials in .env
- Test connection with psql/mongosh

**2. API Key Issues**

- ACLED: Check key validity, email match
- System will use sample data if key invalid

**3. Import Errors**

- Ensure you're in project root
- Check Python path
- Reinstall dependencies

**4. Empty Results**

- Run setup_db.py first
- Check if countries are seeded
- Verify internet connectivity for data fetching

---

## Support and Contact

For technical issues:

1. Check SETUP_GUIDE.md
2. Review logs in console
3. Verify configuration
4. Check database connectivity

---

**Document Version:** 1.0  
**Last Updated:** December 25, 2025  
**Phase:** 1 - Data Ingestion and Risk Scoring
