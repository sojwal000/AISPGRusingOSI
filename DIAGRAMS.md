# System Diagrams for Geopolitical Risk Assessment System

This document contains all technical diagrams required for the research paper. All diagrams are provided in Mermaid syntax for easy rendering and can be exported as images for paper inclusion.

---

## 1. System Architecture Diagram (MANDATORY)

This diagram illustrates the complete system architecture including data sources, processing layers, storage, and presentation components.

```mermaid
graph TB
    subgraph "External Data Sources"
        A1[News RSS Feeds<br/>19 International Sources]
        A2[GDELT API<br/>Conflict Events]
        A3[World Bank API<br/>Economic Indicators]
        A4[Government Portals<br/>Official Communications]
    end

    subgraph "Data Ingestion Layer"
        B1[RSS Feed Parser<br/>feedparser]
        B2[GDELT Query Module]
        B3[World Bank Client]
        B4[Web Scraper<br/>BeautifulSoup]
    end

    subgraph "Processing Layer"
        C1[Country Tagging<br/>Keyword Matching]
        C2[Sentiment Analysis<br/>DistilBERT Model]
        C3[Data Validation<br/>Quality Checks]
        C4[Text Preprocessing<br/>NLP Pipeline]
    end

    subgraph "Storage Layer"
        D1[(PostgreSQL<br/>Structured Data)]
        D2[(MongoDB<br/>Document Store)]
    end

    subgraph "Analytics Layer"
        E1[Risk Scoring Engine<br/>Weighted Aggregation]
        E2[Signal Processors<br/>News/Conflict/Economic/Gov]
        E3[Trend Analysis<br/>Temporal Scoring]
    end

    subgraph "Presentation Layer"
        F1[FastAPI REST API<br/>8 Endpoints]
        F2[Streamlit Dashboard<br/>Visualization]
    end

    subgraph "Users"
        G1[Researchers]
        G2[Policy Analysts]
        G3[API Consumers]
    end

    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B4

    B1 --> C1
    B1 --> C4
    B2 --> C3
    B3 --> C3
    B4 --> C3

    C1 --> C2
    C4 --> C2
    C2 --> D2
    C3 --> D1
    C3 --> D2

    D1 --> E2
    D2 --> E2
    E2 --> E1
    E1 --> E3
    E3 --> D1

    D1 --> F1
    D2 --> F1
    D1 --> F2
    D2 --> F2

    F1 --> G3
    F2 --> G1
    F2 --> G2

    style E1 fill:#ff9999
    style C2 fill:#99ccff
    style D1 fill:#99ff99
    style D2 fill:#99ff99
```

**Component Description:**
- **Data Ingestion Layer:** Collects OSINT data from multiple heterogeneous sources
- **Processing Layer:** Applies NLP and validation to raw data
- **Storage Layer:** Hybrid database design (PostgreSQL + MongoDB)
- **Analytics Layer:** Implements weighted risk scoring algorithm
- **Presentation Layer:** Provides API and web interface for data access

---

## 2. Use Case Diagram (MANDATORY)

This diagram defines system functionality and actor interactions.

```mermaid
graph LR
    subgraph "Actors"
        A1([Researcher])
        A2([Policy Analyst])
        A3([System Administrator])
        A4([API Consumer])
    end

    subgraph "Geopolitical Risk Assessment System"
        U1[View Risk Scores]
        U2[Query Signal Breakdown]
        U3[Filter by Country]
        U4[View Historical Trends]
        U5[Export Data via API]
        U6[Monitor News Articles]
        U7[Analyze Conflict Events]
        U8[Review Economic Indicators]
        U9[Run Data Pipeline]
        U10[Configure Data Sources]
        U11[Manage Database]
        U12[View System Logs]
        U13[Generate Risk Reports]
    end

    A1 --> U1
    A1 --> U2
    A1 --> U3
    A1 --> U4
    A1 --> U6
    A1 --> U13

    A2 --> U1
    A2 --> U2
    A2 --> U3
    A2 --> U4
    A2 --> U7
    A2 --> U8
    A2 --> U13

    A3 --> U9
    A3 --> U10
    A3 --> U11
    A3 --> U12

    A4 --> U5
    A4 --> U1
    A4 --> U2

    style A1 fill:#e1f5ff
    style A2 fill:#e1f5ff
    style A3 fill:#ffe1e1
    style A4 fill:#e1ffe1
```

