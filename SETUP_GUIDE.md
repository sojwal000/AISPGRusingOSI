# AI System for Predicting Geopolitical Risk - Setup Guide

## Phase 1: Data Ingestion and Risk Scoring

This guide will help you set up and run the geopolitical risk analysis system.

---

## Prerequisites

### Required Software

1. **Python 3.9+**
2. **PostgreSQL 14+**
3. **MongoDB 6+**

### Installation Links

- Python: https://www.python.org/downloads/
- PostgreSQL: https://www.postgresql.org/download/
- MongoDB: https://www.mongodb.com/try/download/community

---

## Setup Instructions

### Step 1: Install Dependencies

```bash
cd c:\Users\Swastik\Desktop\ClientProjects\AISPGRusingOSI
pip install -r requirements.txt
```

### Step 2: Configure Environment

1. Copy the example environment file:

   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and configure:

   ```
   # Database credentials
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=geopolitical_risk
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_postgres_password

   MONGODB_HOST=localhost
   MONGODB_PORT=27017
   MONGODB_DB=geopolitical_risk

   # API Keys (optional for Phase 1 - will use sample data if not provided)
   ACLED_API_KEY=your_acled_key
   ACLED_EMAIL=your_email@example.com
   ```

### Step 3: Create Databases

#### PostgreSQL

```sql
-- Open PostgreSQL command line or pgAdmin
CREATE DATABASE geopolitical_risk;
```

#### MongoDB

```bash
# MongoDB database will be created automatically
```

### Step 4: Initialize Database Schema

```bash
python setup_db.py
```

This will:

- Create all PostgreSQL tables
- Create MongoDB collections with indexes
- Seed initial country data

---

## Running the System

### Option 1: Run Complete Pipeline (Recommended for First Time)

```bash
python run_pipeline.py
```

This will:

1. Ingest news data from RSS feeds (India-focused)
2. Fetch conflict events from ACLED
3. Get economic indicators from World Bank
4. Calculate risk score for India
5. Display comprehensive results in console

**Output includes:**

- Data ingestion summary
- Overall risk score (0-100)
- Risk level (minimal, low, medium, high, critical)
- Signal breakdown (news, conflict, economic, government)

### Option 2: Run for Different Country

```bash
python run_pipeline.py --country PAK
```

### Option 3: Get JSON Output

```bash
python run_pipeline.py --json > results.json
```

---

## Starting the API Server

After running the pipeline at least once:

```bash
python run_api.py
```

The API will be available at:

- **Base URL:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **API Spec:** http://localhost:8000/openapi.json

### Available Endpoints

```
GET /api/v1/countries
  - List all countries

GET /api/v1/risk-score/{country_code}
  - Get latest risk score for a country
  - Example: http://localhost:8000/api/v1/risk-score/IND

GET /api/v1/risk-score/{country_code}/history?days=30
  - Get risk score history

GET /api/v1/signals/{country_code}
  - Get detailed signal breakdown with calculation metadata

GET /api/v1/alerts?country_code=IND&days=30
  - Get recent alerts

GET /api/v1/conflict-events/{country_code}?days=30
  - Get conflict events

GET /api/v1/economic-indicators/{country_code}
  - Get economic indicators
```

---

## Testing the API

### Using Browser

Visit: http://localhost:8000/docs

### Using curl

```bash
# Get risk score for India
curl http://localhost:8000/api/v1/risk-score/IND

# Get signal breakdown
curl http://localhost:8000/api/v1/signals/IND

# Get recent alerts
curl http://localhost:8000/api/v1/alerts?country_code=IND

# Get all countries
curl http://localhost:8000/api/v1/countries
```

### Using PowerShell

```powershell
# Get risk score
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/risk-score/IND" | ConvertTo-Json

# Get signals
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/signals/IND" | ConvertTo-Json
```

---

## Understanding the Risk Score

### Overall Score (0-100)

- **0-20:** Minimal risk
- **20-40:** Low risk
- **40-60:** Medium risk
- **60-75:** High risk
- **75-100:** Critical risk

### Signal Components

1. **News Signal (20% weight)**

   - Based on article frequency and negative keywords
   - Detects emerging tensions through news coverage

2. **Conflict Signal (40% weight)**

   - Based on ACLED conflict events
   - Considers event frequency, type severity, and fatalities

3. **Economic Signal (30% weight)**

   - Based on World Bank indicators
   - Analyzes GDP growth, inflation, unemployment

4. **Government Signal (10% weight)**
   - Placeholder for Phase 1
   - Will analyze official reports in Phase 2

### Explainability

- Each signal score includes detailed metadata
- Calculation logic is deterministic and reproducible
- All source data is traceable

---

## Troubleshooting

### Database Connection Issues

**PostgreSQL:**

```bash
# Test connection
psql -U postgres -d geopolitical_risk -c "SELECT 1"
```

**MongoDB:**

```bash
# Test connection
mongosh --eval "db.adminCommand('ping')"
```

### Missing API Keys

The system will work with sample data if API keys are not provided:

- ACLED: Generates sample conflict events
- World Bank: Uses fallback data generation

To get real data:

- **ACLED:** Register at https://developer.acleddata.com/
- **World Bank:** No registration needed (public API)

### Import Errors

If you see import errors:

```bash
# Make sure you're in the project directory
cd c:\Users\Swastik\Desktop\ClientProjects\AISPGRusingOSI

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

---

## Data Sources (Phase 1)

### News RSS Feeds

- The Hindu - National
- Times of India - India
- Indian Express - India
- NDTV India
- BBC India

### Conflict Data

- ACLED (Armed Conflict Location & Event Data Project)
- Sample data generated if API key not available

### Economic Indicators

- World Bank API (no key required)
- Indicators: GDP Growth, Inflation, Unemployment, Foreign Reserves, Government Debt

---

## Next Steps

Once Phase 1 is working:

1. **Schedule automatic ingestion** using Windows Task Scheduler or cron
2. **Monitor risk scores** regularly via API
3. **Export data** for further analysis
4. **Prepare for Phase 2**: Frontend dashboard development

---

## Support

For issues or questions:

1. Check logs in console output
2. Verify database connectivity
3. Ensure all dependencies are installed
4. Check `.env` configuration

---

## Project Structure

```
AISPGRusingOSI/
├── backend/
│   ├── app/
│   │   ├── core/          # Configuration, database
│   │   ├── models/        # Database models
│   │   ├── ingestion/     # Data ingestion modules
│   │   ├── scoring/       # Risk scoring engine
│   │   └── api/           # FastAPI routes
│   └── scripts/           # Utility scripts
├── run_pipeline.py        # Main pipeline runner
├── run_api.py            # API server runner
├── setup_db.py           # Database initialization
├── requirements.txt       # Python dependencies
└── .env                  # Configuration (create from .env.example)
```
