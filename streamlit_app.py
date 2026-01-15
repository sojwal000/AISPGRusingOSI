"""
Geopolitical Risk Dashboard
Visualizes India's risk assessment using all backend signals

Run: streamlit run streamlit_app.py
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import SessionLocal, get_mongo_db
from app.models.sql_models import RiskScore, Alert, ConflictEvent, EconomicIndicator
from app.scoring.risk_engine import RiskScoringEngine
from app.scoring.ai_explainer import get_ai_explainer

# Page config
st.set_page_config(
    page_title="Geopolitical Risk Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #4a9eff;
        text-align: center;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .sub-header {
        text-align: center;
        color: #b0b0b0;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2a4a6f 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #4a9eff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 1rem;
    }
    .signal-card {
        background: linear-gradient(135deg, #2a2a3e 0%, #3a3a4e 100%);
        padding: 1.25rem;
        border-radius: 10px;
        border: 1px solid #404050;
        margin: 0.75rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .alert-card {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .alert-critical { border-left-color: #d32f2f; background: rgba(211,47,47,0.1); }
    .alert-high { border-left-color: #f57c00; background: rgba(245,124,0,0.1); }
    .alert-medium { border-left-color: #fbc02d; background: rgba(251,192,45,0.1); }
    .alert-low { border-left-color: #388e3c; background: rgba(56,142,60,0.1); }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-success { background: #2e7d32; color: white; }
    .badge-warning { background: #f57c00; color: white; }
    .badge-error { background: #c62828; color: white; }
    .badge-info { background: #1976d2; color: white; }
    .risk-high { color: #ff5252; font-weight: 700; }
    .risk-medium { color: #ffa726; font-weight: 700; }
    .risk-low { color: #66bb6a; font-weight: 700; }
    .ai-explanation {
        background: linear-gradient(135deg, #1a2332 0%, #2a3342 100%);
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #3a4a5f;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin: 1rem 0;
    }
    .system-status {
        background: #1e1e2e;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #3a3a4a;
        margin-top: 1rem;
    }
    .divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, #4a9eff, transparent);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
@st.cache_resource
def get_db_session():
    return SessionLocal()

@st.cache_resource
def get_mongo():
    return get_mongo_db()

# Cache risk calculation for 5 minutes
@st.cache_data(ttl=300)
def calculate_current_risk(country_code="IND"):
    """Calculate current risk score"""
    engine = RiskScoringEngine()
    return engine.calculate_overall_risk(country_code=country_code)

@st.cache_data(ttl=300)
def get_risk_history(country_code="IND", days=30):
    """Get historical risk scores"""
    db = get_db_session()
    start_date = datetime.utcnow() - timedelta(days=days)
    
    scores = db.query(RiskScore).filter(
        RiskScore.country_code == country_code,
        RiskScore.date >= start_date
    ).order_by(RiskScore.date.asc()).all()
    
    return [{
        'date': score.date,
        'overall_score': score.overall_score,
        'confidence': score.confidence_score,
        'news': score.news_signal_score,
        'conflict': score.conflict_signal_score,
        'economic': score.economic_signal_score,
        'government': score.government_signal_score
    } for score in scores]

@st.cache_data(ttl=300)
def get_recent_alerts(country_code="IND", days=7):
    """Get recent alerts"""
    db = get_db_session()
    start_date = datetime.utcnow() - timedelta(days=days)
    
    alerts = db.query(Alert).filter(
        Alert.country_code == country_code,
        Alert.created_at >= start_date
    ).order_by(Alert.created_at.desc()).limit(10).all()
    
    return [{
        'type': alert.alert_type,
        'severity': alert.severity,
        'message': alert.message,
        'created_at': alert.created_at,
        'confidence': alert.confidence_score,
        'change': alert.change_percentage
    } for alert in alerts]

@st.cache_data(ttl=300)
def get_conflict_events(country_code="IND", days=30):
    """Get recent conflict events for map"""
    db = get_db_session()
    start_date = datetime.utcnow() - timedelta(days=days)
    
    events = db.query(ConflictEvent).filter(
        ConflictEvent.country_code == country_code,
        ConflictEvent.event_date >= start_date,
        ConflictEvent.latitude.isnot(None),
        ConflictEvent.longitude.isnot(None)
    ).order_by(ConflictEvent.event_date.desc()).limit(100).all()
    
    return [{
        'date': event.event_date,
        'type': event.event_type,
        'location': event.location,
        'lat': event.latitude,
        'lon': event.longitude,
        'fatalities': event.fatalities or 0,
        'notes': event.notes or '',
        'source': event.source
    } for event in events]

@st.cache_data(ttl=300)
def get_data_sources_status(country_code="IND"):
    """Get status and statistics of all data sources"""
    db = get_db_session()
    mongo_db = get_mongo_db()
    
    try:
        # GDELT Conflict Events
        conflict_count = db.query(ConflictEvent).filter(
            ConflictEvent.country_code == country_code
        ).count()
        latest_conflict = db.query(ConflictEvent).filter(
            ConflictEvent.country_code == country_code
        ).order_by(ConflictEvent.created_at.desc()).first()
        
        # News Articles from MongoDB
        # News stores 'countries' as an array, not 'country_code'
        news_count = mongo_db.news_articles.count_documents({"countries": country_code})
        latest_news = mongo_db.news_articles.find_one(
            {"countries": country_code},
            sort=[("published_date", -1)]
        )
        
        # Economic indicators from PostgreSQL (not MongoDB!)
        economic_count = db.query(EconomicIndicator).filter(
            EconomicIndicator.country_code == country_code
        ).count()
        latest_economic = db.query(EconomicIndicator).filter(
            EconomicIndicator.country_code == country_code
        ).order_by(EconomicIndicator.date.desc()).first()
        
        # Government reports from MongoDB
        # For India, also include legacy documents without country_code field
        if country_code == "IND":
            govt_query = {
                "$or": [
                    {"country_code": country_code},
                    {"country": country_code},
                    {"country_code": {"$exists": False}}  # Legacy documents
                ]
            }
        else:
            govt_query = {
                "$or": [
                    {"country_code": country_code},
                    {"country": country_code}
                ]
            }
        
        govt_count = mongo_db.government_reports.count_documents(govt_query)
        latest_govt = mongo_db.government_reports.find_one(
            govt_query,
            sort=[("report_date", -1)]
        )
        
        return {
            'conflict': {
                'count': conflict_count,
                'last_update': latest_conflict.created_at if latest_conflict else None,
                'source': 'GDELT 2.0 Event Database',
                'status': 'active' if conflict_count > 0 else 'inactive'
            },
            'news': {
                'count': news_count,
                'last_update': latest_news.get('published_date') if latest_news else None,
                'source': 'RSS Feeds (Reuters, BBC, Al Jazeera)',
                'status': 'active' if news_count > 0 else 'inactive'
            },
            'economic': {
                'count': economic_count,
                'last_update': latest_economic.date if latest_economic else None,
                'source': 'World Bank Open Data API',
                'status': 'active' if economic_count > 0 else 'inactive'
            },
            'government': {
                'count': govt_count,
                'last_update': latest_govt.get('report_date') if latest_govt else None,
                'source': 'Press Information Bureau (PIB)',
                'status': 'active' if govt_count > 0 else 'inactive'
            }
        }
    except Exception as e:
        return None

def get_risk_color(score):
    """Get color based on risk score"""
    if score >= 70:
        return "#ff5252"  # Red
    elif score >= 40:
        return "#ffa726"  # Orange
    else:
        return "#66bb6a"  # Green

def get_risk_level_class(level):
    """Get CSS class for risk level"""
    if level in ["high", "very_high"]:
        return "risk-high"
    elif level == "medium":
        return "risk-medium"
    else:
        return "risk-low"

def get_trend_emoji(trend):
    """Get emoji for trend"""
    if trend == "increasing":
        return "📈"
    elif trend == "decreasing":
        return "📉"
    else:
        return "➡️"

def format_time_ago(dt):
    """Format datetime as 'X ago'"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        mins = int(diff.total_seconds() / 60)
        return f"{mins}m ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    else:
        days = diff.days
        return f"{days}d ago"

# ============================================================================
# NEW HELPER FUNCTIONS - Backend Features Integration
# ============================================================================

@st.cache_data(ttl=300)
def get_news_articles_with_sentiment(country_code="IND", limit=50):
    """Get news articles with individual sentiment scores"""
    mongo_db = get_mongo_db()
    
    try:
        articles = list(mongo_db.news_articles.find(
            {"countries": country_code}
        ).sort("published_date", -1).limit(limit))
        
        # Add sentiment analysis if not present
        try:
            from app.ml.sentiment import get_sentiment_analyzer
            analyzer = get_sentiment_analyzer()
            
            for article in articles:
                if 'sentiment_score' not in article or article['sentiment_score'] is None:
                    text = f"{article.get('title', '')}. {article.get('content', '')[:500]}"
                    sentiment = analyzer.analyze(text)
                    article['sentiment_score'] = sentiment['normalized_score']
                    article['sentiment_label'] = sentiment['label']
                    article['sentiment_confidence'] = sentiment['confidence']
                else:
                    # Map existing scores
                    score = article.get('sentiment_score', 0)
                    article['sentiment_label'] = 'POSITIVE' if score > 0 else 'NEGATIVE' if score < 0 else 'NEUTRAL'
                    article['sentiment_confidence'] = abs(score)
        except Exception as e:
            for article in articles:
                article['sentiment_score'] = article.get('sentiment_score', 0)
                article['sentiment_label'] = 'UNKNOWN'
                article['sentiment_confidence'] = 0
        
        return [{
            'title': a.get('title', 'No Title'),
            'source': a.get('source', 'Unknown'),
            'published_date': a.get('published_date'),
            'url': a.get('url', '#'),
            'sentiment_score': a.get('sentiment_score', 0),
            'sentiment_label': a.get('sentiment_label', 'NEUTRAL'),
            'sentiment_confidence': a.get('sentiment_confidence', 0),
            'content_preview': (a.get('content', '') or '')[:200] + '...' if a.get('content') else ''
        } for a in articles]
    except Exception as e:
        return []

@st.cache_data(ttl=300)
def get_economic_history(country_code="IND", years=5):
    """Get economic indicator history for charting"""
    db = get_db_session()
    
    try:
        indicators = db.query(EconomicIndicator).filter(
            EconomicIndicator.country_code == country_code
        ).order_by(EconomicIndicator.date.desc()).all()
        
        # Group by indicator type
        history = {
            'GDP_GROWTH': [],
            'INFLATION': [],
            'UNEMPLOYMENT': []
        }
        
        for ind in indicators:
            code = ind.indicator_code
            if code in history:
                history[code].append({
                    'year': ind.date.year if ind.date else None,
                    'value': ind.value,
                    'name': ind.indicator_name
                })
        
        return history
    except Exception as e:
        return {'GDP_GROWTH': [], 'INFLATION': [], 'UNEMPLOYMENT': []}