**Actor Responsibilities:**
- **Researcher:** Academic analysis of risk scores and trends
- **Policy Analyst:** Real-world decision support using risk assessments
- **System Administrator:** Pipeline execution and system maintenance
- **API Consumer:** Programmatic access to risk data

---

## 3. Data Flow Diagram - Level 1 (MANDATORY)

This DFD shows how data flows through the system from external sources to final risk scores.

```mermaid
graph TB
    subgraph "External Entities"
        E1[News Sources]
        E2[GDELT Database]
        E3[World Bank]
        E4[Government Websites]
        E5[End Users]
    end

    subgraph "Processes"
        P1[1.0<br/>Ingest News Data]
        P2[2.0<br/>Ingest Conflict Data]
        P3[3.0<br/>Ingest Economic Data]
        P4[4.0<br/>Ingest Government Data]
        P5[5.0<br/>Process & Analyze Text]
        P6[6.0<br/>Calculate Risk Scores]
        P7[7.0<br/>Generate Reports]
    end

    subgraph "Data Stores"
        D1[(D1: News Articles<br/>MongoDB)]
        D2[(D2: Conflict Events<br/>PostgreSQL)]
        D3[(D3: Economic Indicators<br/>PostgreSQL)]
        D4[(D4: Government Reports<br/>MongoDB)]
        D5[(D5: Risk Scores<br/>PostgreSQL)]
    end

    E1 -->|RSS Feeds| P1
    E2 -->|API Response| P2
    E3 -->|API Response| P3
    E4 -->|HTML Pages| P4

    P1 -->|Raw Articles| D1
    P2 -->|Event Records| D2
    P3 -->|Indicator Values| D3
    P4 -->|Report Documents| D4

    D1 -->|Article Text| P5
    D4 -->|Report Text| P5
    P5 -->|Sentiment Scores| D1
    P5 -->|Sentiment Scores| D4

    D1 -->|News Signal Data| P6
    D2 -->|Conflict Signal Data| P6
    D3 -->|Economic Signal Data| P6
    D4 -->|Gov Signal Data| P6

    P6 -->|Risk Scores| D5
    D5 -->|Score Data| P7
    P7 -->|Risk Reports| E5

    style P5 fill:#ffcccc
    style P6 fill:#ff9999
    style D1 fill:#ccffcc
    style D5 fill:#ccffcc
```

**Process Description:**
- **P1-P4:** Data ingestion processes for each source type
- **P5:** NLP processing including sentiment analysis
- **P6:** Core risk scoring engine with weighted aggregation
- **P7:** Report generation and data presentation

---

## 4. Sequence Diagram - Risk Score Calculation (HIGHLY RECOMMENDED)

This diagram shows the complete execution sequence when calculating risk scores for a country.

