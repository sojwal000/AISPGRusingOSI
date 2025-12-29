# AI System for Predicting Geopolitical Risk Using OSINT

## Phase 1: Data Ingestion and Risk Scoring Pipeline

### Current Features

- Real data ingestion from News RSS, ACLED, and World Bank
- PostgreSQL schema for structured data (risk scores, countries, alerts)
- MongoDB schema for unstructured data (news articles, reports)
- Deterministic risk scoring engine for India
- FastAPI backend with REST endpoints
- Console runner for testing

### Prerequisites

- Python 3.9+
- PostgreSQL 14+
- MongoDB 6+

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and configure:

- Database credentials
- API keys (ACLED, World Bank)

### Running the System

```bash
# Run data ingestion and scoring pipeline
python run_pipeline.py

# Start API server
python run_api.py
```

### Project Structure

```
backend/
├── app/
│   ├── core/           # Configuration, database connections
│   ├── models/         # Database models
│   ├── ingestion/      # Data ingestion modules
│   ├── scoring/        # Risk scoring logic
│   └── api/            # FastAPI routes
├── tests/
└── scripts/
```

### API Endpoints

- `GET /api/v1/countries` - List all countries
- `GET /api/v1/risk-score/{country_code}` - Get risk score for country
- `GET /api/v1/signals/{country_code}` - Get signal breakdown
- `GET /api/v1/alerts` - Get recent alerts

## Roadmap

- [ ] Phase 1: Data ingestion and scoring (Current)
- [ ] Phase 2: Frontend dashboard with React
- [ ] Phase 3: AI assistant with Gemini + LangChain
- [ ] Phase 4: Authentication and multi-user support