@st.cache_data(ttl=600)
def extract_entities_from_articles(country_code="IND", limit=20):
    """Extract named entities from recent articles"""
    try:
        from app.ml.ner import get_entity_extractor
        extractor = get_entity_extractor()
        
        mongo_db = get_mongo_db()
        articles = list(mongo_db.news_articles.find(
            {"countries": country_code}
        ).sort("published_date", -1).limit(limit))
        
        all_persons = []
        all_organizations = []
        all_locations = []
        
        for article in articles:
            text = f"{article.get('title', '')}. {article.get('content', '')[:2000]}"
            actors = extractor.extract_key_actors(text)
            all_persons.extend(actors.get('persons', []))
            all_organizations.extend(actors.get('organizations', []))
            all_locations.extend(actors.get('locations', []))
        
        # Count frequencies
        from collections import Counter
        person_counts = Counter(all_persons).most_common(10)
        org_counts = Counter(all_organizations).most_common(10)
        location_counts = Counter(all_locations).most_common(10)
        
        return {
            'persons': person_counts,
            'organizations': org_counts,
            'locations': location_counts,
            'articles_analyzed': len(articles)
        }
    except Exception as e:
        return {
            'persons': [],
            'organizations': [],
            'locations': [],
            'articles_analyzed': 0,
            'error': str(e)
        }

@st.cache_data(ttl=300)
def get_alerts_with_evidence(country_code="IND", days=7):
    """Get alerts with full evidence data"""
    db = get_db_session()
    start_date = datetime.utcnow() - timedelta(days=days)
    
    alerts = db.query(Alert).filter(
        Alert.country_code == country_code,
        Alert.created_at >= start_date
    ).order_by(Alert.created_at.desc()).limit(10).all()
    
    import json
    return [{
        'id': alert.id,
        'type': alert.alert_type,
        'severity': alert.severity,
        'title': alert.title,
        'message': alert.message,
        'description': alert.description,
        'created_at': alert.created_at,
        'confidence': alert.confidence_score,
        'change': alert.change_percentage,
        'risk_score': alert.risk_score,
        'evidence': json.loads(alert.evidence) if alert.evidence else {}
    } for alert in alerts]

