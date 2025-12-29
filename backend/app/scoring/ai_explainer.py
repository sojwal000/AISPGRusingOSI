"""
Phase 2: AI Explanation Layer
Generates natural language explanations for risk scores and alerts using Gemini AI.
"""

import os
from typing import Dict, List, Optional
from datetime import datetime
import json
from app.core.logging import setup_logger

logger = setup_logger(__name__)

# Check if google-generativeai is available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. AI explanations will be disabled.")


class AIExplanationGenerator:
    """
    Generates natural language explanations for risk assessments and alerts.
    Uses Google Gemini AI for analysis and explanation generation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini AI client.
        
        Args:
            api_key: Gemini API key (or use GEMINI_API_KEY environment variable)
        """
        self.enabled = False
        
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini AI not available. Install with: pip install google-generativeai")
            return
        
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("Gemini API key not provided. AI explanations disabled. Set GEMINI_API_KEY environment variable.")
            return
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')  # Latest stable model
            self.enabled = True
            logger.info("Gemini AI explanation generator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI: {e}")
            self.enabled = False
    
    def generate_risk_explanation(
        self,
        country_code: str,
        risk_score: float,
        confidence_score: float,
        signals: Dict,
        trend: str
    ) -> str:
        """
        Generate natural language explanation for overall risk score.
        
        Args:
            country_code: Country being analyzed
            risk_score: Overall risk score (0-100)
            confidence_score: Confidence in assessment (0-100)
            signals: Dict of individual signal scores
            trend: Risk trend (increasing/decreasing/stable)
            
        Returns:
            Natural language explanation
        """
        if not self.enabled:
            return self._generate_fallback_explanation(country_code, risk_score, signals, trend)
        
        try:
            prompt = self._build_risk_explanation_prompt(
                country_code, risk_score, confidence_score, signals, trend
            )
            
            response = self.model.generate_content(prompt)
            explanation = response.text.strip()
            
            logger.info(f"Generated AI explanation for {country_code}")
            return explanation
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._generate_fallback_explanation(country_code, risk_score, signals, trend)
    
    def generate_alert_explanation(
        self,
        country_code: str,
        alert_type: str,
        risk_score: float,
        previous_score: float,
        change_percent: float,
        signals: Dict,
        confidence_score: float
    ) -> str:
        """
        Generate natural language explanation for an alert.
        
        Args:
            country_code: Country
            alert_type: Type of alert
            risk_score: Current risk score
            previous_score: Previous risk score
            change_percent: Percentage change
            signals: Signal components
            confidence_score: Confidence level
            
        Returns:
            Natural language explanation
        """
        if not self.enabled:
            return self._generate_fallback_alert_explanation(
                country_code, alert_type, risk_score, previous_score, change_percent
            )
        
        try:
            prompt = self._build_alert_explanation_prompt(
                country_code, alert_type, risk_score, previous_score,
                change_percent, signals, confidence_score
            )
            
            response = self.model.generate_content(prompt)
            explanation = response.text.strip()
            
            logger.info(f"Generated AI alert explanation for {country_code}")
            return explanation
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._generate_fallback_alert_explanation(
                country_code, alert_type, risk_score, previous_score, change_percent
            )
    
    def _build_risk_explanation_prompt(
        self,
        country_code: str,
        risk_score: float,
        confidence_score: float,
        signals: Dict,
        trend: str
    ) -> str:
        """Build prompt for risk explanation"""
        
        news_score = signals.get("news", {}).get("score", 0)
        conflict_score = signals.get("conflict", {}).get("score", 0)
        economic_score = signals.get("economic", {}).get("score", 0)
        gov_score = signals.get("government", {}).get("score", 0)
        
        # Extract key details
        news_count = signals.get("news", {}).get("article_count", 0)
        conflict_count = signals.get("conflict", {}).get("event_count", 0)
        fatalities = signals.get("conflict", {}).get("total_fatalities", 0)
        escalation = signals.get("conflict", {}).get("escalation_rate", 0)
        
        prompt = f"""You are a geopolitical risk analyst. Provide a concise, professional analysis of the current risk situation for {country_code}.

**Risk Assessment:**
- Overall Risk Score: {risk_score:.1f}/100 ({self._risk_level_text(risk_score)})
- Confidence: {confidence_score:.1f}/100
- Trend: {trend}

**Signal Components:**
- News Signal: {news_score:.1f} ({news_count} articles analyzed)
- Conflict Signal: {conflict_score:.1f} ({conflict_count} events, {fatalities} fatalities, {escalation:.0f}% escalation rate)
- Economic Signal: {economic_score:.1f}
- Government Signal: {gov_score:.1f}

**Instructions:**
1. Provide a 2-3 sentence summary of the overall risk situation
2. Identify the primary risk driver(s)
3. Mention any notable trends or patterns
4. Keep the tone professional and analytical
5. Do not include speculation or predictions beyond the data

Generate the explanation:"""
        
        return prompt
    
    def _build_alert_explanation_prompt(
        self,
        country_code: str,
        alert_type: str,
        risk_score: float,
        previous_score: float,
        change_percent: float,
        signals: Dict,
        confidence_score: float
    ) -> str:
        """Build prompt for alert explanation"""
        
        alert_descriptions = {
            "risk_increase": f"significant risk increase of {change_percent:.1f}%",
            "sudden_spike": f"sudden spike of {change_percent:.1f}% in 24 hours",
            "sustained_high": f"sustained high risk above 70 for extended period",
            "rapid_escalation": f"rapid escalation of {change_percent:.1f}% in just 6 hours"
        }
        
        description = alert_descriptions.get(alert_type, "risk change")
        
        # Identify primary driver
        scores = {
            "news": signals.get("news", {}).get("score", 0),
            "conflict": signals.get("conflict", {}).get("score", 0),
            "economic": signals.get("economic", {}).get("score", 0),
            "government": signals.get("government", {}).get("score", 0)
        }
        primary_driver = max(scores, key=scores.get)
        driver_score = scores[primary_driver]
        
        prompt = f"""You are a geopolitical risk analyst. Explain this urgent alert for {country_code}.

**Alert Details:**
- Alert Type: {description}
- Current Risk: {risk_score:.1f}/100
- Previous Risk: {previous_score:.1f}/100
- Change: {change_percent:+.1f}%
- Confidence: {confidence_score:.1f}/100

**Primary Driver:**
- {primary_driver.capitalize()} signal: {driver_score:.1f}/100

**Additional Context:**
{json.dumps(signals, indent=2)}

**Instructions:**
1. Explain WHY this alert was triggered (2 sentences max)
2. Identify the immediate risk driver
3. Suggest what type of events/data caused this change
4. Keep it urgent but professional
5. No predictions, only explain what the data shows

Generate the alert explanation:"""
        
        return prompt
    
    def _risk_level_text(self, score: float) -> str:
        """Convert score to risk level text"""
        if score >= 75:
            return "CRITICAL RISK"
        elif score >= 60:
            return "HIGH RISK"
        elif score >= 40:
            return "MODERATE RISK"
        elif score >= 20:
            return "LOW RISK"
        else:
            return "MINIMAL RISK"
    
    def _generate_fallback_explanation(
        self,
        country_code: str,
        risk_score: float,
        signals: Dict,
        trend: str
    ) -> str:
        """Generate rule-based explanation when AI is unavailable"""
        
        # Identify primary driver
        scores = {
            "news": signals.get("news", {}).get("score", 0),
            "conflict": signals.get("conflict", {}).get("score", 0),
            "economic": signals.get("economic", {}).get("score", 0),
            "government": signals.get("government", {}).get("score", 0)
        }
        
        primary_driver = max(scores, key=scores.get)
        driver_score = scores[primary_driver]
        
        risk_level = self._risk_level_text(risk_score)
        trend_text = {
            "increasing": "Risk is increasing",
            "decreasing": "Risk is decreasing",
            "stable": "Risk remains stable"
        }.get(trend, "Risk trend unknown")
        
        explanation = f"{country_code} currently shows {risk_level.lower()} with an overall score of {risk_score:.1f}/100. "
        explanation += f"{trend_text}. "
        
        if driver_score > 60:
            explanation += f"The primary risk driver is {primary_driver} activity (score: {driver_score:.1f}), "
            explanation += "indicating heightened concerns in this area. "
        
        # Add specific details
        if primary_driver == "conflict":
            events = signals.get("conflict", {}).get("event_count", 0)
            fatalities = signals.get("conflict", {}).get("total_fatalities", 0)
            if events > 0:
                explanation += f"Analysis identifies {events} conflict events with {fatalities} reported fatalities. "
        
        elif primary_driver == "news":
            articles = signals.get("news", {}).get("article_count", 0)
            if articles > 0:
                explanation += f"Analysis of {articles} recent news articles indicates elevated risk signals. "
        
        return explanation.strip()
    
    def _generate_fallback_alert_explanation(
        self,
        country_code: str,
        alert_type: str,
        risk_score: float,
        previous_score: float,
        change_percent: float
    ) -> str:
        """Generate rule-based alert explanation when AI is unavailable"""
        
        alert_messages = {
            "risk_increase": f"Alert triggered due to {change_percent:.1f}% risk increase from {previous_score:.1f} to {risk_score:.1f}.",
            "sudden_spike": f"URGENT: Risk spiked {change_percent:.1f}% within 24 hours (from {previous_score:.1f} to {risk_score:.1f}), indicating rapid deterioration.",
            "sustained_high": f"CRITICAL: Risk has remained above 70 for an extended period (current: {risk_score:.1f}), suggesting persistent instability.",
            "rapid_escalation": f"CRITICAL: Rapid escalation of {change_percent:.1f}% in just 6 hours (from {previous_score:.1f} to {risk_score:.1f}). Immediate attention recommended."
        }
        
        message = alert_messages.get(alert_type, f"Alert: Risk changed from {previous_score:.1f} to {risk_score:.1f}")
        message += f" This {country_code} alert requires review by analysts."
        
        return message


# Singleton instance
_ai_explainer: Optional[AIExplanationGenerator] = None


def get_ai_explainer() -> AIExplanationGenerator:
    """Get or create AI explanation generator singleton"""
    global _ai_explainer
    if _ai_explainer is None:
        _ai_explainer = AIExplanationGenerator()
    return _ai_explainer
