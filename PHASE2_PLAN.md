# Phase 2 Implementation Plan

## Overview

Phase 2 adds AI-powered analysis, government data scraping, predictive modeling, and enhanced alerting to the geopolitical risk scoring system.

## Core Features

### 1. AI/ML Integration 🤖

#### 1.1 Sentiment Analysis

- **Library:** `transformers` (HuggingFace)
- **Model:** `distilbert-base-uncased-finetuned-sst-2-english` for news sentiment
- **Purpose:** Replace keyword-based news scoring with ML sentiment analysis
- **Implementation:**
  - Analyze news article titles and content
  - Generate sentiment scores (-1 to +1)
  - Weight by article recency
  - Integrate into news signal calculation

#### 1.2 Named Entity Recognition (NER)

- **Model:** `bert-base-NER` or spaCy
- **Purpose:** Extract entities (people, organizations, locations, events)
- **Use Cases:**
  - Identify key actors in conflicts
  - Track mentioned politicians/organizations
  - Geographic risk clustering

#### 1.3 Predictive Risk Modeling

- **Approach:** Time-series forecasting
- **Models:** LSTM or Prophet for trend prediction
- **Features:**
  - Historical risk scores
  - Seasonal patterns
  - Anomaly detection (isolation forest)
  - Confidence intervals

### 2. Government Data Sources 🏛️

#### 2.1 Indian Government Sources

- **PIB (Press Information Bureau):** https://pib.gov.in/
  - Press releases
  - Government announcements
  - Ministry updates
- **MEA (Ministry of External Affairs):** https://www.mea.gov.in/

  - Diplomatic statements
  - Foreign policy updates
  - International relations