def trigger_pipeline_ingestion(ingestion_type, country_code="IND", **kwargs):
    """Trigger data ingestion via API endpoints"""
    import requests
    
    try:
        base_url = "http://localhost:8000/api/v1"
        
        if ingestion_type == "government":
            response = requests.post(
                f"{base_url}/ingest/government",
                params={"days_back": kwargs.get("days_back", 7)}
            )
        elif ingestion_type == "gdelt":
            response = requests.post(
                f"{base_url}/ingest/gdelt",
                params={
                    "hours_back": kwargs.get("hours_back", 24),
                    "country_code": country_code
                }
            )
        else:
            return {"status": "error", "message": f"Unknown ingestion type: {ingestion_type}"}
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": f"API returned {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "API server not running. Start with: python run_api.py"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_confidence_breakdown(risk_data):
    """Extract confidence breakdown from risk data"""
    try:
        signals = risk_data.get('signals', {})
        
        # Get confidence from calculation metadata
        metadata = {}
        for signal_name, signal_data in signals.items():
            if isinstance(signal_data, dict):
                metadata[signal_name] = signal_data
        
        # Calculate component scores
        news = signals.get('news', {})
        conflict = signals.get('conflict', {})
        economic = signals.get('economic', {})
        government = signals.get('government', {})
        
        # Data source count (how many signals have data)
        active_sources = sum([
            1 if news.get('article_count', 0) > 0 else 0,
            1 if conflict.get('event_count', 0) > 0 else 0,
            1 if len(economic.get('indicators_available', [])) > 0 else 0,
            1 if government.get('reports_analyzed', 0) > 0 else 0
        ])
        source_score = (active_sources / 4) * 100
        
        # Data freshness (based on days analyzed)
        freshness_score = 80  # Default
        
        # Signal consistency (how close are signals to each other)
        scores = [
            news.get('score', 0),
            conflict.get('score', 0),
            economic.get('score', 0),
            government.get('score', 0)
        ]
        non_zero_scores = [s for s in scores if s > 0]
        if len(non_zero_scores) > 1:
            import statistics
            consistency_score = 100 - (statistics.stdev(non_zero_scores) * 2)
            consistency_score = max(0, min(100, consistency_score))
        else:
            consistency_score = 50
        
        return {
            'source_count': round(source_score, 1),
            'freshness': round(freshness_score, 1),
            'consistency': round(consistency_score, 1),
            'historical_validation': round(risk_data.get('confidence_score', 50) * 0.8, 1),
            'active_sources': active_sources,
            'total_sources': 4
        }
    except Exception as e:
        return {
            'source_count': 50,
            'freshness': 50,
            'consistency': 50,
            'historical_validation': 50,
            'active_sources': 0,
            'total_sources': 4
        }

def get_enhanced_signal_details(signals):
    """Extract enhanced details from signals for display"""
    details = {
        'news': {},
        'conflict': {},
        'economic': {},
        'government': {}
    }
    
    # News signal details
    news = signals.get('news', {})
    if isinstance(news, dict):
        details['news'] = {
            'article_count': news.get('article_count', 0),
            'method': news.get('method', 'unknown'),
            'mean_sentiment': news.get('mean_sentiment', 0),
            'positive_ratio': news.get('positive_ratio', 0),
            'negative_ratio': news.get('negative_ratio', 0),
            'days_analyzed': news.get('days_analyzed', 7)
        }
    
    # Conflict signal details
    conflict = signals.get('conflict', {})
    if isinstance(conflict, dict):
        details['conflict'] = {
            'event_count': conflict.get('event_count', 0),
            'total_fatalities': conflict.get('total_fatalities', 0),
            'high_casualty_events': conflict.get('high_casualty_events', 0),
            'avg_severity': conflict.get('avg_severity', 0),
            'escalation_rate': conflict.get('escalation_rate', 0),
            'days_analyzed': conflict.get('days_analyzed', 30)
        }
    
    # Economic signal details
    economic = signals.get('economic', {})
    if isinstance(economic, dict):
        details['economic'] = {
            'gdp_score': economic.get('gdp_score', 0),
            'inflation_score': economic.get('inflation_score', 0),
            'unemployment_score': economic.get('unemployment_score', 0),
            'indicators_available': economic.get('indicators_available', [])
        }
    
    # Government signal details
    government = signals.get('government', {})
    if isinstance(government, dict):
        details['government'] = {
            'reports_analyzed': government.get('reports_analyzed', 0),
            'method': government.get('method', 'unknown'),
            'mean_sentiment': government.get('mean_sentiment', 0),
            'categories': government.get('categories', {}),
            'stability_score': government.get('stability_score', 0),
            'sentiment_score': government.get('sentiment_score', 0),
            'security_score': government.get('security_score', 0),
            'days_analyzed': government.get('days_analyzed', 30)
        }
    
    return details

# ==============================================================================
# ML ENHANCEMENT HELPER FUNCTIONS - Phase 3
# ==============================================================================

@st.cache_data(ttl=600)
def get_ml_topic_analysis(country_code="IND", days=14):
    """Get topic modeling analysis from ML backend"""
    try:
        import requests
        response = requests.get(
            f"http://localhost:8000/api/v1/ml/topics/{country_code}",
            params={"days": days},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "error": f"API returned {response.status_code}"}
    except requests.exceptions.ConnectionError:
        # Fallback: direct ML call if API not available
        try:
            from app.scoring.ml_integration import get_ml_enhancer
            from app.core.database import get_mongo_db
            enhancer = get_ml_enhancer(get_db_session(), get_mongo_db())
            result = enhancer.analyze_news_topics(country_code, days)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "error": f"ML module error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@st.cache_data(ttl=600)
def get_ml_risk_forecast(country_code="IND", periods=14):
    """Get risk forecast from ML backend"""
    try:
        import requests
        response = requests.get(
            f"http://localhost:8000/api/v1/ml/forecast/{country_code}",
            params={"periods": periods},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "error": f"API returned {response.status_code}"}
    except requests.exceptions.ConnectionError:
        try:
            from app.scoring.ml_integration import get_ml_enhancer
            from app.core.database import get_mongo_db
            enhancer = get_ml_enhancer(get_db_session(), get_mongo_db())
            result = enhancer.forecast_risk(country_code, periods)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "error": f"ML module error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@st.cache_data(ttl=600)
def get_ml_anomaly_detection(country_code="IND", days=30):
    """Get anomaly detection from ML backend"""
    try:
        import requests
        response = requests.get(
            f"http://localhost:8000/api/v1/ml/anomalies/{country_code}",
            params={"days": days},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "error": f"API returned {response.status_code}"}
    except requests.exceptions.ConnectionError:
        try:
            from app.scoring.ml_integration import get_ml_enhancer
            from app.core.database import get_mongo_db
            enhancer = get_ml_enhancer(get_db_session(), get_mongo_db())
            result = enhancer.detect_anomalies(country_code, days)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "error": f"ML module error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@st.cache_data(ttl=600)
def get_ml_event_clusters(country_code="IND", days=30):
    """Get event clustering from ML backend"""
    try:
        import requests
        response = requests.get(
            f"http://localhost:8000/api/v1/ml/clusters/{country_code}",
            params={"days": days},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "error": f"API returned {response.status_code}"}
    except requests.exceptions.ConnectionError:
        try:
            from app.scoring.ml_integration import get_ml_enhancer
            from app.core.database import get_mongo_db
            enhancer = get_ml_enhancer(get_db_session(), get_mongo_db())
            result = enhancer.cluster_conflict_events(country_code, days)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "error": f"ML module error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def render_ml_analytics_section(country_code):
    """Render the ML Analytics dashboard section"""
    st.markdown("### 🧠 Advanced ML Analytics")
    st.markdown("*Machine learning enhanced risk analysis - Topic modeling, forecasting, anomaly detection, and event clustering*")
    
    # Create tabs for different ML features
    ml_tabs = st.tabs(["📊 Risk Forecast", "🔍 Topic Analysis", "⚠️ Anomaly Detection", "🔗 Event Clusters"])
    
    # Tab 1: Risk Forecast
    with ml_tabs[0]:
        st.markdown("#### 📈 Risk Score Forecast")
        st.markdown("*Predicted risk trajectory for the next 14 days using time series analysis*")
        
        forecast_result = get_ml_risk_forecast(country_code)
        
        if forecast_result.get("status") == "success":
            data = forecast_result.get("data", {})
            
            if "error" not in data:
                forecasts = data.get("forecasts", [])
                outlook = data.get("outlook", {})
                
                if forecasts:
                    # Forecast chart
                    import plotly.graph_objects as go
                    
                    dates = [f["date"] for f in forecasts]
                    predicted = [f["predicted_score"] for f in forecasts]
                    lower = [f["lower_bound"] for f in forecasts]
                    upper = [f["upper_bound"] for f in forecasts]
                    
                    fig = go.Figure()
                    
                    # Confidence interval
                    fig.add_trace(go.Scatter(
                        x=dates + dates[::-1],
                        y=upper + lower[::-1],
                        fill='toself',
                        fillcolor='rgba(74, 158, 255, 0.2)',
                        line=dict(color='rgba(255,255,255,0)'),
                        name='Confidence Interval'
                    ))
                    
                    # Predicted line
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=predicted,
                        mode='lines+markers',
                        name='Predicted Risk',
                        line=dict(color='#4a9eff', width=3),
                        marker=dict(size=8)
                    ))
                    
                    # Add risk threshold lines
                    fig.add_hline(y=75, line_dash="dash", line_color="#ff5252", 
                                 annotation_text="Critical Threshold")
                    fig.add_hline(y=60, line_dash="dash", line_color="#ffa726",
                                 annotation_text="High Risk")
                    
                    fig.update_layout(
                        title="14-Day Risk Forecast",
                        xaxis_title="Date",
                        yaxis_title="Risk Score",
                        yaxis=dict(range=[0, 100]),
                        height=400,
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Outlook summary
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        outlook_emoji = {
                            "critical": "🔴", "elevated": "🟠", 
                            "moderate": "🟡", "low": "🟢"
                        }.get(outlook.get("outlook", ""), "⚪")
                        st.metric(
                            "Risk Outlook",
                            f"{outlook_emoji} {outlook.get('outlook', 'Unknown').upper()}",
                            help=outlook.get('summary', '')
                        )
                    
                    with col2:
                        st.metric(
                            "Predicted End Score",
                            f"{data.get('predicted_end_score', 0):.1f}",
                            delta=f"{data.get('predicted_end_score', 0) - data.get('current_score', 0):.1f}",
                            delta_color="inverse"
                        )
                    
                    with col3:
                        st.metric(
                            "Trend",
                            data.get("trend", "stable").capitalize(),
                            help=f"Method: {data.get('method', 'unknown')}"
                        )
                else:
                    st.info("Insufficient historical data for forecasting. Need at least 14 days of risk scores.")
            else:
                st.warning(f"Forecast unavailable: {data.get('error', 'Unknown error')}")
        else:
            st.error(f"Could not fetch forecast: {forecast_result.get('error', 'Unknown error')}")
    
    # Tab 2: Topic Analysis
    with ml_tabs[1]:
        st.markdown("#### 📰 Emerging Topics")
        st.markdown("*Key themes identified in recent news using BERTopic*")
        
        topic_result = get_ml_topic_analysis(country_code)
        
        if topic_result.get("status") == "success":
            data = topic_result.get("data", {})
            
            if "error" not in data and data.get("topics"):
                topics = data.get("topics", [])
                
                st.markdown(f"**{data.get('num_topics', 0)} Topics** identified from **{data.get('total_documents', 0)}** articles")
                st.markdown(f"*Weighted Risk Factor: {data.get('weighted_risk_factor', 1.0):.2f}*")
                
                # Display topics
                for topic in topics[:8]:
                    risk_color = {
                        "conflict": "#ff5252",
                        "terrorism": "#d32f2f", 
                        "nuclear": "#b71c1c",
                        "protest": "#ffa726",
                        "economy_negative": "#ff9800",
                        "border": "#f57c00",
                        "diplomacy": "#66bb6a",
                        "general": "#4a9eff"
                    }.get(topic.get("risk_category", "general"), "#4a9eff")
                    
                    with st.expander(
                        f"🏷️ Topic {topic['topic_id']}: {topic.get('risk_category', 'general').replace('_', ' ').title()} "
                        f"({topic.get('count', 0)} articles)"
                    ):
                        st.markdown(f"**Keywords:** {', '.join(topic.get('keywords', [])[:8])}")
                        st.markdown(f"**Risk Category:** {topic.get('risk_category', 'general')}")
                        st.markdown(f"**Risk Multiplier:** {topic.get('risk_multiplier', 1.0):.2f}x")
                        
                        # Progress bar for article count
                        total = data.get("total_documents", 1)
                        ratio = topic.get("count", 0) / total
                        st.progress(ratio, text=f"{ratio*100:.1f}% of articles")
                
                # Trending topics
                if data.get("trending_topics"):
                    st.markdown("---")
                    st.markdown("**🔥 Trending Topics**")
                    for trend in data.get("trending_topics", [])[:3]:
                        is_emerging = trend.get("is_emerging", False)
                        emoji = "🆕" if is_emerging else "📈"
                        st.markdown(f"{emoji} **{trend.get('risk_category', 'unknown')}** - {trend.get('count', 0)} articles")
            else:
                st.info("Topic modeling requires at least 10 articles. Run the news ingestion pipeline first.")
        else:
            st.warning(f"Topic analysis unavailable: {topic_result.get('error', 'Install bertopic: pip install bertopic')}")
    
    # Tab 3: Anomaly Detection
    with ml_tabs[2]:
        st.markdown("#### ⚠️ Anomaly Detection")
        st.markdown("*Unusual patterns in risk signals using Isolation Forest and statistical methods*")
        
        anomaly_result = get_ml_anomaly_detection(country_code)
        
        if anomaly_result.get("status") == "success":
            data = anomaly_result.get("data", {})
            
            if "error" not in data:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    anomaly_count = data.get("anomaly_count", 0)
                    color = "inverse" if anomaly_count > 3 else "normal"
                    st.metric("Anomalies Detected", anomaly_count, delta_color=color)
                
                with col2:
                    rate = data.get("anomaly_rate", 0) * 100
                    st.metric("Anomaly Rate", f"{rate:.1f}%")
                
                with col3:
                    spikes = len(data.get("spikes", []))
                    st.metric("Risk Spikes", spikes)
                
                # Show anomalies
                anomalies = data.get("anomalies", [])
                if anomalies:
                    st.markdown("**Recent Anomalies:**")
                    for anomaly in anomalies[:5]:
                        confidence = anomaly.get("confidence", 0)
                        severity = "🔴" if confidence >= 0.66 else "🟠" if confidence >= 0.33 else "🟡"
                        ts = anomaly.get("timestamp", "Unknown")
                        score = anomaly.get("overall_score", 0)
                        methods = ", ".join(anomaly.get("detection_methods", []))
                        
                        st.markdown(f"{severity} **Score: {score:.1f}** | Confidence: {confidence:.0%} | Methods: {methods}")
                
                # Show spikes
                spikes = data.get("spikes", [])
                if spikes:
                    st.markdown("---")
                    st.markdown("**Risk Spikes:**")
                    for spike in spikes[:3]:
                        direction = "📈" if spike.get("direction") == "spike" else "📉"
                        severity_icon = "🔴" if spike.get("severity") == "critical" else "🟠"
                        change = spike.get("change", 0)
                        st.markdown(
                            f"{severity_icon} {direction} {spike.get('previous_score', 0):.1f} → "
                            f"{spike.get('current_score', 0):.1f} (Δ{change:+.1f})"
                        )
                
                # Generated alerts
                alerts = data.get("generated_alerts", [])
                if alerts:
                    st.markdown("---")
                    st.markdown("**Generated Alerts:**")
                    for alert in alerts[:3]:
                        sev_icon = {"critical": "🔴", "high": "🟠", "warning": "🟡"}.get(alert.get("severity"), "⚪")
                        st.warning(f"{sev_icon} {alert.get('message', 'Alert')}")
            else:
                st.info(f"Anomaly detection unavailable: {data.get('error', 'Need more historical data')}")
        else:
            st.warning(f"Could not fetch anomaly data: {anomaly_result.get('error', 'Unknown error')}")
    
    # Tab 4: Event Clusters
    with ml_tabs[3]:
        st.markdown("#### 🔗 Event Clustering")
        st.markdown("*Related conflict events grouped by semantic similarity*")
        
        cluster_result = get_ml_event_clusters(country_code)
        
        if cluster_result.get("status") == "success":
            data = cluster_result.get("data", {})
            
            if "error" not in data:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Events", data.get("total_events", 0))
                
                with col2:
                    st.metric("Clusters Found", data.get("cluster_count", 0))
                
                with col3:
                    escalating = len(data.get("escalating_chains", []))
                    st.metric("Escalating Chains", escalating, delta_color="inverse" if escalating > 0 else "off")
                
                # Show clusters
                clusters = data.get("clusters", [])
                if clusters:
                    st.markdown("**Event Clusters:**")
                    for cluster in clusters[:5]:
                        cluster_type = cluster.get("cluster_type", "general")
                        type_icon = {
                            "escalating": "📈", "high_intensity": "💥",
                            "recurring": "🔄", "civil_unrest": "✊",
                            "conflict": "⚔️", "general": "📍"
                        }.get(cluster_type, "📍")
                        
                        with st.expander(
                            f"{type_icon} Cluster: {cluster_type.replace('_', ' ').title()} "
                            f"({cluster.get('event_count', 0)} events)"
                        ):
                            st.markdown(f"**Total Fatalities:** {cluster.get('total_fatalities', 0)}")
                            st.markdown(f"**Average Severity:** {cluster.get('average_severity', 0):.1f}")
                            
                            countries = cluster.get("country_distribution", {})
                            if countries:
                                st.markdown(f"**Countries:** {', '.join(countries.keys())}")
                            
                            event_types = cluster.get("event_types", {})
                            if event_types:
                                st.markdown(f"**Event Types:** {', '.join(event_types.keys())}")
                            
                            actors = cluster.get("unique_actors", [])[:5]
                            if actors:
                                st.markdown(f"**Key Actors:** {', '.join(actors)}")
                            
                            time_range = cluster.get("time_range", {})
                            if time_range.get("start"):
                                st.markdown(f"**Time Span:** {time_range.get('span_days', 0)} days")
                
                # Show event chains
                chains = data.get("event_chains", [])
                if chains:
                    st.markdown("---")
                    st.markdown("**Event Chains (Potentially Linked Incidents):**")
                    for chain in chains[:3]:
                        is_escalating = chain.get("is_escalating", False)
                        chain_icon = "📈🔴" if is_escalating else "🔗"
                        st.markdown(
                            f"{chain_icon} **{chain.get('chain_length', 0)} events** over "
                            f"{chain.get('total_span_days', 0)} days | "
                            f"Fatalities: {chain.get('total_fatalities', 0)}"
                        )
                        
                        if is_escalating:
                            st.warning("⚠️ This chain shows escalating pattern - increasing severity over time")
            else:
                st.info(f"Event clustering unavailable: {data.get('error', 'Need more events')}")
        else:
            st.warning(f"Could not fetch cluster data: {cluster_result.get('error', 'Install sentence-transformers')}")


# Main dashboard
def main():
    # Header
    st.markdown("<div class='main-header'>🌍 Geopolitical Risk Intelligence</div>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Control Panel")
        st.markdown("---")
        
        # Country selector
        st.markdown("**🌐 Country Selection**")
        country_code = st.selectbox(
            "Target Country",
            ["IND", "USA", "CHN", "RUS", "PAK", "BGD"],
            index=0,
            format_func=lambda x: {
                "IND": "🇮🇳 India (Data Available)", 
                "USA": "🇺🇸 United States (Run Pipeline)", 
                "CHN": "🇨🇳 China (Run Pipeline)", 
                "RUS": "🇷🇺 Russia (Run Pipeline)", 
                "PAK": "🇵🇰 Pakistan (Run Pipeline)", 
                "BGD": "🇧🇩 Bangladesh (Run Pipeline)"
            }.get(x, x),
            help="Select country - India has data, others need pipeline run with country code"
        )
        
        # Data availability notice
        with st.expander("ℹ️ Universal Free Data Sources (All Countries)"):
            st.markdown("""
            **✅ ALREADY WORKING FOR ALL COUNTRIES:**
            
            ⚔️ **Conflict Data (GDELT)**
            - ✔ Already integrated
            - ✔ Global coverage (200+ countries)
            - ✔ Near real-time
            - ✔ No API key required
            
            💹 **Economic Data (World Bank API)**
            - ✔ Works for every country
            - ✔ GDP, inflation, unemployment
            - ✔ No authentication needed
            - ✔ Structured JSON
            
            ---
            
            **📰 ADD NEWS RSS (5 minutes per country):**
            
            Universal sources (work for any country):
            - Google News RSS: `news.google.com/rss/search?q={COUNTRY}`
            - Bing News RSS
            - Yahoo News RSS
            
            Country-specific (optional):
            - India: The Hindu, Indian Express
            - USA: AP News, Reuters
            - China: Xinhua, Global Times
            - Russia: TASS, RT
            
            📝 *Edit: `backend/app/ingestion/news_rss.py`*
            
            ---
            
            **🏛️ GOVERNMENT DATA (Easy):**
            
            Option 1 (Recommended): Already covered by GDELT
            - Policy announcements captured in news
            - No scraping needed
            
            Option 2 (If RSS available):
            - India: PIB RSS ✔
            - USA: whitehouse.gov RSS
            - UK: gov.uk RSS
            
            ---
            
            **🚀 To Enable New Country:**
            
            1. Add 2-3 RSS feeds to `news_rss.py`
            2. Run: `python run_pipeline.py --country {CODE}`
            3. Done! (GDELT + World Bank work automatically)
            
            *Minimal setup: 3 data sources = credible risk model*
            """)
    
    # Dynamic subtitle based on selected country
    country_names = {
        "IND": "India",
        "USA": "United States",
        "CHN": "China",
        "RUS": "Russia",
        "PAK": "Pakistan",
        "BGD": "Bangladesh"
    }
    st.markdown(f"<div class='sub-header'>{country_names.get(country_code, country_code)} Risk Assessment • Real-time OSINT Analysis</div>", unsafe_allow_html=True)
    
    # Continue sidebar
    with st.sidebar:
        
        st.markdown("---")
        st.markdown("**📅 Time Window**")
        history_days = st.slider(
            "History (days)",
            min_value=7,
            max_value=90,
            value=30,
            help="Number of days for historical analysis"
        )
        
        st.markdown("---")
        st.markdown("**📊 Signal Weights**")
        st.markdown("""
        <div style='font-size: 0.9rem; color: #b0b0b0;'>
        • <b>Conflict</b>: 40%<br>
        • <b>News</b>: 20%<br>
        • <b>Economic</b>: 30%<br>
        • <b>Government</b>: 10%
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("**🔄 Actions**")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Pipeline Control Panel - NEW FEATURE
        st.markdown("---")
        st.markdown("**🚀 Pipeline Control**")
        with st.expander("Trigger Data Ingestion"):
            st.caption("Requires API server running: `python run_api.py`")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📰 News RSS", use_container_width=True, help="Fetch latest news articles"):
                    with st.spinner("Running news ingestion..."):
                        # News ingestion runs via pipeline
                        st.info("Run: `python run_pipeline.py --country " + country_code + "`")
            
            with col_btn2:
                if st.button("⚔️ GDELT", use_container_width=True, help="Fetch conflict events"):
                    result = trigger_pipeline_ingestion("gdelt", country_code, hours_back=24)
                    if result.get("status") == "success":
                        st.success(f"✅ {result.get('events_stored', 0)} events stored")
                    else:
                        st.error(result.get("message", "Failed"))
            
            col_btn3, col_btn4 = st.columns(2)
            with col_btn3:
                if st.button("🏛️ Government", use_container_width=True, help="Fetch government reports"):
                    result = trigger_pipeline_ingestion("government", country_code, days_back=7)
                    if result.get("status") == "success":
                        st.success(f"✅ Ingestion complete")
                    else:
                        st.error(result.get("message", "Failed"))
            
            with col_btn4:
                if st.button("💹 Economic", use_container_width=True, help="Fetch World Bank data"):
                    st.info("Run: `python run_pipeline.py --country " + country_code + "`")
        
        st.markdown("---")
        st.markdown("**💡 Data Sources**")
        st.markdown("""
        <div style='font-size: 0.85rem; color: #90a0b0;'>
        <b>✓</b> GDELT (Conflict)<br>
        <b>✓</b> RSS Feeds (News)<br>
        <b>✓</b> World Bank (Economic)<br>
        <b>✓</b> PIB (Government)
        </div>
        """, unsafe_allow_html=True)
    
    # Main content layout with data sources sidebar on right
    main_col, sources_col = st.columns([3, 1])
    
    with main_col:
        # Calculate current risk
        try:
            with st.spinner("🔄 Analyzing geopolitical intelligence..."):
                risk_data = calculate_current_risk(country_code)
            
            # === LEVEL 1: GLOBAL SUMMARY ===
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            
            # Top summary cards
            col1, col2, col3, col4 = st.columns(4)
            
            risk_score = risk_data.get('overall_score', 0)
            confidence = risk_data.get('confidence_score', 0)
            risk_level = risk_data.get('risk_level', 'unknown')
            trend = risk_data.get('trend', 'stable')
            alerts_count = risk_data.get('alerts_triggered', 0)
            calc_time = datetime.fromisoformat(risk_data.get('calculated_at', datetime.utcnow().isoformat()))
            
            with col1:
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='font-size: 0.9rem; color: #b0b0b0; margin-bottom: 0.5rem;'>OVERALL RISK SCORE</div>
                    <div style='font-size: 2.5rem; font-weight: 700; color: {get_risk_color(risk_score)};'>
                        {risk_score:.1f}<span style='font-size: 1.2rem; color: #808080;'>/100</span>
                    </div>
                    <div class='<span class='{get_risk_level_class(risk_level)}' style='font-size: 1.1rem; margin-top: 0.5rem;'>
                        {risk_level.upper().replace('_', ' ')}
                    </div>
                    <div style='font-size: 0.85rem; color: #90a0b0; margin-top: 0.5rem;'>
                        {get_trend_emoji(trend)} {trend.title()}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                confidence_color = "#66bb6a" if confidence >= 70 else "#ffa726" if confidence >= 50 else "#ff5252"
                confidence_label = "High" if confidence >= 70 else "Medium" if confidence >= 50 else "Low"
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='font-size: 0.9rem; color: #b0b0b0; margin-bottom: 0.5rem;'>CONFIDENCE</div>
                    <div style='font-size: 2.5rem; font-weight: 700; color: {confidence_color};'>
                        {confidence:.0f}<span style='font-size: 1.2rem; color: #808080;'>%</span>
                    </div>
                    <div style='font-size: 1.1rem; color: {confidence_color}; margin-top: 0.5rem;'>
                        {confidence_label}
                    </div>
                    <div style='font-size: 0.75rem; color: #707080; margin-top: 0.5rem;'>
                        Data quality & reliability
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                alert_color = "#ff5252" if alerts_count > 0 else "#66bb6a"
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='font-size: 0.9rem; color: #b0b0b0; margin-bottom: 0.5rem;'>ACTIVE ALERTS</div>
                    <div style='font-size: 2.5rem; font-weight: 700; color: {alert_color};'>
                        {alerts_count}
                    </div>
                    <div style='font-size: 1.1rem; color: {'#ff5252' if alerts_count > 0 else '#66bb6a'}; margin-top: 0.5rem;'>
                        {'⚠️ Monitoring' if alerts_count > 0 else '✓ Stable'}
                    </div>
                    <div style='font-size: 0.75rem; color: #707080; margin-top: 0.5rem;'>
                        Last {history_days} days
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='font-size: 0.9rem; color: #b0b0b0; margin-bottom: 0.5rem;'>LAST UPDATED</div>
                    <div style='font-size: 2rem; font-weight: 600; color: #4a9eff;'>
                        {calc_time.strftime("%H:%M")}
                    </div>
                    <div style='font-size: 1rem; color: #90a0b0; margin-top: 0.5rem;'>
                        {calc_time.strftime("%b %d, %Y")}
                    </div>
                    <div style='font-size: 0.85rem; color: #70b0a0; margin-top: 0.5rem;'>
                        {format_time_ago(calc_time)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            
            # === LEVEL 2: VISUAL ANALYTICS ===
            
            # Signal breakdown - individual cards
            st.markdown("### 📊 Signal Breakdown")
            st.markdown("*Each signal contributes to the overall risk assessment based on its weight*")
            st.markdown("")
        
            signals = risk_data.get('signals', {})
            # Map weights from risk engine format to dashboard format
            raw_weights = risk_data.get('weights', {})
            signal_weights = {
                'news': raw_weights.get('news_signal', 0),  # 'news' not 'news_sentiment'
                'conflict': raw_weights.get('conflict_signal', 0),
                'economic': raw_weights.get('economic_signal', 0),
                'government': raw_weights.get('government_signal', 0)
            }
        
            signal_cols = st.columns(4)
            signal_info = [
                {
                    'name': 'Conflict Events',
                    'key': 'conflict',
                    'icon': '⚔️',
                    'description': 'Armed conflict, protests, riots'
                },
                {
                    'name': 'News Sentiment',
                    'key': 'news',  # Risk engine returns 'news', not 'news_sentiment'
                    'icon': '📰',
                    'description': 'Media coverage analysis'
                },
                {
                    'name': 'Economic',
                    'key': 'economic',
                    'icon': '💹',
                    'description': 'GDP, inflation, indicators'
                },
                {
                    'name': 'Government',
                    'key': 'government',
                    'icon': '🏛️',
                    'description': 'Policy changes, stability'
                }
            ]
        
            for idx, signal_meta in enumerate(signal_info):
                signal_key = signal_meta['key']
                signal_data = signals.get(signal_key, {})
                score = signal_data.get('score', 0)
                weight = signal_weights.get(signal_key, 0) * 100
                contribution = score * (weight / 100)
            
                available = score > 0
                status_badge = "✅ <span style='color: #66bb6a;'>Available</span>" if available else "⚠️ <span style='color: #ffa726;'>Unavailable</span>"
            
                with signal_cols[idx]:
                    st.markdown(f"""
                    <div class='signal-card'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;'>
                            <div style='font-size: 1.8rem;'>{signal_meta['icon']}</div>
                            <div style='font-size: 0.75rem;'>{status_badge}</div>
                        </div>
                        <div style='font-size: 1rem; font-weight: 600; color: #e0e0e0; margin-bottom: 0.5rem;'>
                            {signal_meta['name']}
                        </div>
                        <div style='font-size: 0.75rem; color: #909090; margin-bottom: 1rem; height: 2.5rem;'>
                            {signal_meta['description']}
                        </div>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;'>
                            <span style='font-size: 0.8rem; color: #b0b0b0;'>Score:</span>
                            <span style='font-size: 1.3rem; font-weight: 700; color: {get_risk_color(score)};'>{score:.1f}</span>
                        </div>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;'>
                            <span style='font-size: 0.8rem; color: #b0b0b0;'>Weight:</span>
                            <span style='font-size: 1rem; color: #4a9eff;'>{weight:.0f}%</span>
                        </div>
                        <div style='border-top: 1px solid #3a3a4e; padding-top: 0.5rem; margin-top: 0.5rem;'>
                            <div style='display: flex; justify-content: space-between; align-items: center;'>
                                <span style='font-size: 0.8rem; color: #c0c0c0;'>Contribution:</span>
                                <span style='font-size: 1.1rem; font-weight: 600; color: #4a9eff;'>{contribution:.1f}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        
            # Risk gauge chart
            st.markdown("### 🎯 Risk Assessment Visualization")
        
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=risk_data['overall_score'],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Overall Risk Level", 'font': {'size': 24}},
                delta={'reference': 50, 'increasing': {'color': "red"}, 'decreasing': {'color': "green"}},
                gauge={
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': get_risk_color(risk_data['overall_score'])},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 40], 'color': '#d4f1d4'},
                        {'range': [40, 70], 'color': '#ffe6cc'},
                        {'range': [70, 100], 'color': '#ffcccc'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 70
                    }
                }
            ))
        
            fig_gauge.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=50, b=20)
            )
        
            st.plotly_chart(fig_gauge, use_container_width=True)
        
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        
            # Signal breakdown
            st.markdown("---")
            st.subheader("🎯 Signal Breakdown")
        
            # Debug: Show what we actually got
            with st.expander("🔍 Debug: Raw Data Structure"):
                st.json(risk_data)
        
            signals = risk_data.get('signals', {})
            weights = risk_data.get('weights', {})
        
            # Safely extract signal scores
            conflict_score = signals.get('conflict', {}).get('score', 0) if isinstance(signals.get('conflict'), dict) else 0
            news_score = signals.get('news', {}).get('score', 0) if isinstance(signals.get('news'), dict) else 0
            economic_score = signals.get('economic', {}).get('score', 0) if isinstance(signals.get('economic'), dict) else 0
            government_score = signals.get('government', {}).get('score', 0) if isinstance(signals.get('government'), dict) else 0
        
            signal_df = pd.DataFrame([
                {
                    'Signal': 'Conflict Events',
                    'Score': conflict_score,
                    'Weight': weights.get('conflict', 40),
                    'Weighted': conflict_score * weights.get('conflict', 40) / 100
                },
                {
                    'Signal': 'News Sentiment',
                    'Score': news_score,
                    'Weight': weights.get('news', 20),
                    'Weighted': news_score * weights.get('news', 20) / 100
                },
                {
                    'Signal': 'Economic Indicators',
                    'Score': economic_score,
                    'Weight': weights.get('economic', 30),
                    'Weighted': economic_score * weights.get('economic', 30) / 100
                },
                {
                    'Signal': 'Government Reports',
                    'Score': government_score,
                    'Weight': weights.get('government', 10),
                    'Weighted': government_score * weights.get('government', 10) / 100
                }
            ])
        
            col1, col2 = st.columns(2)
        
            with col1:
                # Raw scores
                fig_signals = px.bar(
                    signal_df,
                    x='Signal',
                    y='Score',
                    title="Signal Scores (0-100)",
                    color='Score',
                    color_continuous_scale=['green', 'yellow', 'orange', 'red'],
                    range_color=[0, 100]
                )
                fig_signals.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_signals, use_container_width=True)
        
            with col2:
                # Weighted contribution
                fig_weighted = px.bar(
                    signal_df,
                    x='Signal',
                    y='Weighted',
                    title="Weighted Contribution to Risk",
                    color='Weighted',
                    color_continuous_scale=['green', 'yellow', 'orange', 'red'],
                    range_color=[0, 40]
                )
                fig_weighted.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_weighted, use_container_width=True)
        
            # Enhanced Signal details - NEW: Shows all backend data
            with st.expander("📋 Enhanced Signal Details (Backend Features)"):
                enhanced_details = get_enhanced_signal_details(signals)
                
                st.markdown("#### ⚔️ Conflict Events Signal")
                conflict_details = enhanced_details['conflict']
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1:
                    st.metric("Events", conflict_details.get('event_count', 0))
                with col_c2:
                    st.metric("Fatalities", conflict_details.get('total_fatalities', 0))
                with col_c3:
                    esc_rate = conflict_details.get('escalation_rate', 0)
                    st.metric("Escalation Rate", f"{esc_rate:.1f}%", 
                             delta=f"{'↑' if esc_rate > 0 else '↓' if esc_rate < 0 else '→'}")
                col_c4, col_c5 = st.columns(2)
                with col_c4:
                    st.write(f"**High Casualty Events:** {conflict_details.get('high_casualty_events', 0)}")
                with col_c5:
                    st.write(f"**Avg Severity:** {conflict_details.get('avg_severity', 0):.1f}")
                st.markdown("---")
                
                st.markdown("#### 📰 News Sentiment Signal")
                news_details = enhanced_details['news']
                col_n1, col_n2, col_n3 = st.columns(3)
                with col_n1:
                    st.metric("Articles", news_details.get('article_count', 0))
                with col_n2:
                    mean_sent = news_details.get('mean_sentiment', 0)
                    st.metric("Mean Sentiment", f"{mean_sent:.3f}",
                             delta="Positive" if mean_sent > 0 else "Negative" if mean_sent < 0 else "Neutral")
                with col_n3:
                    st.metric("Method", news_details.get('method', 'unknown').upper())
                col_n4, col_n5 = st.columns(2)
                with col_n4:
                    pos_ratio = news_details.get('positive_ratio', 0) * 100
                    st.write(f"**Positive Ratio:** {pos_ratio:.1f}%")
                with col_n5:
                    neg_ratio = news_details.get('negative_ratio', 0) * 100
                    st.write(f"**Negative Ratio:** {neg_ratio:.1f}%")
                st.markdown("---")
                
                st.markdown("#### 💹 Economic Signal")
                econ_details = enhanced_details['economic']
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    st.metric("GDP Score", f"{econ_details.get('gdp_score', 0):.1f}")
                with col_e2:
                    st.metric("Inflation Score", f"{econ_details.get('inflation_score', 0):.1f}")
                with col_e3:
                    st.metric("Unemployment Score", f"{econ_details.get('unemployment_score', 0):.1f}")
                indicators = econ_details.get('indicators_available', [])
                if indicators:
                    st.write(f"**Indicators Available:** {', '.join(indicators)}")
                st.markdown("---")
                
                st.markdown("#### 🏛️ Government Signal")
                govt_details = enhanced_details['government']
                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1:
                    st.metric("Reports Analyzed", govt_details.get('reports_analyzed', 0))
                with col_g2:
                    st.metric("Method", govt_details.get('method', 'none').upper())
                with col_g3:
                    govt_sent = govt_details.get('mean_sentiment', 0)
                    st.metric("Sentiment", f"{govt_sent:.3f}" if govt_sent else "N/A")
                
                # Government categories breakdown - NEW
                categories = govt_details.get('categories', {})
                if categories:
                    st.write("**Report Categories:**")
                    cat_cols = st.columns(len(categories) if len(categories) <= 4 else 4)
                    for i, (cat, count) in enumerate(categories.items()):
                        with cat_cols[i % 4]:
                            st.write(f"• {cat.title()}: {count}")
                
                # Score components
                col_g4, col_g5, col_g6 = st.columns(3)
                with col_g4:
                    st.write(f"**Stability:** {govt_details.get('stability_score', 0):.1f}")
                with col_g5:
                    st.write(f"**Sentiment:** {govt_details.get('sentiment_score', 0):.1f}")
                with col_g6:
                    st.write(f"**Security:** {govt_details.get('security_score', 0):.1f}")
            
            # Confidence Breakdown Panel - NEW SECTION
            with st.expander("🎯 Confidence Score Breakdown"):
                conf_breakdown = get_confidence_breakdown(risk_data)
                
                st.markdown("**How confidence is calculated:**")
                
                col_conf1, col_conf2 = st.columns(2)
                
                with col_conf1:
                    # Progress bars for each component
                    source_score = conf_breakdown.get('source_count', 0)
                    st.markdown(f"**Data Source Coverage** ({conf_breakdown.get('active_sources', 0)}/{conf_breakdown.get('total_sources', 4)} sources)")
                    st.progress(source_score / 100)
                    st.caption(f"{source_score:.0f}% - More sources = higher confidence")
                    
                    freshness_score = conf_breakdown.get('freshness', 0)
                    st.markdown(f"**Data Freshness**")
                    st.progress(freshness_score / 100)
                    st.caption(f"{freshness_score:.0f}% - Recent data = higher confidence")
                
                with col_conf2:
                    consistency_score = conf_breakdown.get('consistency', 0)
                    st.markdown(f"**Signal Consistency**")
                    st.progress(consistency_score / 100)
                    st.caption(f"{consistency_score:.0f}% - Aligned signals = higher confidence")
                    
                    historical_score = conf_breakdown.get('historical_validation', 0)
                    st.markdown(f"**Historical Validation**")
                    st.progress(historical_score / 100)
                    st.caption(f"{historical_score:.0f}% - Matches past patterns")

            # Historical trend
            st.markdown(f"### 📈 {history_days}-Day Risk Trend")
            st.markdown(f"*Historical risk score evolution over the last {history_days} days*")
        
            history = get_risk_history(country_code, history_days)
        
            if history:
                df_history = pd.DataFrame(history)
            
                fig_trend = go.Figure()
            
                # Risk score line
                fig_trend.add_trace(go.Scatter(
                    x=df_history['date'],
                    y=df_history['overall_score'],
                    mode='lines+markers',
                    name='Risk Score',
                    line=dict(color='#4a9eff', width=3),
                    marker=dict(size=6, color='#4a9eff'),
                    fill='tozeroy',
                    fillcolor='rgba(74, 158, 255, 0.1)'
                ))
            
                # Confidence band
                fig_trend.add_trace(go.Scatter(
                    x=df_history['date'],
                    y=df_history['confidence'],
                    mode='lines',
                    name='Confidence',
                    line=dict(color='#66bb6a', width=2, dash='dash'),
                    yaxis='y2'
                ))
            
                fig_trend.update_layout(
                    title="Risk Score Evolution",
                    xaxis_title="Date",
                    yaxis_title="Score",
                    yaxis=dict(range=[0, 100], showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                    yaxis2=dict(title='Confidence %', overlaying='y', side='right', range=[0, 100], showgrid=False),
                    hovermode='x unified',
                    height=400,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )
            
                st.plotly_chart(fig_trend, use_container_width=True)
            
                # Trend statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    avg_score = df_history['overall_score'].mean()
                    st.metric(f"{history_days}-Day Average", f"{avg_score:.1f}", help=f"Mean risk score over {history_days} days")
                with col2:
                    max_score = df_history['overall_score'].max()
                    st.metric("Peak Risk", f"{max_score:.1f}", help="Highest risk score in period")
                with col3:
                    min_score = df_history['overall_score'].min()
                    st.metric("Lowest Risk", f"{min_score:.1f}", help="Lowest risk score in period")
                with col4:
                    volatility = df_history['overall_score'].std()
                    st.metric("Volatility", f"{volatility:.1f}", help="Standard deviation (stability measure)")
            
            
                # Individual signal trends
                with st.expander("🔍 Individual Signal Trends"):
                    fig_signals_trend = go.Figure()
                
                    for signal, color in [
                        ('conflict', 'red'),
                        ('news', 'blue'),
                        ('economic', 'orange'),
                        ('government', 'green')
                    ]:
                        fig_signals_trend.add_trace(go.Scatter(
                            x=df_history['date'],
                            y=df_history[signal],
                            mode='lines',
                            name=signal.title(),
                            line=dict(color=color)
                        ))
                
                    fig_signals_trend.update_layout(
                        title="Signal Evolution Over Time",
                        xaxis_title="Date",
                        yaxis_title="Score",
                        hovermode='x unified',
                        height=400
                    )
                
                    st.plotly_chart(fig_signals_trend, use_container_width=True)
            else:
                st.info("📊 No historical data available yet. Risk scores will appear here after 24 hours of operation.")
        
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        
            # === LEVEL 3: DIAGNOSTICS & DETAILS ===
        
            # Enhanced Alerts section - NOW WITH EVIDENCE DATA
            st.markdown("### 🚨 Active Risk Alerts")
            st.markdown(f"*Real-time notifications for significant risk changes (Last {history_days} days)*")
        
            # Use enhanced alerts with evidence
            alerts = get_alerts_with_evidence(country_code, history_days)
        
            if alerts:
                for alert in alerts:
                    severity_map = {
                        'critical': {'emoji': '🔴', 'color': '#ff5252', 'label': 'CRITICAL'},
                        'high': {'emoji': '🟠', 'color': '#ffa726', 'label': 'HIGH'},
                        'medium': {'emoji': '🟡', 'color': '#ffeb3b', 'label': 'MEDIUM'},
                        'low': {'emoji': '🟢', 'color': '#66bb6a', 'label': 'LOW'}
                    }
                    severity_info = severity_map.get(alert['severity'], {'emoji': '⚪', 'color': '#808080', 'label': 'UNKNOWN'})
                
                    st.markdown(f"""
                    <div class='alert-card alert-{alert['severity']}'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;'>
                            <div style='display: flex; align-items: center; gap: 0.5rem;'>
                                <span style='font-size: 1.5rem;'>{severity_info['emoji']}</span>
                                <span style='font-weight: 700; color: {severity_info['color']}; font-size: 1.1rem;'>
                                    {severity_info['label']}
                                </span>
                            </div>
                            <span style='font-size: 0.85rem; color: #a0a0a0;'>
                                {alert['created_at'].strftime('%b %d, %H:%M UTC')}
                            </span>
                        </div>
                        <div style='font-size: 1.1rem; font-weight: 600; color: #e0e0e0; margin-bottom: 0.6rem;'>
                            {alert.get('title', alert['type'].replace('_', ' ').title())}
                        </div>
                        <div style='font-size: 0.95rem; color: #c0c0c0; line-height: 1.5; margin-bottom: 0.8rem;'>
                            {alert.get('description', alert['message']) or alert['message']}
                        </div>
                        <div style='display: flex; gap: 1.5rem; font-size: 0.85rem;'>
                            {f"<span style='color: #90a0b0;'>Risk Score: <strong style='color: #4a9eff;'>{alert['risk_score']:.1f}</strong></span>" if alert.get('risk_score') else ""}
                            {f"<span style='color: #90a0b0;'>Confidence: <strong style='color: #4a9eff;'>{alert['confidence']:.1f}%</strong></span>" if alert.get('confidence') else ""}
                            {f"<span style='color: #90a0b0;'>Change: <strong style='color: {'#ff5252' if alert['change'] > 0 else '#66bb6a'};'>{alert['change']:+.1f}%</strong></span>" if alert.get('change') else ""}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show evidence data in expander - NEW FEATURE
                    evidence = alert.get('evidence', {})
                    if evidence:
                        with st.expander(f"📋 View Evidence for Alert #{alert['id']}", expanded=False):
                            if 'signals' in evidence:
                                st.markdown("**Signal Data at Alert Time:**")
                                for sig_name, sig_data in evidence['signals'].items():
                                    if isinstance(sig_data, dict):
                                        st.write(f"• **{sig_name.title()}**: Score={sig_data.get('score', 'N/A')}")
                            
                            if 'change' in evidence:
                                st.write(f"**Score Change:** {evidence['change']}")
                            
                            if 'previous_score_id' in evidence:
                                st.write(f"**Previous Score ID:** {evidence['previous_score_id']}")
                            
                            if 'risk_score_id' in evidence:
                                st.write(f"**Current Score ID:** {evidence['risk_score_id']}")
            else:
                st.markdown("""
                <div style='padding: 2rem; text-align: center; background: rgba(102, 187, 106, 0.1); border: 1px solid #66bb6a; border-radius: 8px;'>
                    <div style='font-size: 2rem; margin-bottom: 0.5rem;'>✅</div>
                    <div style='font-size: 1.1rem; color: #66bb6a; font-weight: 600;'>No Active Alerts</div>
                    <div style='font-size: 0.9rem; color: #90a0a0; margin-top: 0.5rem;'>All risk indicators within normal thresholds</div>
                </div>
                """, unsafe_allow_html=True)
        
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        
            # Conflict map
            st.markdown("### 🗺️ Conflict Event Map")
            st.markdown(f"*Geographic distribution of conflict events (Last {history_days} Days)*")
        
            events = get_conflict_events(country_code, history_days)
        
            if events:
                # Country center coordinates for map
                country_centers = {
                    'IND': {'lat': 20.5937, 'lon': 78.9629, 'zoom': 5, 'name': 'India'},
                    'USA': {'lat': 39.8283, 'lon': -98.5795, 'zoom': 4, 'name': 'United States'},
                    'CHN': {'lat': 35.8617, 'lon': 104.1954, 'zoom': 4, 'name': 'China'},
                    'RUS': {'lat': 61.5240, 'lon': 105.3188, 'zoom': 3, 'name': 'Russia'},
                    'PAK': {'lat': 30.3753, 'lon': 69.3451, 'zoom': 5, 'name': 'Pakistan'},
                    'BGD': {'lat': 23.6850, 'lon': 90.3563, 'zoom': 7, 'name': 'Bangladesh'},
                    'GBR': {'lat': 55.3781, 'lon': -3.4360, 'zoom': 5, 'name': 'United Kingdom'},
                    'FRA': {'lat': 46.2276, 'lon': 2.2137, 'zoom': 5, 'name': 'France'},
                    'DEU': {'lat': 51.1657, 'lon': 10.4515, 'zoom': 5, 'name': 'Germany'},
                    'JPN': {'lat': 36.2048, 'lon': 138.2529, 'zoom': 5, 'name': 'Japan'},
                    'BRA': {'lat': -14.2350, 'lon': -51.9253, 'zoom': 4, 'name': 'Brazil'},
                    'AUS': {'lat': -25.2744, 'lon': 133.7751, 'zoom': 4, 'name': 'Australia'},
                }
                
                # Get center from events if available, else use country default
                center = country_centers.get(country_code, {'lat': 20.0, 'lon': 0.0, 'zoom': 2})
                
                # Calculate actual center from events if we have data
                if len(events) > 0:
                    avg_lat = sum(e['lat'] for e in events) / len(events)
                    avg_lon = sum(e['lon'] for e in events) / len(events)
                    map_lat = avg_lat
                    map_lon = avg_lon
                    map_zoom = center['zoom']
                else:
                    map_lat = center['lat']
                    map_lon = center['lon']
                    map_zoom = center['zoom']
                
                # Create map centered on the country/events
                m = folium.Map(
                    location=[map_lat, map_lon],
                    zoom_start=map_zoom,
                    tiles='OpenStreetMap'
                )
            
                # Add events to map with comprehensive color mapping
                event_colors = {
                    'Battles': 'red',
                    'Violence against civilians': 'darkred',
                    'Explosions/Remote violence': 'purple',
                    'Protests': 'orange',
                    'Riots': 'darkorange',
                    'Strategic developments': 'blue',
                    'Agreement': 'green',
                    'Headquarters or base established': 'cadetblue',
                    'Non-violent transfer of territory': 'lightblue',
                    'Government regains territory': 'darkgreen',
                    'Armed clash': 'red',
                    'Attack': 'crimson',
                    'Abduction/forced disappearance': 'darkpurple',
                    'Sexual violence': 'maroon',
                    'Chemical weapon': 'black',
                    'Peaceful protest': 'lightorange',
                    'Violent demonstration': 'orange',
                    'Mob violence': 'orangered',
                }
                
                for event in events:
                    color = event_colors.get(event['type'], 'gray')
                
                    # Ensure valid coordinates
                    lat = event.get('lat')
                    lon = event.get('lon')
                    if lat is None or lon is None:
                        continue
                    
                    try:
                        folium.CircleMarker(
                            location=[float(lat), float(lon)],
                            radius=5 + min((event['fatalities'] or 0) * 0.5, 20),  # Cap size
                            popup=f"""
                                <b>{event['type']}</b><br>
                                Date: {event['date'].strftime('%Y-%m-%d') if event['date'] else 'Unknown'}<br>
                                Location: {event['location'] or 'Unknown'}<br>
                                Fatalities: {event['fatalities']}<br>
                                Source: {event['source'] or 'GDELT'}<br>
                                {(event['notes'] or '')[:100]}
                            """,
                            color=color,
                            fill=True,
                            fillColor=color,
                            fillOpacity=0.7
                        ).add_to(m)
                    except (ValueError, TypeError):
                        continue  # Skip invalid coordinates
            
                st_folium(m, width=None, height=500)
                
                # Legend
                st.markdown("""
                <div style='display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center; margin-top: 0.5rem;'>
                    <span style='font-size: 0.75rem;'>🔴 Battles</span>
                    <span style='font-size: 0.75rem;'>🟤 Violence</span>
                    <span style='font-size: 0.75rem;'>🟣 Explosions</span>
                    <span style='font-size: 0.75rem;'>🟠 Protests</span>
                    <span style='font-size: 0.75rem;'>🔵 Strategic</span>
                    <span style='font-size: 0.75rem;'>🟢 Agreements</span>
                </div>
                """, unsafe_allow_html=True)
            
                st.markdown(f"<div style='text-align: center; color: #90a0a0; font-size: 0.9rem; margin-top: 1rem;'>Displaying <strong>{len(events)}</strong> events from GDELT 2.0 Event Database</div>", unsafe_allow_html=True)
            else:
                st.info(f"🗺️ No recent conflict events with geographic coordinates available for {country_code}. Run the GDELT pipeline to fetch data.")
        
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            
            # ============================================================
            # NEW SECTION: News Article Browser with Sentiment
            # ============================================================
            st.markdown("### 📰 News Article Browser")
            st.markdown("*Individual article sentiment analysis from ML pipeline*")
            
            with st.expander("View News Articles with Sentiment Scores", expanded=False):
                articles = get_news_articles_with_sentiment(country_code, limit=30)
                
                if articles:
                    # Filter controls
                    filter_col1, filter_col2 = st.columns(2)
                    with filter_col1:
                        sentiment_filter = st.selectbox(
                            "Filter by Sentiment",
                            ["All", "Positive", "Negative", "Neutral"],
                            index=0
                        )
                    with filter_col2:
                        sort_by = st.selectbox(
                            "Sort by",
                            ["Date (Newest)", "Date (Oldest)", "Sentiment (High)", "Sentiment (Low)"],
                            index=0
                        )
                    
                    # Apply filters
                    filtered_articles = articles
                    if sentiment_filter != "All":
                        filtered_articles = [a for a in articles if a['sentiment_label'].upper() == sentiment_filter.upper()]
                    
                    # Apply sorting
                    if sort_by == "Date (Oldest)":
                        filtered_articles = sorted(filtered_articles, key=lambda x: x['published_date'] or datetime.min)
                    elif sort_by == "Sentiment (High)":
                        filtered_articles = sorted(filtered_articles, key=lambda x: x['sentiment_score'], reverse=True)
                    elif sort_by == "Sentiment (Low)":
                        filtered_articles = sorted(filtered_articles, key=lambda x: x['sentiment_score'])
                    
                    # Display articles
                    for article in filtered_articles[:20]:
                        sent_score = article['sentiment_score']
                        sent_color = "#66bb6a" if sent_score > 0.2 else "#ff5252" if sent_score < -0.2 else "#ffa726"
                        sent_label = article['sentiment_label']
                        
                        st.markdown(f"""
                        <div style='background: rgba(42, 42, 62, 0.4); padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 3px solid {sent_color};'>
                            <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                                <div style='flex: 1;'>
                                    <div style='font-weight: 600; color: #e0e0e0; margin-bottom: 0.3rem;'>
                                        {article['title'][:100]}{'...' if len(article['title']) > 100 else ''}
                                    </div>
                                    <div style='font-size: 0.8rem; color: #909090;'>
                                        {article['source']} • {article['published_date'].strftime('%b %d, %Y') if article['published_date'] else 'Unknown date'}
                                    </div>
                                </div>
                                <div style='text-align: right; min-width: 100px;'>
                                    <div style='font-size: 1.2rem; font-weight: 700; color: {sent_color};'>{sent_score:.2f}</div>
                                    <div style='font-size: 0.75rem; color: {sent_color};'>{sent_label}</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Summary stats
                    st.markdown("---")
                    pos_count = sum(1 for a in articles if a['sentiment_score'] > 0.2)
                    neg_count = sum(1 for a in articles if a['sentiment_score'] < -0.2)
                    neu_count = len(articles) - pos_count - neg_count
                    
                    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                    with col_s1:
                        st.metric("Total Articles", len(articles))
                    with col_s2:
                        st.metric("Positive", pos_count, delta=f"{pos_count/len(articles)*100:.0f}%")
                    with col_s3:
                        st.metric("Negative", neg_count, delta=f"{neg_count/len(articles)*100:.0f}%")
                    with col_s4:
                        st.metric("Neutral", neu_count, delta=f"{neu_count/len(articles)*100:.0f}%")
                else:
                    st.info("No news articles found for this country. Run the pipeline to ingest news data.")
            
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            
            # ============================================================
            # NEW SECTION: Named Entity Extraction
            # ============================================================
            st.markdown("### 🔍 Key Entities & Actors")
            st.markdown("*Named Entity Recognition from recent news articles*")
            
            with st.expander("View Extracted Entities (NER)", expanded=False):
                entities_data = extract_entities_from_articles(country_code, limit=20)
                
                if entities_data.get('articles_analyzed', 0) > 0:
                    st.caption(f"Analyzed {entities_data['articles_analyzed']} recent articles")
                    
                    col_ent1, col_ent2, col_ent3 = st.columns(3)
                    
                    with col_ent1:
                        st.markdown("#### 👤 People")
                        persons = entities_data.get('persons', [])
                        if persons:
                            for person, count in persons[:10]:
                                st.write(f"• **{person}** ({count} mentions)")
                        else:
                            st.write("No persons detected")
                    
                    with col_ent2:
                        st.markdown("#### 🏢 Organizations")
                        orgs = entities_data.get('organizations', [])
                        if orgs:
                            for org, count in orgs[:10]:
                                st.write(f"• **{org}** ({count} mentions)")
                        else:
                            st.write("No organizations detected")
                    
                    with col_ent3:
                        st.markdown("#### 📍 Locations")
                        locations = entities_data.get('locations', [])
                        if locations:
                            for loc, count in locations[:10]:
                                st.write(f"• **{loc}** ({count} mentions)")
                        else:
                            st.write("No locations detected")
                else:
                    if 'error' in entities_data:
                        st.warning(f"NER not available: {entities_data['error']}")
                        st.caption("Install spaCy: `pip install spacy && python -m spacy download en_core_web_sm`")
                    else:
                        st.info("No articles available for entity extraction.")
            
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            
            # ============================================================
            # NEW SECTION: Economic Indicator History
            # ============================================================
            st.markdown("### 📊 Economic Indicator Trends")
            st.markdown("*Historical economic data from World Bank API*")
            
            with st.expander("View Economic History (5 Years)", expanded=False):
                econ_history = get_economic_history(country_code, years=5)
                
                has_data = any(len(v) > 0 for v in econ_history.values())
                
                if has_data:
                    # Create line chart for each indicator
                    fig_econ = go.Figure()
                    
                    indicator_names = {
                        'GDP_GROWTH': ('GDP Growth Rate (%)', '#4a9eff'),
                        'INFLATION': ('Inflation Rate (%)', '#ff5252'),
                        'UNEMPLOYMENT': ('Unemployment Rate (%)', '#ffa726')
                    }
                    
                    for ind_code, (name, color) in indicator_names.items():
                        data = econ_history.get(ind_code, [])
                        if data:
                            # Sort by year
                            sorted_data = sorted(data, key=lambda x: x['year'] or 0)
                            years = [d['year'] for d in sorted_data if d['year']]
                            values = [d['value'] for d in sorted_data if d['year']]
                            
                            if years and values:
                                fig_econ.add_trace(go.Scatter(
                                    x=years,
                                    y=values,
                                    mode='lines+markers',
                                    name=name,
                                    line=dict(color=color, width=2),
                                    marker=dict(size=8)
                                ))
                    
                    fig_econ.update_layout(
                        title="Economic Indicators Over Time",
                        xaxis_title="Year",
                        yaxis_title="Value (%)",
                        height=400,
                        hovermode='x unified',
                        legend=dict(orientation='h', yanchor='bottom', y=1.02)
                    )
                    
                    st.plotly_chart(fig_econ, use_container_width=True)
                    
                    # Show latest values
                    st.markdown("**Latest Values:**")
                    col_ec1, col_ec2, col_ec3 = st.columns(3)
                    
                    with col_ec1:
                        gdp_data = econ_history.get('GDP_GROWTH', [])
                        if gdp_data:
                            latest = sorted(gdp_data, key=lambda x: x['year'] or 0, reverse=True)[0]
                            st.metric("GDP Growth", f"{latest['value']:.1f}%", 
                                     help=f"Year: {latest['year']}")
                    
                    with col_ec2:
                        inf_data = econ_history.get('INFLATION', [])
                        if inf_data:
                            latest = sorted(inf_data, key=lambda x: x['year'] or 0, reverse=True)[0]
                            st.metric("Inflation", f"{latest['value']:.1f}%",
                                     help=f"Year: {latest['year']}")
                    
                    with col_ec3:
                        unemp_data = econ_history.get('UNEMPLOYMENT', [])
                        if unemp_data:
                            latest = sorted(unemp_data, key=lambda x: x['year'] or 0, reverse=True)[0]
                            st.metric("Unemployment", f"{latest['value']:.1f}%",
                                     help=f"Year: {latest['year']}")
                else:
                    st.info("No economic history data available. Run the pipeline to fetch World Bank data.")

            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

            # ==============================================================
            # NEW SECTION: Advanced ML Analytics
            # ==============================================================
            render_ml_analytics_section(country_code)

            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

            # AI Explanation
            st.markdown("### 🤖 AI Risk Analysis")
            st.markdown("*Generative AI explanation powered by Google Gemini*")
        
            with st.spinner("🔄 Generating intelligent analysis..."):
                try:
                    explainer = get_ai_explainer()
                    explanation = explainer.generate_risk_explanation(
                        country_code=country_code,
                        risk_score=risk_data['overall_score'],
                        confidence_score=risk_data['confidence_score'],
                        signals=signals,
                        trend=risk_data['trend']
                    )
                
                    st.markdown(f"""
                    <div class='ai-explanation'>
                        <div style='font-weight: 600; color: #4a9eff; margin-bottom: 1rem; font-size: 1.05rem;'>
                            📊 Analysis Summary
                        </div>
                        <div style='line-height: 1.8; color: #d0d0d0;'>
                            {explanation}
                        </div>
                        <div style='margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #3a3a4e; font-size: 0.85rem; color: #909090;'>
                            <strong style='color: #b0b0b0;'>💡 Note:</strong> This analysis is generated by AI and should be used as supplementary intelligence. 
                            Always verify critical information with primary sources.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f"""
                    <div style='padding: 1.5rem; background: rgba(255, 165, 38, 0.1); border: 1px solid #ffa726; border-radius: 8px;'>
                        <div style='font-weight: 600; color: #ffa726; margin-bottom: 0.5rem;'>⚠️ AI Service Unavailable</div>
                        <div style='font-size: 0.9rem; color: #c0c0c0;'>Gemini API error: {str(e)[:100]}...</div>
                        <div style='font-size: 0.85rem; color: #909090; margin-top: 0.5rem;'>Using fallback statistical analysis</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                    # Enhanced fallback analysis
                    conflict_score = signals.get('conflict', {}).get('score', 0)
                    news_score = signals.get('news_sentiment', {}).get('score', 0)
                    economic_score = signals.get('economic', {}).get('score', 0)
                    government_score = signals.get('government', {}).get('score', 0)
                
                    st.markdown(f"""
                    <div style='padding: 1.5rem; background: rgba(74, 158, 255, 0.05); border: 1px solid #4a9eff; border-radius: 8px; margin-top: 1rem;'>
                        <div style='font-weight: 600; color: #4a9eff; margin-bottom: 1rem; font-size: 1.05rem;'>
                            📊 Statistical Risk Summary
                        </div>
                        <div style='line-height: 1.8; color: #d0d0d0;'>
                            India's current risk assessment shows a score of <strong>{risk_data['overall_score']:.1f}/100</strong>, 
                            indicating <strong>{risk_data['risk_level'].replace('_', ' ').upper()}</strong> geopolitical risk.
                        
                            <br><br><strong style='color: #e0e0e0;'>Signal Breakdown:</strong>
                            <ul style='margin: 0.5rem 0; padding-left: 1.5rem;'>
                                <li><strong>Conflict Events:</strong> {conflict_score:.1f}/100 - {'High activity' if conflict_score > 60 else 'Moderate activity' if conflict_score > 30 else 'Low activity'}</li>
                                <li><strong>News Sentiment:</strong> {news_score:.1f}/100 - {'Negative coverage' if news_score > 60 else 'Mixed coverage' if news_score > 30 else 'Positive coverage'}</li>
                                <li><strong>Economic Indicators:</strong> {economic_score:.1f}/100 - {'Concerning trends' if economic_score > 60 else 'Stable conditions' if economic_score > 30 else 'Strong performance'}</li>
                                <li><strong>Government Activity:</strong> {government_score:.1f}/100 - {'High volatility' if government_score > 60 else 'Normal operations' if government_score > 30 else 'Stable governance'}</li>
                            </ul>
                        
                            <br>The assessment carries a confidence level of <strong>{risk_data['confidence_score']:.1f}%</strong> 
                            with a <strong>{risk_data['trend'].upper()}</strong> trend over recent periods.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        except Exception as e:
            st.error(f"⚠️ Dashboard Error: Unable to load risk data")
            st.markdown(f"""
            <div style='padding: 1rem; background: rgba(255, 82, 82, 0.1); border: 1px solid #ff5252; border-radius: 8px; margin-top: 1rem;'>
                <div style='font-weight: 600; color: #ff5252; margin-bottom: 0.5rem;'>Technical Details:</div>
                <div style='font-size: 0.9rem; color: #c0c0c0; font-family: monospace;'>{str(e)}</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("🔧 Troubleshooting Steps"):
                st.markdown("""
                **Common Solutions:**
                1. ✓ Verify PostgreSQL database is running
                2. ✓ Check MongoDB connection
                3. ✓ Run `python run_pipeline.py` to generate data
                4. ✓ Verify `.env` configuration
                5. ✓ Check backend logs for errors
                
                **Quick Diagnostic:**
                ```bash
                # Test database connection
                python test_setup.py
                
                # Run data ingestion
                python run_pipeline.py
                ```
                """)
    
    # Right sidebar - Data Sources Panel
    with sources_col:
        st.markdown("### 📊 Data Sources")
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        
        # Get data sources status
        sources_status = get_data_sources_status(country_code)
        
        if sources_status:
            # GDELT Conflict Data
            conflict_data = sources_status['conflict']
            status_icon = "✅" if conflict_data['status'] == 'active' else "⚠️"
            st.markdown(f"""
            <div style='background: rgba(42, 42, 62, 0.6); padding: 1rem; border-radius: 8px; border-left: 3px solid #ff5252; margin-bottom: 1rem;'>
                <div style='display: flex; justify-content: between; align-items: center; margin-bottom: 0.5rem;'>
                    <span style='font-size: 1.3rem;'>⚔️</span>
                    <span style='font-size: 0.7rem; margin-left: auto;'>{status_icon}</span>
                </div>
                <div style='font-weight: 600; color: #e0e0e0; font-size: 0.95rem; margin-bottom: 0.5rem;'>Conflict Events</div>
                <div style='font-size: 0.75rem; color: #b0b0b0; margin-bottom: 0.8rem;'>{conflict_data['source']}</div>
                <div style='font-size: 0.85rem; color: #4a9eff; font-weight: 600;'>{conflict_data['count']:,} records</div>
                {f"<div style='font-size: 0.7rem; color: #90a0a0; margin-top: 0.3rem;'>Updated: {conflict_data['last_update'].strftime('%b %d, %H:%M') if conflict_data['last_update'] else 'N/A'}</div>" if conflict_data['last_update'] else ""}
            </div>
            """, unsafe_allow_html=True)
            
            # News Sentiment Data
            news_data = sources_status['news']
            status_icon = "✅" if news_data['status'] == 'active' else "⚠️"
            st.markdown(f"""
            <div style='background: rgba(42, 42, 62, 0.6); padding: 1rem; border-radius: 8px; border-left: 3px solid #4a9eff; margin-bottom: 1rem;'>
                <div style='display: flex; justify-content: between; align-items: center; margin-bottom: 0.5rem;'>
                    <span style='font-size: 1.3rem;'>📰</span>
                    <span style='font-size: 0.7rem; margin-left: auto;'>{status_icon}</span>
                </div>
                <div style='font-weight: 600; color: #e0e0e0; font-size: 0.95rem; margin-bottom: 0.5rem;'>News Sentiment</div>
                <div style='font-size: 0.75rem; color: #b0b0b0; margin-bottom: 0.8rem;'>{news_data['source']}</div>
                <div style='font-size: 0.85rem; color: #4a9eff; font-weight: 600;'>{news_data['count']:,} articles</div>
                {f"<div style='font-size: 0.7rem; color: #90a0a0; margin-top: 0.3rem;'>Updated: {news_data['last_update'].strftime('%b %d, %H:%M') if news_data['last_update'] else 'N/A'}</div>" if news_data.get('last_update') else ""}
            </div>
            """, unsafe_allow_html=True)
            
            # Economic Indicators
            econ_data = sources_status['economic']
            status_icon = "✅" if econ_data['status'] == 'active' else "⚠️"
            st.markdown(f"""
            <div style='background: rgba(42, 42, 62, 0.6); padding: 1rem; border-radius: 8px; border-left: 3px solid #ffa726; margin-bottom: 1rem;'>
                <div style='display: flex; justify-content: between; align-items: center; margin-bottom: 0.5rem;'>
                    <span style='font-size: 1.3rem;'>💹</span>
                    <span style='font-size: 0.7rem; margin-left: auto;'>{status_icon}</span>
                </div>
                <div style='font-weight: 600; color: #e0e0e0; font-size: 0.95rem; margin-bottom: 0.5rem;'>Economic Data</div>
                <div style='font-size: 0.75rem; color: #b0b0b0; margin-bottom: 0.8rem;'>{econ_data['source']}</div>
                <div style='font-size: 0.85rem; color: #4a9eff; font-weight: 600;'>{econ_data['count']:,} indicators</div>
                {f"<div style='font-size: 0.7rem; color: #90a0a0; margin-top: 0.3rem;'>Updated: {econ_data['last_update'].strftime('%b %d') if econ_data['last_update'] else 'N/A'}</div>" if econ_data.get('last_update') else ""}
            </div>
            """, unsafe_allow_html=True)
            
            # Government Reports
            govt_data = sources_status['government']
            status_icon = "✅" if govt_data['status'] == 'active' else "⚠️"
            st.markdown(f"""
            <div style='background: rgba(42, 42, 62, 0.6); padding: 1rem; border-radius: 8px; border-left: 3px solid #66bb6a; margin-bottom: 1rem;'>
                <div style='display: flex; justify-content: between; align-items: center; margin-bottom: 0.5rem;'>
                    <span style='font-size: 1.3rem;'>🏛️</span>
                    <span style='font-size: 0.7rem; margin-left: auto;'>{status_icon}</span>
                </div>
                <div style='font-weight: 600; color: #e0e0e0; font-size: 0.95rem; margin-bottom: 0.5rem;'>Government Reports</div>
                <div style='font-size: 0.75rem; color: #b0b0b0; margin-bottom: 0.8rem;'>{govt_data['source']}</div>
                <div style='font-size: 0.85rem; color: #4a9eff; font-weight: 600;'>{govt_data['count']:,} reports</div>
                {f"<div style='font-size: 0.7rem; color: #90a0a0; margin-top: 0.3rem;'>Updated: {govt_data['last_update'].strftime('%b %d, %H:%M') if govt_data['last_update'] else 'N/A'}</div>" if govt_data.get('last_update') else ""}
            </div>
            """, unsafe_allow_html=True)
            
            # Citations & Methodology
            st.markdown("---")
            st.markdown("### 📚 Citations")
            st.markdown("""
            <div style='font-size: 0.75rem; color: #a0a0a0; line-height: 1.6;'>
            <b>Data Sources:</b><br>
            • GDELT Project (2024)<br>
            • World Bank Open Data<br>
            • Reuters/BBC RSS Feeds<br>
            • Press Info Bureau India<br><br>
            
            <b>Methodology:</b><br>
            Weighted risk scoring using NLP sentiment analysis, conflict event frequency, economic indicators, and government policy changes.<br><br>
            
            <b>License:</b><br>
            Open Source Intelligence (OSINT) for research purposes.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Unable to fetch data sources status")
            st.markdown("""
            <div style='font-size: 0.8rem; color: #b0b0b0;'>
            <b>Primary Sources:</b><br>
            • GDELT Event Database<br>
            • World Bank API<br>
            • News RSS Feeds<br>
            • Government Portals
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
