from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from datetime import datetime
from ..core.database import Base


class Country(Base):
    """Country master table"""
    __tablename__ = "countries"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(3), unique=True, nullable=False, index=True)  # ISO 3-letter code
    name = Column(String(100), nullable=False)
    region = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    

class RiskScore(Base):
    """Risk scores over time for each country"""
    __tablename__ = "risk_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String(3), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    
    # Overall risk score (0-100)
    overall_score = Column(Float, nullable=False)
    
    # Signal component scores
    news_signal_score = Column(Float, default=0.0)
    conflict_signal_score = Column(Float, default=0.0)
    economic_signal_score = Column(Float, default=0.0)
    government_signal_score = Column(Float, default=0.0)
    
    # Phase 2: Confidence scoring (0-100)
    confidence_score = Column(Float, default=0.0)
    
    # Trend indicator
    trend = Column(String(20))  # "increasing", "decreasing", "stable"
    
    # Metadata
    calculation_metadata = Column(Text)  # JSON string with calculation details
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_country_date', 'country_code', 'date'),
    )


class Alert(Base):
    """Generated alerts based on risk threshold breaches"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String(3), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # "threshold_breach", "sudden_spike", etc.
    severity = Column(String(20), nullable=False)  # "low", "medium", "high", "critical"
    
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    risk_score = Column(Float)
    previous_score = Column(Float)
    
    # Phase 2: Enhanced alert metadata
    confidence_score = Column(Float, default=0.0)  # Confidence in alert (0-100)
    change_percentage = Column(Float)  # Percentage change that triggered alert
    ai_explanation = Column(Text)  # Natural language explanation from Gemini
    
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    status = Column(String(20), default="new")  # "new", "reviewed", "archived"
    
    evidence = Column(Text)  # JSON string with supporting evidence
    created_at = Column(DateTime, default=datetime.utcnow)


class EconomicIndicator(Base):
    """Economic indicators from World Bank and other sources"""
    __tablename__ = "economic_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String(3), nullable=False, index=True)
    indicator_code = Column(String(50), nullable=False, index=True)  # e.g., "GDP_GROWTH", "INFLATION"
    indicator_name = Column(String(200))
    
    date = Column(DateTime, nullable=False, index=True)
    value = Column(Float)
    
    source = Column(String(100))  # "World Bank", "RBI", etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_country_indicator_date', 'country_code', 'indicator_code', 'date'),
    )


class ConflictEvent(Base):
    """Conflict and protest events from ACLED"""
    __tablename__ = "conflict_events"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(50), unique=True)  # ACLED event ID
    
    country_code = Column(String(3), nullable=False, index=True)
    event_date = Column(DateTime, nullable=False, index=True)
    
    event_type = Column(String(100))  # "Protests", "Riots", "Violence against civilians", etc.
    sub_event_type = Column(String(100))
    
    actor1 = Column(String(200))
    actor2 = Column(String(200))
    
    location = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    
    fatalities = Column(Integer, default=0)
    notes = Column(Text)
    
    source = Column(String(100), default="ACLED")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_country_event_date', 'country_code', 'event_date'),
    )
