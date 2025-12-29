"""
Phase 2: Confidence Scoring Module
Calculates confidence levels for risk assessments based on data quality metrics.
"""

from datetime import datetime, timedelta
from typing import Dict, List
import statistics
from app.core.logging import setup_logger

logger = setup_logger(__name__)


class ConfidenceScorer:
    """
    Calculates confidence scores for risk assessments.
    
    Confidence factors:
    1. Data Source Count (30%): More diverse sources = higher confidence
    2. Data Freshness (25%): Recent data = higher confidence
    3. Signal Consistency (25%): Aligned signals = higher confidence
    4. Historical Validation (20%): Matches historical patterns = higher confidence
    """
    
    WEIGHTS = {
        "data_source_count": 0.30,
        "data_freshness": 0.25,
        "signal_consistency": 0.25,
        "historical_validation": 0.20
    }
    
    @staticmethod
    def calculate_confidence(
        news_signal: Dict,
        conflict_signal: Dict,
        economic_signal: Dict,
        government_signal: Dict,
        historical_scores: List[float] = None
    ) -> Dict:
        """
        Calculate overall confidence score (0-100).
        
        Args:
            news_signal: News signal calculation result
            conflict_signal: Conflict signal calculation result
            economic_signal: Economic signal calculation result
            government_signal: Government signal calculation result
            historical_scores: List of historical risk scores for validation
            
        Returns:
            Dict with confidence_score and component scores
        """
        try:
            # 1. Data Source Count Score (0-100)
            source_count_score = ConfidenceScorer._calculate_source_count_score(
                news_signal, conflict_signal, economic_signal, government_signal
            )
            
            # 2. Data Freshness Score (0-100)
            freshness_score = ConfidenceScorer._calculate_freshness_score(
                news_signal, conflict_signal, economic_signal, government_signal
            )
            
            # 3. Signal Consistency Score (0-100)
            consistency_score = ConfidenceScorer._calculate_consistency_score(
                news_signal, conflict_signal, economic_signal, government_signal
            )
            
            # 4. Historical Validation Score (0-100)
            historical_score = ConfidenceScorer._calculate_historical_validation(
                historical_scores or []
            )
            
            # Weighted combination
            confidence_score = (
                source_count_score * ConfidenceScorer.WEIGHTS["data_source_count"] +
                freshness_score * ConfidenceScorer.WEIGHTS["data_freshness"] +
                consistency_score * ConfidenceScorer.WEIGHTS["signal_consistency"] +
                historical_score * ConfidenceScorer.WEIGHTS["historical_validation"]
            )
            
            return {
                "confidence_score": round(confidence_score, 2),
                "components": {
                    "source_count": round(source_count_score, 2),
                    "freshness": round(freshness_score, 2),
                    "consistency": round(consistency_score, 2),
                    "historical_validation": round(historical_score, 2)
                },
                "confidence_level": ConfidenceScorer._get_confidence_level(confidence_score)
            }
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return {
                "confidence_score": 50.0,
                "components": {},
                "confidence_level": "medium",
                "error": str(e)
            }
    
    @staticmethod
    def _calculate_source_count_score(
        news_signal: Dict,
        conflict_signal: Dict,
        economic_signal: Dict,
        government_signal: Dict
    ) -> float:
        """
        Score based on number of active data sources.
        More sources with substantial data = higher confidence.
        """
        active_sources = 0
        data_volume_score = 0
        
        # News signal
        if news_signal.get("article_count", 0) > 5:
            active_sources += 1
            data_volume_score += min(news_signal.get("article_count", 0) / 50.0 * 25, 25)
        
        # Conflict signal
        if conflict_signal.get("event_count", 0) > 3:
            active_sources += 1
            data_volume_score += min(conflict_signal.get("event_count", 0) / 30.0 * 25, 25)
        
        # Economic signal
        if economic_signal.get("score", 0) > 0:
            active_sources += 1
            data_volume_score += 25
        
        # Government signal
        if government_signal.get("reports_analyzed", 0) > 3:
            active_sources += 1
            data_volume_score += min(government_signal.get("reports_analyzed", 0) / 20.0 * 25, 25)
        
        # Base score on number of sources (4 sources max)
        source_score = (active_sources / 4.0) * 50
        
        # Add data volume bonus
        volume_score = min(data_volume_score, 50)
        
        return min(source_score + volume_score, 100)
    
    @staticmethod
    def _calculate_freshness_score(
        news_signal: Dict,
        conflict_signal: Dict,
        economic_signal: Dict,
        government_signal: Dict
    ) -> float:
        """
        Score based on data recency.
        Recent data within analysis periods = high score.
        """
        freshness_score = 0
        
        # News (7 days analysis - if we have recent articles, high freshness)
        news_days = news_signal.get("days_analyzed", 7)
        if news_signal.get("article_count", 0) > 0:
            freshness_score += 30  # Recent news available
        elif news_days <= 7:
            freshness_score += 15  # Data checked recently but none found
        
        # Conflict (30 days analysis)
        conflict_days = conflict_signal.get("days_analyzed", 30)
        if conflict_signal.get("event_count", 0) > 0:
            freshness_score += 30  # Recent conflicts recorded
        elif conflict_days <= 30:
            freshness_score += 15  # Data checked but none found (actually good news)
        
        # Economic (usually annual data, less critical for freshness)
        if economic_signal.get("score", 0) > 0:
            freshness_score += 20  # Economic data available
        
        # Government (30 days analysis)
        gov_days = government_signal.get("days_analyzed", 30)
        if government_signal.get("reports_analyzed", 0) > 0:
            freshness_score += 20  # Recent government reports
        elif gov_days <= 30:
            freshness_score += 10
        
        return min(freshness_score, 100)
    
    @staticmethod
    def _calculate_consistency_score(
        news_signal: Dict,
        conflict_signal: Dict,
        economic_signal: Dict,
        government_signal: Dict
    ) -> float:
        """
        Score based on alignment between different signals.
        Similar risk levels across signals = high consistency.
        """
        scores = []
        
        if news_signal.get("score", 0) > 0:
            scores.append(news_signal["score"])
        if conflict_signal.get("score", 0) > 0:
            scores.append(conflict_signal["score"])
        if economic_signal.get("score", 0) > 0:
            scores.append(economic_signal["score"])
        if government_signal.get("score", 0) > 0:
            scores.append(government_signal["score"])
        
        if len(scores) < 2:
            # Not enough data to assess consistency
            return 50.0
        
        # Calculate standard deviation
        mean_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
        
        # Low std deviation = high consistency
        # Normalize: 0 std dev = 100, 30+ std dev = 0
        consistency_score = max(0, 100 - (std_dev / 30.0 * 100))
        
        return min(consistency_score, 100)
    
    @staticmethod
    def _calculate_historical_validation(historical_scores: List[float]) -> float:
        """
        Score based on historical pattern matching.
        Stable risk patterns = higher confidence.
        Volatile patterns = lower confidence (unexpected changes).
        """
        if len(historical_scores) < 3:
            # Not enough history
            return 50.0
        
        # Calculate volatility (standard deviation)
        mean_score = statistics.mean(historical_scores)
        std_dev = statistics.stdev(historical_scores)
        
        # Lower volatility = higher confidence
        # Normalize: 0-10 std dev = 100-70, 10-30 = 70-30, 30+ = 30-0
        if std_dev <= 10:
            validation_score = 100 - (std_dev * 3)
        elif std_dev <= 30:
            validation_score = 70 - ((std_dev - 10) * 2)
        else:
            validation_score = max(0, 30 - (std_dev - 30))
        
        return max(0, min(validation_score, 100))
    
    @staticmethod
    def _get_confidence_level(score: float) -> str:
        """Convert numeric confidence to level"""
        if score >= 80:
            return "very_high"
        elif score >= 65:
            return "high"
        elif score >= 50:
            return "medium"
        elif score >= 35:
            return "low"
        else:
            return "very_low"
