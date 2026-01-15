from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.sql_models import Country, RiskScore, Alert, ConflictEvent, EconomicIndicator
from app.api import schemas
from app.ingestion.government_data import GovernmentDataIngestion
from app.ingestion.gdelt import GDELTIngestion

app = FastAPI(
    title="Geopolitical Risk Analysis API",
    description="API for India-focused geopolitical risk assessment using OSINT",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """API root endpoint"""
    return {
        "name": "Geopolitical Risk Analysis API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "countries": "/api/v1/countries",
            "risk_score": "/api/v1/risk-score/{country_code}",
            "signals": "/api/v1/signals/{country_code}",
            "alerts": "/api/v1/alerts",
            "health": "/health"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/v1/ingest/government")
def trigger_government_ingestion(days_back: int = 7):
    """
    Trigger government data ingestion (PIB)
    
    Args:
        days_back: Number of days to scrape (default 7)
    
    Returns:
        Ingestion summary with document counts
    """
    try:
        ingestion = GovernmentDataIngestion()
        result = ingestion.ingest_all_sources(days_back=days_back)
        
        return {
            "status": "success",
            "message": f"Government data ingestion completed",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@app.post("/api/v1/ingest/gdelt")
def trigger_gdelt_ingestion(hours_back: int = 24, country_code: str = "IND"):
    """
    Trigger GDELT conflict event ingestion
    
    Args:
        hours_back: Number of hours to fetch (default 24)
        country_code: Country to focus on (default IND)
    
    Returns:
        Ingestion summary with event counts
    """
    try:
        ingestion = GDELTIngestion()
        result = ingestion.ingest(hours_back=hours_back, country_code=country_code)
        
        return {
            "status": result["status"],
            "message": f"GDELT ingestion completed for {country_code}",
            "events_fetched": result.get("events_fetched", 0),
            "events_stored": result.get("events_stored", 0),
            "hours_back": hours_back,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@app.get("/api/v1/countries", response_model=List[schemas.CountryResponse])
def get_countries(db: Session = Depends(get_db)):
    """Get list of all countries"""
    countries = db.query(Country).all()
    return countries


@app.get("/api/v1/countries/{country_code}", response_model=schemas.CountryResponse)
def get_country(country_code: str, db: Session = Depends(get_db)):
    """Get details of a specific country"""
    country = db.query(Country).filter(Country.code == country_code).first()
    
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    
    return country


@app.get("/api/v1/risk-score/{country_code}", response_model=schemas.RiskScoreResponse)
def get_risk_score(country_code: str, db: Session = Depends(get_db)):
    """Get latest risk score for a country"""
    
    # Get latest risk score
    risk_score = db.query(RiskScore).filter(
        RiskScore.country_code == country_code
    ).order_by(RiskScore.date.desc()).first()
    
    if not risk_score:
        raise HTTPException(
            status_code=404,
            detail=f"No risk score found for country {country_code}"
        )
    
    return {
        "country_code": risk_score.country_code,
        "overall_score": risk_score.overall_score,
        "risk_level": _get_risk_level(risk_score.overall_score),
        "trend": risk_score.trend,
        "date": risk_score.date,
        "signals": {
            "news": risk_score.news_signal_score,
            "conflict": risk_score.conflict_signal_score,
            "economic": risk_score.economic_signal_score,
            "government": risk_score.government_signal_score
        }
    }


@app.get("/api/v1/risk-score/{country_code}/history")
def get_risk_score_history(
    country_code: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get risk score history for a country"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    scores = db.query(RiskScore).filter(
        RiskScore.country_code == country_code,
        RiskScore.date >= cutoff_date
    ).order_by(RiskScore.date.asc()).all()
    
    if not scores:
        raise HTTPException(
            status_code=404,
            detail=f"No risk score history found for {country_code}"
        )
    
    return {
        "country_code": country_code,
        "days": days,
        "count": len(scores),
        "scores": [
            {
                "date": score.date.isoformat(),
                "overall_score": score.overall_score,
                "trend": score.trend
            }
            for score in scores
        ]
    }


@app.get("/api/v1/signals/{country_code}")
def get_signals_breakdown(country_code: str, db: Session = Depends(get_db)):
    """Get detailed signal breakdown for a country"""
    
    # Get latest risk score
    risk_score = db.query(RiskScore).filter(
        RiskScore.country_code == country_code
    ).order_by(RiskScore.date.desc()).first()
    
    if not risk_score:
        raise HTTPException(
            status_code=404,
            detail=f"No signals found for country {country_code}"
        )
    
    # Parse metadata
    import json
    metadata = json.loads(risk_score.calculation_metadata) if risk_score.calculation_metadata else {}
    
    return {
        "country_code": country_code,
        "calculated_at": risk_score.date.isoformat(),
        "overall_score": risk_score.overall_score,
        "signals": {
            "news": {
                "score": risk_score.news_signal_score,
                "weight": 0.20,
                "details": metadata.get("news", {})
            },
            "conflict": {
                "score": risk_score.conflict_signal_score,
                "weight": 0.40,
                "details": metadata.get("conflict", {})
            },
            "economic": {
                "score": risk_score.economic_signal_score,
                "weight": 0.30,
                "details": metadata.get("economic", {})
            },
            "government": {
                "score": risk_score.government_signal_score,
                "weight": 0.10,
                "details": metadata.get("government", {})
            }
        }
    }


@app.get("/api/v1/alerts", response_model=List[schemas.AlertResponse])
def get_alerts(
    country_code: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get recent alerts"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Alert).filter(Alert.triggered_at >= cutoff_date)
    
    if country_code:
        query = query.filter(Alert.country_code == country_code)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    alerts = query.order_by(Alert.triggered_at.desc()).limit(100).all()
    
    return alerts


@app.get("/api/v1/conflict-events/{country_code}")
def get_conflict_events(
    country_code: str,
    days: int = 30,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get recent conflict events for a country"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    events = db.query(ConflictEvent).filter(
        ConflictEvent.country_code == country_code,
        ConflictEvent.event_date >= cutoff_date
    ).order_by(ConflictEvent.event_date.desc()).limit(limit).all()
    
    return {
        "country_code": country_code,
        "days": days,
        "count": len(events),
        "events": [
            {
                "date": event.event_date.isoformat(),
                "type": event.event_type,
                "sub_type": event.sub_event_type,
                "location": event.location,
                "fatalities": event.fatalities,
                "actors": [event.actor1, event.actor2]
            }
            for event in events
        ]
    }


@app.get("/api/v1/economic-indicators/{country_code}")
def get_economic_indicators(
    country_code: str,
    db: Session = Depends(get_db)
):
    """Get economic indicators for a country"""
    
    # Get indicators from last 5 years
    current_year = datetime.utcnow().year
    
    indicators_by_type = {}
    
    for indicator_code in ["GDP_GROWTH", "INFLATION", "UNEMPLOYMENT", "FOREIGN_RESERVES", "GOVT_DEBT"]:
        indicators = db.query(EconomicIndicator).filter(
            EconomicIndicator.country_code == country_code,
            EconomicIndicator.indicator_code == indicator_code
        ).order_by(EconomicIndicator.date.desc()).limit(5).all()
        
        if indicators:
            indicators_by_type[indicator_code] = [
                {
                    "year": ind.date.year,
                    "value": ind.value,
                    "name": ind.indicator_name
                }
                for ind in indicators
            ]
    
    return {
        "country_code": country_code,
        "indicators": indicators_by_type
    }


# ==============================================================================
# ML ENHANCED ENDPOINTS - Phase 3
# ==============================================================================

@app.get("/api/v1/ml/topics/{country_code}")
def get_topic_analysis(country_code: str, days: int = 14, db: Session = Depends(get_db)):
    """
    Get topic modeling analysis for news articles.
    Identifies emerging themes and trending topics.
    
    Args:
        country_code: Country to analyze
        days: Number of days to look back
    
    Returns:
        Topic analysis with trending topics and risk factors
    """
    try:
        from app.scoring.ml_integration import get_ml_enhancer
        from app.core.database import get_mongo_db
        
        enhancer = get_ml_enhancer(db, get_mongo_db())
        result = enhancer.analyze_news_topics(country_code, days)
        
        return {
            "status": "error" if "error" in result else "success",
            "country_code": country_code,
            "days_analyzed": days,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Topic analysis failed: {str(e)}")


@app.get("/api/v1/ml/forecast/{country_code}")
def get_risk_forecast(country_code: str, periods: int = 14, db: Session = Depends(get_db)):
    """
    Get risk score forecast for future periods.
    Uses Prophet or statistical methods to predict risk trends.
    
    Args:
        country_code: Country to forecast
        periods: Number of days to forecast
    
    Returns:
        Forecast with predictions and outlook
    """
    try:
        from app.scoring.ml_integration import get_ml_enhancer
        from app.core.database import get_mongo_db
        
        enhancer = get_ml_enhancer(db, get_mongo_db())
        result = enhancer.forecast_risk(country_code, periods)
        
        return {
            "status": "error" if "error" in result else "success",
            "country_code": country_code,
            "forecast_periods": periods,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(e)}")


@app.get("/api/v1/ml/anomalies/{country_code}")
def get_anomaly_detection(country_code: str, days: int = 30, db: Session = Depends(get_db)):
    """
    Detect anomalies in risk signals.
    Identifies unusual patterns, spikes, and outliers.
    
    Args:
        country_code: Country to analyze
        days: Number of days to analyze
    
    Returns:
        Anomaly detection results with alerts
    """
    try:
        from app.scoring.ml_integration import get_ml_enhancer
        from app.core.database import get_mongo_db
        
        enhancer = get_ml_enhancer(db, get_mongo_db())
        result = enhancer.detect_anomalies(country_code, days)
        
        return {
            "status": "error" if "error" in result else "success",
            "country_code": country_code,
            "days_analyzed": days,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")


@app.get("/api/v1/ml/clusters/{country_code}")
def get_event_clusters(country_code: str, days: int = 30, db: Session = Depends(get_db)):
    """
    Cluster related conflict events.
    Groups similar events to identify patterns and chains.
    
    Args:
        country_code: Country to analyze
        days: Number of days to look back
    
    Returns:
        Event clustering with chains and patterns
    """
    try:
        from app.scoring.ml_integration import get_ml_enhancer
        from app.core.database import get_mongo_db
        
        enhancer = get_ml_enhancer(db, get_mongo_db())
        result = enhancer.cluster_conflict_events(country_code, days)
        
        return {
            "status": "error" if "error" in result else "success",
            "country_code": country_code,
            "days_analyzed": days,
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event clustering failed: {str(e)}")


@app.get("/api/v1/ml/analysis/{country_code}")
def get_comprehensive_ml_analysis(country_code: str, db: Session = Depends(get_db)):
    """
    Get comprehensive ML-enhanced analysis for a country.
    Combines topic modeling, forecasting, anomaly detection, and clustering.
    
    Args:
        country_code: Country to analyze
    
    Returns:
        Complete ML analysis with all components
    """
    try:
        from app.scoring.ml_integration import get_ml_enhancer
        from app.core.database import get_mongo_db
        
        enhancer = get_ml_enhancer(db, get_mongo_db())
        result = enhancer.get_comprehensive_ml_analysis(country_code)
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML analysis failed: {str(e)}")


@app.post("/api/v1/ml/sentiment/analyze")
def analyze_geopolitical_sentiment(texts: List[str]):
    """
    Analyze texts using geopolitical-aware sentiment.
    Uses domain-specific lexicon combined with transformer models.
    
    Args:
        texts: List of texts to analyze
    
    Returns:
        Geopolitical sentiment analysis with risk indicators
    """
    try:
        from app.ml.geopolitical_sentiment import get_geopolitical_analyzer
        
        analyzer = get_geopolitical_analyzer()
        
        results = []
        for text in texts[:50]:  # Limit to 50 texts
            result = analyzer.analyze(text)
            risk_score = analyzer.calculate_document_risk(result)
            results.append({
                "text": text[:100] + "..." if len(text) > 100 else text,
                "risk_level": result["risk_level"],
                "combined_score": result["combined_score"],
                "risk_score": risk_score,
                "top_indicators": result.get("top_risk_indicators", [])[:3]
            })
        
        return {
            "status": "success",
            "analyzed_count": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


def _get_risk_level(score: float) -> str:
    """Convert numeric score to risk level"""
    if score >= 75:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "medium"
    elif score >= 20:
        return "low"
    else:
        return "minimal"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
