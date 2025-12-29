"""
Phase 2: Advanced Alert Detection Module
Detects various alert patterns including sudden spikes, sustained highs, and rapid escalation.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.sql_models import RiskScore, Alert
from app.core.logging import setup_logger
import json

logger = setup_logger(__name__)


class AdvancedAlertDetector:
    """
    Detects advanced alert patterns beyond simple threshold breaches.
    
    Alert Types:
    1. risk_increase: >15% increase from previous score
    2. sudden_spike: >30% increase within 24 hours
    3. sustained_high: Score >70 for 48+ hours
    4. rapid_escalation: >50% increase within 6 hours
    """
    
    THRESHOLDS = {
        "risk_increase": 15.0,      # >15% increase
        "sudden_spike": 30.0,       # >30% in 24h
        "sustained_high": 70.0,     # Score >70
        "sustained_duration": 48,   # 48 hours
        "rapid_escalation": 50.0,   # >50% in 6h
        "rapid_window": 6           # 6 hours
    }
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def detect_all_alerts(
        self,
        country_code: str,
        current_score: float,
        confidence_score: float,
        signals: Dict,
        risk_score_id: int
    ) -> List[Dict]:
        """
        Run all alert detection algorithms.
        
        Args:
            country_code: Country to check
            current_score: Current risk score
            confidence_score: Confidence in the assessment
            signals: Dict of signal components
            risk_score_id: ID of the current risk score record
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        try:
            # 1. Check for risk increase
            increase_alert = self._check_risk_increase(
                country_code, current_score, confidence_score, signals, risk_score_id
            )
            if increase_alert:
                alerts.append(increase_alert)
            
            # 2. Check for sudden spike
            spike_alert = self._check_sudden_spike(
                country_code, current_score, confidence_score, signals, risk_score_id
            )
            if spike_alert:
                alerts.append(spike_alert)
            
            # 3. Check for sustained high risk
            sustained_alert = self._check_sustained_high(
                country_code, current_score, confidence_score, signals, risk_score_id
            )
            if sustained_alert:
                alerts.append(sustained_alert)
            
            # 4. Check for rapid escalation
            escalation_alert = self._check_rapid_escalation(
                country_code, current_score, confidence_score, signals, risk_score_id
            )
            if escalation_alert:
                alerts.append(escalation_alert)
            
            # Create Alert records in database
            created_alerts = []
            for alert_data in alerts:
                if self._should_create_alert(country_code, alert_data["alert_type"]):
                    alert = self._create_alert_record(country_code, alert_data)
                    if alert:
                        created_alerts.append(alert)
            
            return created_alerts
            
        except Exception as e:
            logger.error(f"Error in alert detection: {e}")
            return []
    
    def _check_risk_increase(
        self,
        country_code: str,
        current_score: float,
        confidence_score: float,
        signals: Dict,
        risk_score_id: int
    ) -> Optional[Dict]:
        """Check for significant risk increase (>15%)"""
        try:
            # Get previous score (last 7 days)
            previous = self._get_previous_score(country_code, days=7)
            
            if not previous:
                return None
            
            previous_score = previous.overall_score
            change = current_score - previous_score
            change_percent = (change / previous_score * 100) if previous_score > 0 else 0
            
            if change_percent >= self.THRESHOLDS["risk_increase"]:
                severity = self._calculate_severity(change_percent, "increase")
                
                return {
                    "alert_type": "risk_increase",
                    "severity": severity,
                    "title": f"Risk Increase Alert: {country_code}",
                    "description": f"Risk score increased by {change_percent:.1f}% from {previous_score:.1f} to {current_score:.1f}",
                    "risk_score": current_score,
                    "previous_score": previous_score,
                    "confidence_score": confidence_score,
                    "change_percentage": change_percent,
                    "evidence": {
                        "risk_score_id": risk_score_id,
                        "previous_score_id": previous.id,
                        "signals": signals,
                        "change": change
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking risk increase: {e}")
            return None
    
    def _check_sudden_spike(
        self,
        country_code: str,
        current_score: float,
        confidence_score: float,
        signals: Dict,
        risk_score_id: int
    ) -> Optional[Dict]:
        """Check for sudden spike (>30% in 24h)"""
        try:
            # Get score from 24 hours ago
            previous = self._get_previous_score(country_code, hours=24)
            
            if not previous:
                return None
            
            previous_score = previous.overall_score
            change = current_score - previous_score
            change_percent = (change / previous_score * 100) if previous_score > 0 else 0
            
            if change_percent >= self.THRESHOLDS["sudden_spike"]:
                severity = "critical" if change_percent >= 50 else "high"
                
                # Identify primary driver
                driver = self._identify_primary_driver(signals)
                
                return {
                    "alert_type": "sudden_spike",
                    "severity": severity,
                    "title": f"SUDDEN SPIKE: {country_code} Risk Up {change_percent:.0f}% in 24h",
                    "description": f"Risk jumped from {previous_score:.1f} to {current_score:.1f} within 24 hours. Primary driver: {driver}",
                    "risk_score": current_score,
                    "previous_score": previous_score,
                    "confidence_score": confidence_score,
                    "change_percentage": change_percent,
                    "evidence": {
                        "risk_score_id": risk_score_id,
                        "previous_score_id": previous.id,
                        "signals": signals,
                        "primary_driver": driver,
                        "time_window": "24 hours"
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking sudden spike: {e}")
            return None
    
    def _check_sustained_high(
        self,
        country_code: str,
        current_score: float,
        confidence_score: float,
        signals: Dict,
        risk_score_id: int
    ) -> Optional[Dict]:
        """Check for sustained high risk (>70 for 48+ hours)"""
        try:
            if current_score < self.THRESHOLDS["sustained_high"]:
                return None
            
            # Get all scores from last 48 hours
            cutoff = datetime.utcnow() - timedelta(hours=self.THRESHOLDS["sustained_duration"])
            scores = self.db.query(RiskScore).filter(
                RiskScore.country_code == country_code,
                RiskScore.date >= cutoff
            ).order_by(RiskScore.date).all()
            
            if len(scores) < 2:
                return None
            
            # Check if all scores are above threshold
            all_high = all(score.overall_score >= self.THRESHOLDS["sustained_high"] for score in scores)
            
            if all_high:
                duration_hours = (datetime.utcnow() - scores[0].date).total_seconds() / 3600
                avg_score = sum(s.overall_score for s in scores) / len(scores)
                
                return {
                    "alert_type": "sustained_high",
                    "severity": "critical",
                    "title": f"SUSTAINED HIGH RISK: {country_code}",
                    "description": f"Risk has remained above {self.THRESHOLDS['sustained_high']:.0f} for {duration_hours:.1f} hours (avg: {avg_score:.1f})",
                    "risk_score": current_score,
                    "previous_score": scores[0].overall_score,
                    "confidence_score": confidence_score,
                    "change_percentage": 0,  # No immediate change, but sustained
                    "evidence": {
                        "risk_score_id": risk_score_id,
                        "signals": signals,
                        "duration_hours": duration_hours,
                        "avg_score": avg_score,
                        "score_count": len(scores)
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking sustained high: {e}")
            return None
    
    def _check_rapid_escalation(
        self,
        country_code: str,
        current_score: float,
        confidence_score: float,
        signals: Dict,
        risk_score_id: int
    ) -> Optional[Dict]:
        """Check for rapid escalation (>50% in 6h)"""
        try:
            # Get score from 6 hours ago
            previous = self._get_previous_score(country_code, hours=self.THRESHOLDS["rapid_window"])
            
            if not previous:
                return None
            
            previous_score = previous.overall_score
            change = current_score - previous_score
            change_percent = (change / previous_score * 100) if previous_score > 0 else 0
            
            if change_percent >= self.THRESHOLDS["rapid_escalation"]:
                # This is critical - very rapid escalation
                driver = self._identify_primary_driver(signals)
                
                return {
                    "alert_type": "rapid_escalation",
                    "severity": "critical",
                    "title": f"⚠️ RAPID ESCALATION: {country_code}",
                    "description": f"CRITICAL: Risk escalated {change_percent:.0f}% in just {self.THRESHOLDS['rapid_window']} hours ({previous_score:.1f}→{current_score:.1f}). Driver: {driver}",
                    "risk_score": current_score,
                    "previous_score": previous_score,
                    "confidence_score": confidence_score,
                    "change_percentage": change_percent,
                    "evidence": {
                        "risk_score_id": risk_score_id,
                        "previous_score_id": previous.id,
                        "signals": signals,
                        "primary_driver": driver,
                        "time_window": f"{self.THRESHOLDS['rapid_window']} hours"
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking rapid escalation: {e}")
            return None
    
    def _get_previous_score(
        self,
        country_code: str,
        days: Optional[int] = None,
        hours: Optional[int] = None
    ) -> Optional[RiskScore]:
        """Get previous risk score within time window"""
        try:
            if hours:
                cutoff = datetime.utcnow() - timedelta(hours=hours)
            elif days:
                cutoff = datetime.utcnow() - timedelta(days=days)
            else:
                cutoff = datetime.utcnow() - timedelta(days=1)
            
            return self.db.query(RiskScore).filter(
                RiskScore.country_code == country_code,
                RiskScore.date < datetime.utcnow(),
                RiskScore.date >= cutoff
            ).order_by(RiskScore.date.desc()).first()
            
        except Exception:
            return None
    
    def _identify_primary_driver(self, signals: Dict) -> str:
        """Identify which signal is driving the risk"""
        try:
            scores = {
                "News": signals.get("news", {}).get("score", 0),
                "Conflict": signals.get("conflict", {}).get("score", 0),
                "Economic": signals.get("economic", {}).get("score", 0),
                "Government": signals.get("government", {}).get("score", 0)
            }
            
            if not any(scores.values()):
                return "Unknown"
            
            max_signal = max(scores, key=scores.get)
            max_score = scores[max_signal]
            
            # Add detail if available
            if max_signal == "Conflict":
                escalation = signals.get("conflict", {}).get("escalation_rate", 0)
                if escalation > 50:
                    return f"Conflict (escalating {escalation:.0f}%)"
            
            return f"{max_signal} ({max_score:.0f})"
            
        except Exception:
            return "Multiple factors"
    
    def _calculate_severity(self, change_percent: float, alert_type: str) -> str:
        """Calculate alert severity based on change magnitude"""
        if alert_type == "increase":
            if change_percent >= 40:
                return "critical"
            elif change_percent >= 25:
                return "high"
            elif change_percent >= 15:
                return "medium"
            else:
                return "low"
        
        return "medium"
    
    def _should_create_alert(self, country_code: str, alert_type: str) -> bool:
        """Check if similar alert was recently created (avoid duplicates)"""
        try:
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_alert = self.db.query(Alert).filter(
                Alert.country_code == country_code,
                Alert.alert_type == alert_type,
                Alert.triggered_at >= recent_cutoff
            ).first()
            
            return recent_alert is None
            
        except Exception as e:
            logger.error(f"Error checking for duplicate alerts: {e}")
            return True  # If check fails, allow alert creation
    
    def _create_alert_record(self, country_code: str, alert_data: Dict) -> Optional[Alert]:
        """Create Alert database record"""
        try:
            alert = Alert(
                country_code=country_code,
                alert_type=alert_data["alert_type"],
                severity=alert_data["severity"],
                title=alert_data["title"],
                description=alert_data["description"],
                risk_score=alert_data["risk_score"],
                previous_score=alert_data.get("previous_score"),
                confidence_score=alert_data["confidence_score"],
                change_percentage=alert_data.get("change_percentage", 0),
                status="new",
                evidence=json.dumps(alert_data["evidence"])
            )
            
            self.db.add(alert)
            self.db.commit()
            
            logger.info(f"Created {alert_data['alert_type']} alert for {country_code}")
            return alert
            
        except Exception as e:
            logger.error(f"Error creating alert record: {e}")
            self.db.rollback()
            return None