- **PMO (Prime Minister's Office):** https://www.pmo.gov.in/
  - Official statements
  - Policy announcements

#### 2.2 Scraping Strategy

- **Library:** `beautifulsoup4` + `selenium` (for dynamic content)
- **Frequency:** Daily scheduled scraping
- **Storage:** MongoDB (raw HTML + parsed text)
- **Processing:**
  - Extract date, title, content
  - Classify by ministry/department
  - Tag by topic (security, economy, foreign policy)

#### 2.3 Government Signal Logic

- **Stability Indicators:**
  - Frequency of policy changes (high frequency = instability)
  - Tone of official statements (using sentiment)
  - International relations mentions (conflict keywords)
- **Scoring:**
  - Policy stability: 40%
  - Official sentiment: 30%
  - Diplomatic tensions: 30%

### 3. Enhanced Alerting System 🚨

#### 3.1 Real-time Monitoring

- **Background Task:** Celery + Redis
- **Frequency:** Every 15 minutes during market hours
- **Triggers:**
  - Score threshold breach (>75, >60, >40)
  - Sudden spike (>10 points in 24h)
  - Anomaly detection (3-sigma rule)

#### 3.2 Notification Channels

- **Email:** SMTP integration (SendGrid/AWS SES)
- **Webhook:** POST to configurable URLs
- **In-App:** Alert dashboard in API
- **Future:** SMS, Slack, Teams integration

#### 3.3 Alert Management

- **Priorities:** Critical > High > Medium > Low
- **States:** New → Acknowledged → Resolved → Archived
- **Features:**
  - Alert grouping (similar alerts within 1h)
  - Snooze/mute functionality
  - Alert history and analytics

### 4. Advanced Analytics 📈

#### 4.1 Temporal Analysis

- **Moving averages:** 7-day, 30-day, 90-day
- **Trend detection:** Linear regression on recent scores
- **Seasonality:** Identify recurring patterns
- **Volatility:** Standard deviation tracking

#### 4.2 Signal Correlation

- **Cross-correlation:** News vs Conflict lag analysis
- **Causality:** Granger causality tests
- **Feature importance:** Which signals drive score changes

#### 4.3 Confidence Scores

- **Data freshness:** Decay factor for old data
- **Data completeness:** Penalty for missing indicators
- **Model uncertainty:** Prediction intervals
- **Display:** Risk score ± confidence interval

## Technical Architecture

### New Dependencies

```txt
# AI/ML
transformers==4.36.0
torch==2.1.0
sentence-transformers==2.2.2
spacy==3.7.0
prophet==1.1.5
scikit-learn==1.4.0

# Web Scraping
beautifulsoup4==4.12.0
selenium==4.16.0
lxml==5.1.0
webdriver-manager==4.0.1

# Background Tasks
celery==5.3.0
redis==5.0.0

# Notifications
sendgrid==6.11.0
python-telegram-bot==20.7.0  # Optional

# Enhanced Analytics
statsmodels==0.14.0
plotly==5.18.0  # For visualization
```

### New Project Structure

```
backend/
  app/
    ml/
      __init__.py
      sentiment.py           # Sentiment analysis module
      ner.py                 # Named entity recognition
      prediction.py          # Predictive models
      anomaly.py            # Anomaly detection

    scraping/
      __init__.py
      government.py         # Government website scrapers
      scheduler.py          # Scraping schedule management
      parsers.py            # HTML parsing utilities

    tasks/
      __init__.py
      celery_app.py         # Celery configuration
      monitoring.py         # Background monitoring tasks
      alerts.py             # Alert generation tasks

    notifications/
      __init__.py
      email.py              # Email notifications
      webhook.py            # Webhook dispatcher
      telegram.py           # Telegram bot (optional)

    analytics/
      __init__.py
      temporal.py           # Time-series analysis
      correlation.py        # Signal correlation
      confidence.py         # Confidence interval calculation
```

### Database Schema Updates

#### New PostgreSQL Tables

```sql
-- Government Reports
CREATE TABLE government_reports (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,           -- 'PIB', 'MEA', 'PMO'
    report_date TIMESTAMP NOT NULL,
    title VARCHAR(500),
    url TEXT UNIQUE,
    category VARCHAR(100),                  -- 'security', 'economy', 'foreign_policy'
    sentiment_score FLOAT,                  -- -1 to +1
    importance_score FLOAT,                 -- 0 to 100
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sentiment Scores (for news articles)
CREATE TABLE sentiment_scores (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) REFERENCES news_articles(id),
    model_name VARCHAR(100),
    sentiment_label VARCHAR(20),            -- 'positive', 'negative', 'neutral'
    sentiment_score FLOAT,                  -- -1 to +1
    confidence FLOAT,                       -- 0 to 1
    created_at TIMESTAMP DEFAULT NOW()
);

-- Alert Notifications
CREATE TABLE alert_notifications (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id),
    channel VARCHAR(50),                    -- 'email', 'webhook', 'sms'
    recipient TEXT,
    sent_at TIMESTAMP,
    status VARCHAR(20),                     -- 'sent', 'failed', 'pending'
    error_message TEXT
);

-- Risk Predictions
CREATE TABLE risk_predictions (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(3),
    prediction_date TIMESTAMP NOT NULL,
    predicted_score FLOAT,
    confidence_lower FLOAT,
    confidence_upper FLOAT,
    model_name VARCHAR(100),
    features JSONB,                         -- Model input features
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### MongoDB Collections

```javascript
// Enhanced news_articles with ML features
{
    _id: ObjectId,
    // ... existing fields ...
    ml_analysis: {
        sentiment_score: -0.75,
        sentiment_label: "negative",
        entities: [
            {type: "PERSON", text: "Modi", confidence: 0.95},
            {type: "ORG", text: "BJP", confidence: 0.88}
        ],
        topics: ["politics", "security"],
        processed_at: ISODate("2025-12-25T08:00:00Z")
    }
}

// government_documents (full text storage)
{
    _id: ObjectId,
    source: "PIB",
    url: "https://pib.gov.in/...",
    report_date: ISODate("2025-12-25"),
    title: "Cabinet approves...",
    content: "Full text content...",
    html: "<html>...</html>",
    metadata: {
        ministry: "Ministry of Defence",
        category: "security",
        tags: ["defence", "procurement"]
    },
    parsed_at: ISODate("2025-12-25T08:00:00Z")
}
```

## Implementation Phases

### Phase 2.1: AI/ML Foundation (Week 1-2)

1. Install ML dependencies
2. Create sentiment analysis module
3. Integrate sentiment into news signal
4. Add NER for entity extraction
5. Update API to expose ML features

### Phase 2.2: Government Data (Week 2-3)

1. Build scrapers for PIB, MEA, PMO
2. Create parsing and storage logic
3. Implement government signal scoring
4. Add scheduler for daily scraping
5. API endpoints for government data

### Phase 2.3: Predictive Modeling (Week 3-4)

1. Collect sufficient historical data
2. Train time-series models (LSTM/Prophet)
3. Implement anomaly detection
4. Add confidence intervals
5. Create prediction API endpoints

### Phase 2.4: Enhanced Alerting (Week 4-5)

1. Set up Celery + Redis
2. Implement background monitoring
3. Build notification system (email + webhook)
4. Create alert management endpoints
5. Add alert dashboard

### Phase 2.5: Advanced Analytics (Week 5-6)

1. Temporal analysis (moving averages, trends)
2. Signal correlation analysis
3. Visualization endpoints (Plotly charts)
4. Confidence score calculation
5. Analytics dashboard

## Success Metrics

### Performance

- Sentiment analysis: <2 seconds per article
- Government scraping: Daily completion <10 minutes
- Risk prediction: <5 seconds
- Alert latency: <1 minute from trigger

### Accuracy

- Sentiment accuracy: >80% (validated against human labels)
- Prediction accuracy: RMSE <10 points
- Anomaly detection: <5% false positives
- Alert relevance: >90% actionable

### Coverage

- Government sources: 3+ official sources
- ML model coverage: 100% of news articles
- Prediction horizon: 7 days ahead
- Alert coverage: 24/7 monitoring

## Risk Mitigation

### Technical Risks

- **ML model performance:** Use pre-trained models, fine-tune if needed
- **Scraping reliability:** Implement retry logic, fallback sources
- **API rate limits:** Cache responses, respect robots.txt
- **Background task failures:** Use Celery retry mechanisms

### Operational Risks

- **False alerts:** Implement alert thresholds and grouping
- **Data quality:** Validate scraped data, log anomalies
- **Model drift:** Periodic retraining, monitoring
- **Scalability:** Horizontal scaling with Redis/Celery

## Next Steps

1. **Review and Approve:** Stakeholder review of Phase 2 plan
2. **Environment Setup:** Install dependencies, configure services
3. **Iterative Development:** Start with Phase 2.1, deliver incrementally
4. **Testing:** Unit tests, integration tests, stress tests
5. **Deployment:** Staging → Production with monitoring

---

**Status:** Ready to begin implementation  
**Estimated Timeline:** 6 weeks (can be accelerated with parallel development)  
**Priority Order:** 2.1 → 2.2 → 2.4 → 2.3 → 2.5
