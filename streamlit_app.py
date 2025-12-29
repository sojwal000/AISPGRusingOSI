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
        
            # Signal details
            with st.expander("📋 Signal Details"):
                for signal_name, signal_key, default_weight in [
                    ("Conflict Events", "conflict", 40),
                    ("News Sentiment", "news", 20),
                    ("Economic Indicators", "economic", 30),
                    ("Government Reports", "government", 10)
                ]:
                    st.markdown(f"**{signal_name}** (Weight: {weights.get(signal_key, default_weight)}%)")
                    signal_data = signals.get(signal_key, {})
                    if isinstance(signal_data, dict):
                        st.write(f"Score: {signal_data.get('score', 0):.1f}/100")
                    
                        if 'details' in signal_data and signal_data['details']:
                            details = signal_data['details']
                            for key, value in details.items():
                                if value is not None:
                                    st.write(f"  - {key.replace('_', ' ').title()}: {value}")
                    else:
                        st.write(f"Score: {signal_data if isinstance(signal_data, (int, float)) else 0:.1f}/100")
                    st.markdown("---")
        
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
        
            # Alerts section
            st.markdown("### 🚨 Active Risk Alerts")
            st.markdown(f"*Real-time notifications for significant risk changes (Last {history_days} days)*")
        
            alerts = get_recent_alerts(country_code, history_days)
        
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
                            {alert['type'].replace('_', ' ').title()}
                        </div>
                        <div style='font-size: 0.95rem; color: #c0c0c0; line-height: 1.5; margin-bottom: 0.8rem;'>
                            {alert['message']}
                        </div>
                        <div style='display: flex; gap: 1.5rem; font-size: 0.85rem;'>
                            {f"<span style='color: #90a0b0;'>Confidence: <strong style='color: #4a9eff;'>{alert['confidence']:.1f}%</strong></span>" if alert['confidence'] else ""}
                            {f"<span style='color: #90a0b0;'>Change: <strong style='color: {'#ff5252' if alert['change'] > 0 else '#66bb6a'};'>{alert['change']:+.1f}%</strong></span>" if alert['change'] else ""}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
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
                # Create map centered on India
                m = folium.Map(
                    location=[20.5937, 78.9629],  # India center
                    zoom_start=5,
                    tiles='OpenStreetMap'
                )
            
                # Add events to map
                for event in events:
                    color = {
                        'Battles': 'red',
                        'Violence against civilians': 'darkred',
                        'Protests': 'orange',
                        'Strategic developments': 'blue'
                    }.get(event['type'], 'gray')
                
                    folium.CircleMarker(
                        location=[event['lat'], event['lon']],
                        radius=5 + (event['fatalities'] * 0.5),  # Size based on fatalities
                        popup=f"""
                            <b>{event['type']}</b><br>
                            Date: {event['date'].strftime('%Y-%m-%d')}<br>
                            Location: {event['location']}<br>
                            Fatalities: {event['fatalities']}<br>
                            Source: {event['source']}<br>
                            {event['notes'][:100]}
                        """,
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=0.7
                    ).add_to(m)
            
                st_folium(m, width=None, height=500)
            
                st.markdown(f"<div style='text-align: center; color: #90a0a0; font-size: 0.9rem; margin-top: 1rem;'>Displaying <strong>{len(events)}</strong> events from GDELT 2.0 Event Database</div>", unsafe_allow_html=True)
            else:
                st.info("🗺️ No recent conflict events with geographic coordinates available")
        
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