```mermaid
sequenceDiagram
    actor User
    participant CLI as Command Line Interface
    participant Pipeline as Pipeline Orchestrator
    participant NewsIngestion as News Ingestion Module
    participant GDELT as GDELT Module
    participant WorldBank as World Bank Module
    participant NLP as Sentiment Analyzer
    participant DB as Database Layer
    participant RiskEngine as Risk Scoring Engine
    participant API as FastAPI Server

    User->>CLI: python run_pipeline.py --country RUS
    CLI->>Pipeline: execute_pipeline(country_code="RUS")
    
    activate Pipeline
    Pipeline->>NewsIngestion: fetch_news_articles("RUS")
    activate NewsIngestion
    NewsIngestion->>NewsIngestion: parse_rss_feeds()
    NewsIngestion->>NewsIngestion: tag_country_keywords()
    NewsIngestion->>NLP: analyze_sentiment(articles)
    activate NLP
    NLP->>NLP: preprocess_text()
    NLP->>NLP: distilbert_inference()
    NLP-->>NewsIngestion: sentiment_scores
    deactivate NLP
    NewsIngestion->>DB: store_articles(with_sentiment)
    deactivate NewsIngestion

    Pipeline->>GDELT: fetch_conflict_events("RUS", time_window=60h)
    activate GDELT
    GDELT->>GDELT: query_api()
    GDELT->>DB: store_events()
    deactivate GDELT

    Pipeline->>WorldBank: fetch_economic_indicators("RUS")
    activate WorldBank
    WorldBank->>WorldBank: query_api(GDP, inflation, unemployment)
    WorldBank->>DB: store_indicators()
    deactivate WorldBank

    Pipeline->>RiskEngine: calculate_risk_score("RUS")
    activate RiskEngine
    RiskEngine->>DB: query_news_sentiment()
    DB-->>RiskEngine: news_signal_data
    RiskEngine->>DB: query_conflict_events()
    DB-->>RiskEngine: conflict_signal_data
    RiskEngine->>DB: query_economic_indicators()
    DB-->>RiskEngine: economic_signal_data
    RiskEngine->>DB: query_government_reports()
    DB-->>RiskEngine: government_signal_data

    RiskEngine->>RiskEngine: calculate_news_signal()
    RiskEngine->>RiskEngine: calculate_conflict_signal()
    RiskEngine->>RiskEngine: calculate_economic_signal()
    RiskEngine->>RiskEngine: calculate_government_signal()
    RiskEngine->>RiskEngine: weighted_aggregation()
    RiskEngine->>DB: store_risk_score()
    RiskEngine-->>Pipeline: risk_score_result
    deactivate RiskEngine

    Pipeline-->>CLI: execution_summary
    deactivate Pipeline
    CLI-->>User: Display results

    User->>API: GET /api/v1/risk-score/RUS
    activate API
    API->>DB: query_latest_score("RUS")
    DB-->>API: risk_score_object
    API-->>User: JSON response
    deactivate API
```

**Key Interactions:**
1. User initiates pipeline through CLI
2. Parallel data ingestion from multiple sources
3. Sentiment analysis applied to textual content
4. Risk engine aggregates signals with weights
5. Results stored and accessible via API

---

## 5. Entity Relationship Diagram (HIGHLY RECOMMENDED)

This ER diagram shows the PostgreSQL database schema design.

```mermaid
erDiagram
    Country ||--o{ RiskScore : has
    Country ||--o{ ConflictEvent : records
    Country ||--o{ EconomicIndicator : has
    Country ||--o{ Alert : generates
    RiskScore ||--|| SignalBreakdown : contains

    Country {
        string country_code PK
        string name
        string region
        string iso3_code
        datetime created_at
        datetime updated_at
    }

    RiskScore {
        int id PK
        string country_code FK
        float overall_score
        string risk_level
        string trend
        datetime calculated_at
        jsonb metadata
    }

    SignalBreakdown {
        int risk_score_id PK_FK
        float news_signal_score
        int news_articles_count
        float news_mean_sentiment
        float conflict_signal_score
        int conflict_events_count
        int total_fatalities
        float economic_signal_score
        float gdp_score
        float inflation_score
        float unemployment_score
        float government_signal_score
        string government_data_status
    }

    ConflictEvent {
        int id PK
        string country_code FK
        datetime event_date
        string event_type
        string location
        int fatalities
        float goldstein_scale
        string source_url
        datetime ingested_at
    }

    EconomicIndicator {
        int id PK
        string country_code FK
        string indicator_name
        float value
        int year
        string source
        datetime retrieved_at
    }

    Alert {
        int id PK
        string country_code FK
        string alert_type
        string severity
        string message
        datetime created_at
        boolean is_resolved
    }

    User {
        int id PK
        string username
        string email
        string hashed_password
        string role
        datetime created_at
        datetime last_login
    }
```

