from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from app.core.logging import setup_logger
from app.core.database import SessionLocal, get_mongo_db
from app.models.sql_models import RiskScore, ConflictEvent, EconomicIndicator, Alert
from app.models.mongo_models import COLLECTIONS
from app.scoring.confidence import ConfidenceScorer
from app.scoring.alerts import AdvancedAlertDetector

logger = setup_logger(__name__)


class RiskScoringEngine:
    """
    Deterministic risk scoring engine.
    Combines signals from news, conflict events, and economic indicators.
    """
    
    # Weight configuration for different signals
    WEIGHTS = {
        "news_signal": 0.20,
        "conflict_signal": 0.40,
        "economic_signal": 0.30,
        "government_signal": 0.10
    }
    
    # Thresholds for alerts
    ALERT_THRESHOLDS = {
        "critical": 75.0,
        "high": 60.0,
        "medium": 40.0,
        "low": 20.0
    }
    
    # Phase 2: Advanced alert thresholds
    ALERT_CHANGE_THRESHOLDS = {
        "risk_increase": 15.0,      # >15% increase triggers alert
        "sudden_spike": 30.0,       # >30% increase in 24h
        "sustained_high": 70.0,     # Score >70 for 48h
        "rapid_escalation": 50.0    # >50% increase in 6h
    }
    
    # Confidence scoring weights
    CONFIDENCE_WEIGHTS = {
        "data_source_count": 0.30,
        "data_freshness": 0.25,
        "signal_consistency": 0.25,
        "historical_validation": 0.20
    }
    
    def __init__(self):
        self.db = SessionLocal()
        self.mongo_db = get_mongo_db()
    
    def calculate_news_signal(self, country_code: str, days: int = 7, use_ml: bool = True) -> Dict:
        """
        Calculate news-based risk signal.
        Phase 2: Uses ML sentiment analysis if available, falls back to keywords.
        
        Args:
            country_code: Country to analyze
            days: Number of days to look back
            use_ml: Whether to use ML sentiment analysis (Phase 2)
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent articles - try with date filter first
            articles = list(self.mongo_db[COLLECTIONS["news_articles"]].find({
                "countries": country_code,
                "published_date": {"$gte": cutoff_date}
            }))
            
            article_count = len(articles)
            
            # If no articles with recent date, try without date filter (use all articles for that country)
            if article_count == 0:
                logger.warning(f"No articles found with recent published_date for {country_code}, trying without date filter")
                articles = list(self.mongo_db[COLLECTIONS["news_articles"]].find({
                    "countries": country_code
                }).limit(50))  # Limit to last 50 articles
                article_count = len(articles)
            
            if article_count == 0:
                logger.info(f"No news articles found for {country_code}")
                return {
                    "score": 0.0,
                    "article_count": 0,
                    "method": "none",
                    "days_analyzed": days
                }
            
            # Try ML sentiment analysis (Phase 2)
            if use_ml:
                try:
                    from app.ml.sentiment import get_sentiment_analyzer
                    
                    analyzer = get_sentiment_analyzer()
                    logger.info(f"Using ML sentiment analysis for {article_count} articles")
                    
                    # Analyze sentiment for each article
                    sentiments = []
                    for article in articles:
                        sentiment = analyzer.analyze_article(article)
                        sentiments.append(sentiment)
                    
                    # Calculate aggregate sentiment
                    aggregate = analyzer.calculate_aggregate_sentiment(sentiments)
                    
                    # Convert to risk score
                    # More negative sentiment = higher risk
                    # Mean score ranges from -1 (very negative) to +1 (very positive)
                    mean_sentiment = aggregate["mean_score"]
                    negative_ratio = aggregate["negative_ratio"]
                    
                    # Base score on volume (0-40)
                    volume_score = min(article_count / 20.0 * 40, 40)
                    
                    # Sentiment-based score (0-60)
                    # Negative sentiment increases risk
                    sentiment_score = (1.0 - mean_sentiment) / 2.0 * 60  # Maps -1 to 60, +1 to 0
                    
                    total_score = volume_score + sentiment_score
                    clamped_score = max(0.0, min(total_score, 100.0))
                    
                    logger.info(f"ML sentiment: score={clamped_score:.2f}, mean_sentiment={mean_sentiment:.4f}, volume={volume_score:.1f}")
                    
                    return {
                        "score": round(clamped_score, 2),
                        "article_count": article_count,
                        "method": "ml_sentiment",
                        "mean_sentiment": round(mean_sentiment, 4),
                        "negative_ratio": round(negative_ratio, 4),
                        "positive_ratio": round(aggregate["positive_ratio"], 4),
                        "days_analyzed": days
                    }
                    
                except Exception as ml_error:
                    logger.warning(f"ML sentiment analysis failed: {ml_error}, falling back to keywords")
                    # Fall through to keyword-based method
            
            # Fallback: Keyword-based analysis (Phase 1)
            logger.info(f"Using keyword-based sentiment analysis for {article_count} articles")
            
            negative_keywords = [
                "protest", "riot", "violence", "conflict", "crisis",
                "terrorism", "attack", "strike", "unrest", "tension",
                "war", "emergency", "threat", "sanction"
            ]
            
            negative_count = 0
            for article in articles:
                text = f"{article.get('title', '')} {article.get('content', '')}".lower()
                if any(keyword in text for keyword in negative_keywords):
                    negative_count += 1
            
            # Score calculation
            volume_score = min(article_count / 20.0 * 50, 50)
            
            if article_count > 0:
                negative_ratio = negative_count / article_count
                negative_score = negative_ratio * 50
            else:
                negative_score = 0
            
            total_score = volume_score + negative_score
            clamped_score = max(0.0, min(total_score, 100.0))
            
            logger.info(f"Keyword sentiment: score={clamped_score:.2f}, articles={article_count}, negative={negative_count}, volume={volume_score:.1f}")
            
            return {
                "score": round(clamped_score, 2),
                "article_count": article_count,
                "negative_count": negative_count,
                "method": "keyword",
                "days_analyzed": days
            }
            
        except Exception as e:
            logger.error(f"Error calculating news signal: {e}")
            return {"score": 0, "error": str(e), "method": "error"}
    
    def calculate_conflict_signal(self, country_code: str, days: int = 30) -> Dict:
        """
        Calculate conflict-based risk signal.
        Based on event frequency, type severity, and fatalities.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent conflict events
            events = self.db.query(ConflictEvent).filter(
                ConflictEvent.country_code == country_code,
                ConflictEvent.event_date >= cutoff_date
            ).all()
            
            event_count = len(events)
            
            if event_count == 0:
                return {
                    "score": 0,
                    "event_count": 0,
                    "total_fatalities": 0,
                    "days_analyzed": days
                }
            
            # Event type severity weights (adjusted based on real data)
            event_severity = {
                "Battles": 10,
                "Violence against civilians": 10,
                "Explosions/Remote violence": 9,
                "Riots": 7,
                "Protests": 4,
                "Strategic developments": 3  # Increased from 2 - these still indicate risk
            }
            
            # Phase 2: Calculate escalation rate (comparing first half vs second half of period)
            midpoint = cutoff_date + timedelta(days=days/2)
            first_half = [e for e in events if e.event_date < midpoint]
            second_half = [e for e in events if e.event_date >= midpoint]
            
            escalation_rate = 0
            if len(first_half) > 0:
                escalation_rate = (len(second_half) - len(first_half)) / len(first_half) * 100
            
            total_fatalities = 0
            severity_sum = 0
            high_casualty_events = 0
            
            for event in events:
                fatalities = event.fatalities or 0
                total_fatalities += fatalities
                
                event_type = event.event_type or ""
                base_severity = event_severity.get(event_type, 5)
                
                # Phase 2: Casualty impact multiplier
                if fatalities > 50:
                    severity_multiplier = 1.5  # Mass casualty event
                    high_casualty_events += 1
                elif fatalities > 10:
                    severity_multiplier = 1.3  # High casualty
                elif fatalities > 0:
                    severity_multiplier = 1.1  # Any casualties
                else:
                    severity_multiplier = 1.0
                
                severity_sum += base_severity * severity_multiplier
            
            # Score calculation (Phase 2 enhanced)
            # Event frequency (normalized to 0-40, more sensitive to high counts)
            frequency_score = min(event_count / 15.0 * 40, 40)
            
            # Event severity (normalized to 0-35, adjusted for multipliers)
            avg_severity = severity_sum / event_count if event_count > 0 else 0
            severity_score = (avg_severity / 15.0) * 35  # Adjusted denominator for multipliers
            
            # Fatality impact (normalized to 0-20, slightly reduced for escalation bonus)
            fatality_score = min(total_fatalities / 50.0 * 20, 20)
            
            # Phase 2: Escalation bonus (0-5 points for rapid escalation)
            escalation_bonus = min(max(escalation_rate / 100.0 * 5, 0), 5)
            
            total_score = frequency_score + severity_score + fatality_score + escalation_bonus
            
            # Explicit clamping to ensure 0-100 range
            clamped_score = max(0.0, min(total_score, 100.0))
            
            return {
                "score": clamped_score,
                "event_count": event_count,
                "total_fatalities": total_fatalities,
                "high_casualty_events": high_casualty_events,
                "avg_severity": round(avg_severity, 2),
                "escalation_rate": round(escalation_rate, 2),
                "days_analyzed": days
            }
            
        except Exception as e:
            logger.error(f"Error calculating conflict signal: {e}")
            return {"score": 0, "error": str(e)}
    
    def calculate_economic_signal(self, country_code: str) -> Dict:
        """
        Calculate economic stress signal.
        Based on GDP growth, inflation, and unemployment trends.
        """
        try:
            # Get most recent economic indicators
            current_year = datetime.utcnow().year
            past_2_years = [datetime(current_year - i, 1, 1) for i in range(2)]
            
            indicators = {}
            for date in past_2_years:
                year_indicators = self.db.query(EconomicIndicator).filter(
                    EconomicIndicator.country_code == country_code,
                    EconomicIndicator.date == date
                ).all()
                
                for ind in year_indicators:
                    if ind.indicator_code not in indicators:
                        indicators[ind.indicator_code] = []
                    indicators[ind.indicator_code].append(ind.value)
            
            # Calculate stress scores for each indicator
            gdp_score = self._score_gdp_growth(indicators.get("GDP_GROWTH", []))
            inflation_score = self._score_inflation(indicators.get("INFLATION", []))
            unemployment_score = self._score_unemployment(indicators.get("UNEMPLOYMENT", []))
            
            # Weighted average
            total_score = (gdp_score * 0.4 + inflation_score * 0.4 + unemployment_score * 0.2)
            
            # Explicit clamping to ensure 0-100 range
            clamped_score = max(0.0, min(total_score, 100.0))
            
            return {
                "score": clamped_score,
                "gdp_score": round(gdp_score, 2),
                "inflation_score": round(inflation_score, 2),
                "unemployment_score": round(unemployment_score, 2),
                "indicators_available": list(indicators.keys())
            }
            
        except Exception as e:
            logger.error(f"Error calculating economic signal: {e}")
            return {"score": 0, "error": str(e)}
    
    def _score_gdp_growth(self, values: List[float]) -> float:
        """Score GDP growth (lower growth = higher risk)"""
        if not values:
            return 50  # Neutral if no data
        
        latest = values[0]
        
        # Adjusted thresholds for more realistic risk assessment
        if latest < 0:
            return 90  # Recession is very high risk
        elif latest < 2:
            return 65  # Very low growth
        elif latest < 4:
            return 45  # Below potential
        elif latest < 6:
            return 25  # Moderate growth
        elif latest < 8:
            return 15  # Strong growth
        else:
            return 5   # Exceptional growth
    
    def _score_inflation(self, values: List[float]) -> float:
        """Score inflation (higher inflation = higher risk)"""
        if not values:
            return 50
        
        latest = values[0]
        
        # Adjusted thresholds for more sensitive inflation risk
        if latest > 10:
            return 85   # High inflation
        elif latest > 7:
            return 65   # Elevated inflation
        elif latest > 5:
            return 45   # Above target
        elif latest > 3:
            return 25   # Moderate
        elif latest > 2:
            return 15   # Stable
        else:
            return 5    # Very low (deflation risk minimal)
    
    def _score_unemployment(self, values: List[float]) -> float:
        """Score unemployment (higher unemployment = higher risk)"""
        if not values:
            return 50
        
        latest = values[0]
        
        # Adjusted thresholds for better sensitivity
        if latest > 15:
            return 90   # Crisis level
        elif latest > 12:
            return 75   # Very high
        elif latest > 9:
            return 60   # High
        elif latest > 7:
            return 45   # Elevated
        elif latest > 5:
            return 30   # Moderate
        elif latest > 3:
            return 15   # Low
        else:
            return 5    # Very low
    
    def calculate_government_signal(self, country_code: str, days: int = 30, use_ml: bool = True) -> Dict:
        """
        Calculate government action signal.
        Phase 2.2: Uses scraped government data with sentiment analysis.
        
        Args:
            country_code: Country to analyze
            days: Number of days to look back
            use_ml: Whether to use ML sentiment analysis
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent government reports for this country
            # Note: Government data is currently only available for India (PIB, MEA, PMO)
            # For India, also include documents without country_code (legacy data)
            if country_code == "IND":
                query = {
                    "$or": [
                        {"country_code": country_code},
                        {"country": country_code},
                        {"country_code": {"$exists": False}}  # Legacy documents without country field
                    ],
                    "report_date": {"$gte": cutoff_date},
                    "scraped_at": {"$exists": True}
                }
            else:
                query = {
                    "$or": [
                        {"country_code": country_code},
                        {"country": country_code}
                    ],
                    "report_date": {"$gte": cutoff_date},
                    "scraped_at": {"$exists": True}
                }
            
            reports = list(self.mongo_db[COLLECTIONS["government_reports"]].find(query))
            
            report_count = len(reports)
            
            if report_count == 0:
                logger.info(f"No government reports found for {country_code} (data currently India-only)")
                return {
                    "score": 0,
                    "reports_analyzed": 0,
                    "days_analyzed": days,
                    "note": "No government data available - signal inactive"
                }
            
            # Analyze government reports with ML sentiment
            if use_ml:
                try:
                    from app.ml.sentiment import get_sentiment_analyzer
                    
                    analyzer = get_sentiment_analyzer()
                    
                    # Analyze sentiment for each report
                    sentiments = []
                    for report in reports:
                        text = f"{report.get('title', '')}. {report.get('content', '')}"
                        sentiment = analyzer.analyze(text)
                        sentiments.append(sentiment)
                    
                    # Calculate aggregate sentiment
                    aggregate = analyzer.calculate_aggregate_sentiment(sentiments)
                    mean_sentiment = aggregate["mean_score"]
                    negative_ratio = aggregate["negative_ratio"]
                    
                    # Category distribution
                    categories = {}
                    for report in reports:
                        cat = report.get("category", "general")
                        categories[cat] = categories.get(cat, 0) + 1
                    
                    # Scoring logic
                    # 1. Policy stability (40%): More reports = potential instability
                    #    Optimal: 5-15 reports/month, too many or too few indicates issues
                    if report_count < 5:
                        stability_score = 30  # Too quiet, lack of transparency
                    elif report_count > 30:
                        stability_score = 60  # High activity, potential instability
                    else:
                        stability_score = 20  # Normal activity
                    
                    # 2. Official sentiment (30%): Negative sentiment indicates issues
                    sentiment_score = (1.0 - mean_sentiment) / 2.0 * 30  # Maps -1 to 30, +1 to 0
                    
                    # 3. Security concerns (30%): Security-related reports increase risk
                    security_count = categories.get("security", 0)
                    security_ratio = security_count / report_count if report_count > 0 else 0
                    security_score = security_ratio * 30
                    
                    total_score = stability_score + sentiment_score + security_score
                    clamped_score = max(0.0, min(total_score, 100.0))
                    
                    return {
                        "score": round(clamped_score, 2),
                        "reports_analyzed": report_count,
                        "method": "ml_sentiment",
                        "mean_sentiment": round(mean_sentiment, 4),
                        "negative_ratio": round(negative_ratio, 4),
                        "categories": categories,
                        "stability_score": round(stability_score, 2),
                        "sentiment_score": round(sentiment_score, 2),
                        "security_score": round(security_score, 2),
                        "days_analyzed": days
                    }
                    
                except Exception as ml_error:
                    logger.warning(f"ML analysis of government data failed: {ml_error}, using basic scoring")
                    # Fall through to basic analysis
            
            # Fallback: Basic keyword analysis
            security_keywords = ['defence', 'military', 'security', 'border', 'terrorism', 'threat']
            negative_keywords = ['concern', 'issue', 'problem', 'challenge', 'crisis', 'tension']
            
            security_count = 0
            negative_count = 0
            
            for report in reports:
                text = f"{report.get('title', '')} {report.get('content', '')}".lower()
                
                if any(kw in text for kw in security_keywords):
                    security_count += 1
                if any(kw in text for kw in negative_keywords):
                    negative_count += 1
            
            # Basic scoring
            activity_score = min(report_count / 20.0 * 40, 40)
            security_score = (security_count / report_count * 30) if report_count > 0 else 0
            negative_score = (negative_count / report_count * 30) if report_count > 0 else 0
            
            total_score = activity_score + security_score + negative_score
            clamped_score = max(0.0, min(total_score, 100.0))
            
            return {
                "score": round(clamped_score, 2),
                "reports_analyzed": report_count,
                "method": "keyword",
                "security_mentions": security_count,
                "negative_mentions": negative_count,
                "days_analyzed": days
            }
            
        except Exception as e:
            logger.error(f"Error calculating government signal: {e}")
            return {
                "score": 0,
                "reports_analyzed": 0,
                "days_analyzed": days,
                "error": str(e),
                "note": "Government signal analysis failed"
            }
    
    def calculate_overall_risk(self, country_code: str) -> Dict:
        """
        Calculate overall risk score by combining all signals.
        Returns comprehensive risk assessment.
        """
        logger.info(f"Calculating risk score for {country_code}...")
        
        try:
            # Calculate individual signals
            news_signal = self.calculate_news_signal(country_code, days=7)
            conflict_signal = self.calculate_conflict_signal(country_code, days=30)
            economic_signal = self.calculate_economic_signal(country_code)
            government_signal = self.calculate_government_signal(country_code, days=30)
            
            # Weighted combination
            overall_score = (
                news_signal["score"] * self.WEIGHTS["news_signal"] +
                conflict_signal["score"] * self.WEIGHTS["conflict_signal"] +
                economic_signal["score"] * self.WEIGHTS["economic_signal"] +
                government_signal["score"] * self.WEIGHTS["government_signal"]
            )
            
            # Determine trend (simplified for Phase 1)
            trend = self._determine_trend(country_code, overall_score)
            
            # Phase 2: Calculate confidence score
            historical_scores = self._get_historical_scores(country_code, days=30)
            confidence_result = ConfidenceScorer.calculate_confidence(
                news_signal,
                conflict_signal,
                economic_signal,
                government_signal,
                historical_scores
            )
            confidence_score = confidence_result["confidence_score"]
            
            # Store risk score with confidence
            risk_score = RiskScore(
                country_code=country_code,
                date=datetime.utcnow(),
                overall_score=round(overall_score, 2),
                news_signal_score=round(news_signal["score"], 2),
                conflict_signal_score=round(conflict_signal["score"], 2),
                economic_signal_score=round(economic_signal["score"], 2),
                government_signal_score=round(government_signal["score"], 2),
                confidence_score=round(confidence_score, 2),  # Phase 2
                trend=trend,
                calculation_metadata=json.dumps({
                    "news": news_signal,
                    "conflict": conflict_signal,
                    "economic": economic_signal,
                    "government": government_signal,
                    "weights": self.WEIGHTS,
                    "confidence": confidence_result  # Phase 2
                })
            )
            
            self.db.add(risk_score)
            self.db.commit()
            
            # Phase 2: Advanced alert detection
            signal_dict = {
                "news": news_signal,
                "conflict": conflict_signal,
                "economic": economic_signal,
                "government": government_signal
            }
            
            alert_detector = AdvancedAlertDetector(self.db)
            alerts = alert_detector.detect_all_alerts(
                country_code,
                overall_score,
                confidence_score,
                signal_dict,
                risk_score.id
            )
            
            logger.info(f"Risk score calculated: {overall_score:.2f} for {country_code}, confidence: {confidence_score:.1f}%, alerts: {len(alerts)}")
            
            return {
                "country_code": country_code,
                "overall_score": round(overall_score, 2),
                "confidence_score": round(confidence_score, 2),  # Phase 2
                "confidence_level": confidence_result["confidence_level"],  # Phase 2
                "risk_level": self._get_risk_level(overall_score),
                "trend": trend,
                "signals": {
                    "news": news_signal,
                    "conflict": conflict_signal,
                    "economic": economic_signal,
                    "government": government_signal
                },
                "weights": self.WEIGHTS,
                "alerts_triggered": len(alerts),  # Phase 2
                "calculated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating overall risk: {e}")
            self.db.rollback()
            raise
    
    def _determine_trend(self, country_code: str, current_score: float) -> str:
        """Determine risk trend by comparing with previous scores"""
        try:
            # Get previous score (from last 7 days)
            cutoff = datetime.utcnow() - timedelta(days=7)
            previous = self.db.query(RiskScore).filter(
                RiskScore.country_code == country_code,
                RiskScore.date < datetime.utcnow(),
                RiskScore.date >= cutoff
            ).order_by(RiskScore.date.desc()).first()
            
            if not previous:
                return "stable"
            
            diff = current_score - previous.overall_score
            
            if diff > 10:
                return "increasing"
            elif diff < -10:
                return "decreasing"
            else:
                return "stable"
                
        except Exception:
            return "stable"
    
    def _get_historical_scores(self, country_code: str, days: int = 30) -> List[float]:
        """
        Get list of historical risk scores for confidence calculation.
        Phase 2 addition.
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            scores = self.db.query(RiskScore).filter(
                RiskScore.country_code == country_code,
                RiskScore.date >= cutoff
            ).order_by(RiskScore.date).all()
            
            return [score.overall_score for score in scores]
            
        except Exception as e:
            logger.error(f"Error getting historical scores: {e}")
            return []
    
    def _get_risk_level(self, score: float) -> str:
        """Convert numeric score to risk level"""
        if score >= self.ALERT_THRESHOLDS["critical"]:
            return "critical"
        elif score >= self.ALERT_THRESHOLDS["high"]:
            return "high"
        elif score >= self.ALERT_THRESHOLDS["medium"]:
            return "medium"
        elif score >= self.ALERT_THRESHOLDS["low"]:
            return "low"
        else:
            return "minimal"
    
    def _check_and_create_alerts(self, country_code: str, score: float, risk_score_id: int):
        """Check if score crosses thresholds and create alerts"""
        try:
            # Check for threshold breach
            risk_level = self._get_risk_level(score)
            
            if risk_level in ["high", "critical"]:
                # Check if similar alert was recently created
                recent_cutoff = datetime.utcnow() - timedelta(days=1)
                recent_alert = self.db.query(Alert).filter(
                    Alert.country_code == country_code,
                    Alert.triggered_at >= recent_cutoff,
                    Alert.severity == risk_level
                ).first()
                
                if not recent_alert:
                    alert = Alert(
                        country_code=country_code,
                        alert_type="threshold_breach",
                        severity=risk_level,
                        title=f"{risk_level.upper()} risk level detected for {country_code}",
                        description=f"Geopolitical risk score has reached {score:.2f}, crossing {risk_level} threshold",
                        risk_score=score,
                        status="new",
                        evidence=json.dumps({"risk_score_id": risk_score_id})
                    )
                    
                    self.db.add(alert)
                    self.db.commit()
                    logger.info(f"Created {risk_level} alert for {country_code}")
        
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    def __del__(self):
        """Cleanup database connection"""
        try:
            self.db.close()
        except:
            pass


if __name__ == "__main__":
    # Test scoring
    engine = RiskScoringEngine()
    result = engine.calculate_overall_risk("IND")
    print(json.dumps(result, indent=2, default=str))
