from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict


class CountryResponse(BaseModel):
    """Country response schema"""
    id: int
    code: str
    name: str
    region: Optional[str]
    
    class Config:
        from_attributes = True


class RiskScoreResponse(BaseModel):
    """Risk score response schema"""
    country_code: str
    overall_score: float
    risk_level: str
    trend: Optional[str]
    date: datetime
    signals: Dict[str, float]


class AlertResponse(BaseModel):
    """Alert response schema"""
    id: int
    country_code: str
    alert_type: str
    severity: str
    title: str
    description: Optional[str]
    risk_score: Optional[float]
    triggered_at: datetime
    status: str
    
    class Config:
        from_attributes = True