**Schema Highlights:**
- **Country:** Central entity for all geopolitical data
- **RiskScore:** Stores calculated risk assessments with timestamps
- **SignalBreakdown:** Detailed breakdown of individual signal contributions
- **ConflictEvent, EconomicIndicator:** Source-specific structured data
- **Alert:** System-generated notifications for significant changes

**MongoDB Collections (Not shown in ER):**
- `news_articles`: {title, content, source, published_date, countries[], sentiment_score}
- `government_reports`: {title, content, source, published_date, country_code}

---

## 6. Activity Diagram - Data Pipeline Execution (OPTIONAL BUT USEFUL)

This diagram shows the step-by-step workflow of the automated data pipeline.

```mermaid
graph TD
    Start([Pipeline Start]) --> Init[Initialize Pipeline<br/>Load Configuration]
    Init --> ValidateCountry{Valid Country<br/>Code?}
    
    ValidateCountry -->|No| Error1[Log Error:<br/>Invalid Country]
    Error1 --> End1([End])
    
    ValidateCountry -->|Yes| FetchNews[Fetch News Articles<br/>from RSS Feeds]
    FetchNews --> ParseNews[Parse RSS XML<br/>Extract Article Data]
    ParseNews --> TagCountry[Apply Country Tagging<br/>Keyword Matching]
    TagCountry --> CheckArticles{Articles<br/>Found?}
    
    CheckArticles -->|No| LogWarning1[Log Warning:<br/>No Articles]
    CheckArticles -->|Yes| ProcessText[Preprocess Text<br/>Tokenization]
    
    ProcessText --> SentimentAnalysis[Sentiment Analysis<br/>DistilBERT Model]
    SentimentAnalysis --> StoreArticles[Store Articles<br/>in MongoDB]
    
    StoreArticles --> FetchConflict[Fetch Conflict Events<br/>from GDELT API]
    LogWarning1 --> FetchConflict
    
    FetchConflict --> ValidateConflict[Validate Event Data<br/>Check Completeness]
    ValidateConflict --> StoreConflict[Store Events<br/>in PostgreSQL]
    
    StoreConflict --> FetchEconomic[Fetch Economic Indicators<br/>from World Bank API]
    FetchEconomic --> ValidateEconomic[Validate Economic Data<br/>Range Checks]
    ValidateEconomic --> StoreEconomic[Store Indicators<br/>in PostgreSQL]
    
    StoreEconomic --> FetchGov[Fetch Government Reports<br/>Web Scraping]
    FetchGov --> CheckGovAvailable{Government<br/>Sources Available?}
    
    CheckGovAvailable -->|No| SkipGov[Skip Government Signal]
    CheckGovAvailable -->|Yes| ParseGov[Parse HTML<br/>Extract Documents]
    ParseGov --> AnalyzeGov[Sentiment Analysis<br/>Government Text]
    AnalyzeGov --> StoreGov[Store Reports<br/>in MongoDB]
    
    StoreGov --> CalculateSignals[Calculate Individual Signals]
    SkipGov --> CalculateSignals
    
    CalculateSignals --> NewsSignal[Calculate News Signal<br/>Mean Sentiment]
    NewsSignal --> ConflictSignal[Calculate Conflict Signal<br/>Event Count + Fatalities]
    ConflictSignal --> EconomicSignal[Calculate Economic Signal<br/>GDP + Inflation + Unemployment]
    EconomicSignal --> GovSignal[Calculate Government Signal<br/>Report Sentiment]
    
    GovSignal --> WeightedAgg[Weighted Aggregation<br/>40% Conflict + 30% Economic<br/>+ 20% News + 10% Gov]
    WeightedAgg --> DetermineLevel{Risk Level<br/>Classification}
    
    DetermineLevel -->|0-30| LowRisk[Assign: LOW Risk]
    DetermineLevel -->|30-60| ModerateRisk[Assign: MODERATE Risk]
    DetermineLevel -->|60-100| HighRisk[Assign: HIGH Risk]
    
    LowRisk --> StoreScore[Store Risk Score<br/>in PostgreSQL]
    ModerateRisk --> StoreScore
    HighRisk --> StoreScore
    
    StoreScore --> CheckThreshold{Score Change<br/>> Threshold?}
    CheckThreshold -->|Yes| GenerateAlert[Generate Alert<br/>Store in Database]
    CheckThreshold -->|No| LogComplete[Log Completion<br/>Pipeline Success]
    GenerateAlert --> LogComplete
    
    LogComplete --> DisplaySummary[Display Summary<br/>Console Output]
    DisplaySummary --> End2([End])

    style Start fill:#90EE90
    style End1 fill:#FFB6C6
    style End2 fill:#90EE90
    style SentimentAnalysis fill:#87CEEB
    style WeightedAgg fill:#FFD700
    style StoreScore fill:#98FB98
```

**Workflow Steps:**
1. **Initialization:** Validate country code and load configuration
2. **Data Collection:** Sequential ingestion from all sources
3. **Processing:** Text analysis and sentiment classification
4. **Storage:** Persist data in appropriate databases
5. **Scoring:** Calculate individual signals and aggregate
6. **Classification:** Assign risk level based on score
7. **Alerting:** Generate alerts for significant changes
8. **Reporting:** Output summary to console

---

## Diagram Usage Instructions

### For Research Paper Inclusion:

1. **Render to Images:**
   - Use Mermaid Live Editor: https://mermaid.live/
   - Copy each diagram code block
   - Export as PNG or SVG (300 DPI for print)

2. **Placement Recommendations:**
   - System Architecture: Section 5 (System Architecture)
   - Use Case Diagram: Section 5.1 (System Overview)
   - Data Flow Diagram: Section 6 (Methodology)
   - Sequence Diagram: Section 7 (Implementation Details)
   - ER Diagram: Section 7.2 (Database Schema)
   - Activity Diagram: Section 6.1 (Data Collection)

3. **Caption Format:**
   ```
   Figure X: [Diagram Type] showing [brief description]
   ```

### For Presentation:

- Use high-contrast color schemes
- Increase font sizes for readability
- Animate complex diagrams progressively
- Use separate slides for each diagram

### Technical Notes:

- All diagrams use Mermaid syntax (compatible with GitHub, GitLab, VSCode)
- Can be rendered in Markdown Preview Enhanced
- Exportable to PDF, PNG, SVG formats
- Version control friendly (text-based)

---

## Diagram Coverage Summary

| Diagram Type | Status | Section Placement | Priority |
|-------------|--------|------------------|----------|
| System Architecture | ✅ Included | Section 5 | MANDATORY |
| Use Case | ✅ Included | Section 5.1 | MANDATORY |
| Data Flow (Level 1) | ✅ Included | Section 6 | MANDATORY |
| Sequence | ✅ Included | Section 7 | HIGHLY RECOMMENDED |
| ER Diagram | ✅ Included | Section 7.2 | HIGHLY RECOMMENDED |
| Activity | ✅ Included | Section 6.1 | OPTIONAL |

**Total:** 6 diagrams covering all system aspects from architecture to execution flow.

---

**Document Information:**
- Project: AI System for Predicting Geopolitical Risk Using OSINT
- Diagram Set: Complete Technical Documentation
- Format: Mermaid Syntax (Markdown Compatible)
- Last Updated: January 2026
