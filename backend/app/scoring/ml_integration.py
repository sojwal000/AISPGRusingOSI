"""
Advanced ML Integration for Risk Scoring Engine.
Provides topic modeling, forecasting, anomaly detection, and event clustering
for enhanced geopolitical risk assessment.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

# Setup logger
try:
    from app.core.logging import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class MLRiskEnhancer:
    """
    Enhances risk scoring with advanced ML capabilities.
    Integrates topic modeling, forecasting, anomaly detection, and event clustering.
    """
    
    def __init__(self, db_session=None, mongo_db=None):
        """
        Initialize ML risk enhancer.
        
        Args:
            db_session: SQLAlchemy session for PostgreSQL
            mongo_db: MongoDB database instance
        """
        self.db = db_session
        self.mongo_db = mongo_db
        
        # Lazy load ML components
        self._topic_modeler = None
        self._forecaster = None
        self._anomaly_detector = None
        self._geo_sentiment = None
        self._event_clusterer = None
        
        logger.info("MLRiskEnhancer initialized")
    
    def _get_topic_modeler(self):
        """Lazy load topic modeler."""
        if self._topic_modeler is None:
            try:
                from app.ml.topic_modeling import get_topic_modeler
                self._topic_modeler = get_topic_modeler()
            except Exception as e:
                logger.warning(f"Could not load topic modeler: {e}")
                self._topic_modeler = "not_available"
        return self._topic_modeler if self._topic_modeler != "not_available" else None
    
    def _get_forecaster(self):
        """Lazy load risk forecaster."""
        if self._forecaster is None:
            try:
                from app.ml.forecasting import get_risk_forecaster
                self._forecaster = get_risk_forecaster()
            except Exception as e:
                logger.warning(f"Could not load forecaster: {e}")
                self._forecaster = "not_available"
        return self._forecaster if self._forecaster != "not_available" else None
    
    def _get_anomaly_detector(self):
        """Lazy load anomaly detector."""
        if self._anomaly_detector is None:
            try:
                from app.ml.anomaly_detection import get_anomaly_detector
                self._anomaly_detector = get_anomaly_detector()
            except Exception as e:
                logger.warning(f"Could not load anomaly detector: {e}")
                self._anomaly_detector = "not_available"
        return self._anomaly_detector if self._anomaly_detector != "not_available" else None
    
    def _get_geo_sentiment(self):
        """Lazy load geopolitical sentiment analyzer."""
        if self._geo_sentiment is None:
            try:
                from app.ml.geopolitical_sentiment import get_geopolitical_analyzer
                self._geo_sentiment = get_geopolitical_analyzer()
            except Exception as e:
                logger.warning(f"Could not load geo sentiment: {e}")
                self._geo_sentiment = "not_available"
        return self._geo_sentiment if self._geo_sentiment != "not_available" else None
    
    def _get_event_clusterer(self):
        """Lazy load event clusterer."""
        if self._event_clusterer is None:
            try:
                from app.ml.event_clustering import get_event_clusterer
                self._event_clusterer = get_event_clusterer()
            except Exception as e:
                logger.warning(f"Could not load event clusterer: {e}")
                self._event_clusterer = "not_available"
        return self._event_clusterer if self._event_clusterer != "not_available" else None
    
    def analyze_news_topics(self, country_code: str, days: int = 14) -> Dict:
        """
        Analyze emerging topics in news articles.
        
        Args:
            country_code: Country to analyze
            days: Number of days to look back
        
        Returns:
            Topic analysis results
        """
        modeler = self._get_topic_modeler()
        if not modeler:
            return {"error": "Topic modeling not available", "topics": []}
        
        try:
            # Get articles from MongoDB
            from app.models.mongo_models import COLLECTIONS
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            articles = list(self.mongo_db[COLLECTIONS["news_articles"]].find({
                "countries": country_code,
                "published_date": {"$gte": cutoff_date}
            }))
            
            if len(articles) < 10:
                return {
                    "error": "Insufficient articles for topic modeling",
                    "article_count": len(articles),
                    "topics": []
                }
            
            # Extract texts
            documents = []
            for article in articles:
                text = f"{article.get('title', '')}. {article.get('content', '')}"
                if len(text.strip()) > 50:
                    documents.append(text)
            
            # Analyze topics
            result = modeler.analyze_documents(documents)
            
            # Add trending analysis
            trending = modeler.get_trending_topics(result)
            result["trending_topics"] = trending[:5]
            
            logger.info(f"Topic analysis complete for {country_code}: {result['num_topics']} topics found")
            return result
            
        except Exception as e:
            logger.error(f"Error in topic analysis: {e}")
            return {"error": str(e), "topics": []}
    
    def forecast_risk(self, country_code: str, periods: int = 14) -> Dict:
        """
        Forecast future risk scores.
        
        Args:
            country_code: Country to forecast
            periods: Number of days to forecast
        
        Returns:
            Forecast results with outlook
        """
        forecaster = self._get_forecaster()
        if not forecaster:
            return {"error": "Forecasting not available"}
        
        try:
            # Get historical risk scores
            from app.models.sql_models import RiskScore
            
            cutoff = datetime.utcnow() - timedelta(days=60)
            scores = self.db.query(RiskScore).filter(
                RiskScore.country_code == country_code,
                RiskScore.date >= cutoff
            ).order_by(RiskScore.date).all()
            
            if len(scores) < 14:
                return {
                    "error": "Insufficient historical data for forecasting",
                    "data_points": len(scores),
                    "required": 14
                }
            
            # Prepare data
            risk_data = [
                {"timestamp": s.date, "overall_score": s.overall_score}
                for s in scores
            ]
            
            # Generate forecast
            forecast = forecaster.forecast(risk_data, periods)
            
            # Add outlook
            outlook = forecaster.get_risk_outlook(forecast)
            forecast["outlook"] = outlook
            
            # Detect trend changes
            trend_change = forecaster.detect_trend_change(risk_data)
            forecast["trend_analysis"] = trend_change
            
            logger.info(f"Forecast complete for {country_code}: {outlook['outlook']} outlook")
            return forecast
            
        except Exception as e:
            logger.error(f"Error in risk forecasting: {e}")
            return {"error": str(e)}
    
    def detect_anomalies(self, country_code: str, days: int = 30) -> Dict:
        """
        Detect anomalies in risk signals.
        
        Args:
            country_code: Country to analyze
            days: Number of days to analyze
        
        Returns:
            Anomaly detection results with alerts
        """
        detector = self._get_anomaly_detector()
        if not detector:
            return {"error": "Anomaly detection not available", "anomalies": []}
        
        try:
            # Get historical risk scores with signals
            from app.models.sql_models import RiskScore
            import json
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            scores = self.db.query(RiskScore).filter(
                RiskScore.country_code == country_code,
                RiskScore.date >= cutoff
            ).order_by(RiskScore.date).all()
            
            if len(scores) < 10:
                return {
                    "error": "Insufficient data for anomaly detection",
                    "data_points": len(scores)
                }
            
            # Prepare data with signal components
            risk_data = []
            for s in scores:
                data_point = {
                    "timestamp": s.date,
                    "overall_score": s.overall_score,
                }
                
                # Parse metadata for signal scores
                if s.calculation_metadata:
                    try:
                        metadata = json.loads(s.calculation_metadata)
                        data_point["conflict_signal"] = metadata.get("conflict", {})
                        data_point["news_signal"] = metadata.get("news", {})
                        data_point["economic_signal"] = metadata.get("economic", {})
                    except:
                        pass
                
                risk_data.append(data_point)
            
            # Run multivariate anomaly detection
            analysis = detector.analyze_multivariate(risk_data)
            
            # Generate alerts from anomalies
            alerts = detector.generate_alerts(analysis, country_code)
            analysis["generated_alerts"] = alerts
            
            logger.info(f"Anomaly detection complete for {country_code}: {analysis['anomaly_count']} anomalies found")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return {"error": str(e), "anomalies": []}
    
    def analyze_geopolitical_sentiment(self, texts: List[str]) -> Dict:
        """
        Analyze texts using geopolitical-aware sentiment.
        
        Args:
            texts: List of texts to analyze
        
        Returns:
            Aggregate geopolitical sentiment analysis
        """
        analyzer = self._get_geo_sentiment()
        if not analyzer:
            return {"error": "Geopolitical sentiment not available"}
        
        try:
            analyses = []
            risk_scores = []
            all_risk_indicators = []
            
            for text in texts[:100]:  # Limit to 100 texts
                result = analyzer.analyze(text)
                analyses.append(result)
                risk_scores.append(analyzer.calculate_document_risk(result))
                
                # Collect risk indicators
                all_risk_indicators.extend(result.get('top_risk_indicators', []))
            
            # Aggregate
            import numpy as np
            
            # Count indicator frequencies
            indicator_counts = {}
            for ind in all_risk_indicators:
                word = ind['word']
                indicator_counts[word] = indicator_counts.get(word, 0) + 1
            
            top_indicators = sorted(
                indicator_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            # Risk level distribution
            risk_levels = {}
            for a in analyses:
                level = a.get('risk_level', 'unknown')
                risk_levels[level] = risk_levels.get(level, 0) + 1
            
            return {
                "documents_analyzed": len(analyses),
                "mean_risk_score": round(np.mean(risk_scores), 2),
                "max_risk_score": round(max(risk_scores), 2),
                "min_risk_score": round(min(risk_scores), 2),
                "risk_level_distribution": risk_levels,
                "top_risk_indicators": [{"word": w, "count": c} for w, c in top_indicators],
                "high_risk_count": sum(1 for s in risk_scores if s >= 60)
            }
            
        except Exception as e:
            logger.error(f"Error in geopolitical sentiment: {e}")
            return {"error": str(e)}
    
    def cluster_conflict_events(self, country_code: str, days: int = 30) -> Dict:
        """
        Cluster related conflict events.
        
        Args:
            country_code: Country to analyze
            days: Number of days to look back
        
        Returns:
            Event clustering results
        """
        clusterer = self._get_event_clusterer()
        if not clusterer:
            return {"error": "Event clustering not available", "clusters": []}
        
        try:
            # Get conflict events
            from app.models.sql_models import ConflictEvent
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            events = self.db.query(ConflictEvent).filter(
                ConflictEvent.country_code == country_code,
                ConflictEvent.event_date >= cutoff
            ).all()
            
            if len(events) < 5:
                return {
                    "error": "Insufficient events for clustering",
                    "event_count": len(events),
                    "clusters": []
                }
            
            # Convert to dict format
            event_dicts = []
            for e in events:
                event_dicts.append({
                    "title": e.notes or f"{e.event_type} event",
                    "description": e.notes,
                    "event_type": e.event_type,
                    "country": e.country_code,
                    "location": e.location,
                    "actor1": e.actor1,
                    "actor2": e.actor2,
                    "fatalities": e.fatalities,
                    "timestamp": e.event_date,
                    "severity": e.fatalities * 2 if e.fatalities else 1
                })
            
            # Cluster events
            clusters = clusterer.cluster_hierarchical(event_dicts)
            
            # Analyze clusters
            cluster_analyses = clusterer.analyze_clusters(event_dicts, clusters)
            
            # Detect event chains
            chains = clusterer.detect_event_chains(event_dicts)
            
            logger.info(f"Event clustering complete for {country_code}: {len(cluster_analyses)} significant clusters")
            
            return {
                "total_events": len(events),
                "cluster_count": len(cluster_analyses),
                "clusters": cluster_analyses[:10],  # Top 10 clusters
                "event_chains": chains[:5],  # Top 5 chains
                "escalating_chains": [c for c in chains if c.get('is_escalating')]
            }
            
        except Exception as e:
            logger.error(f"Error in event clustering: {e}")
            return {"error": str(e), "clusters": []}
    
    def get_comprehensive_ml_analysis(self, country_code: str) -> Dict:
        """
        Get comprehensive ML-enhanced analysis for a country.
        
        Args:
            country_code: Country to analyze
        
        Returns:
            Complete ML analysis including all components
        """
        logger.info(f"Running comprehensive ML analysis for {country_code}")
        
        results = {
            "country_code": country_code,
            "analyzed_at": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Topic Analysis
        try:
            topics = self.analyze_news_topics(country_code)
            results["components"]["topic_modeling"] = {
                "status": "error" if "error" in topics else "success",
                "data": topics
            }
        except Exception as e:
            results["components"]["topic_modeling"] = {"status": "error", "error": str(e)}
        
        # Risk Forecast
        try:
            forecast = self.forecast_risk(country_code)
            results["components"]["risk_forecast"] = {
                "status": "error" if "error" in forecast else "success",
                "data": forecast
            }
        except Exception as e:
            results["components"]["risk_forecast"] = {"status": "error", "error": str(e)}
        
        # Anomaly Detection
        try:
            anomalies = self.detect_anomalies(country_code)
            results["components"]["anomaly_detection"] = {
                "status": "error" if "error" in anomalies else "success",
                "data": anomalies
            }
        except Exception as e:
            results["components"]["anomaly_detection"] = {"status": "error", "error": str(e)}
        
        # Event Clustering
        try:
            clusters = self.cluster_conflict_events(country_code)
            results["components"]["event_clustering"] = {
                "status": "error" if "error" in clusters else "success",
                "data": clusters
            }
        except Exception as e:
            results["components"]["event_clustering"] = {"status": "error", "error": str(e)}
        
        # Summary
        successful = sum(1 for c in results["components"].values() if c["status"] == "success")
        results["summary"] = {
            "components_available": successful,
            "total_components": len(results["components"])
        }
        
        return results


# Singleton instance
_ml_enhancer = None


def get_ml_enhancer(db_session=None, mongo_db=None) -> MLRiskEnhancer:
    """Get or create ML risk enhancer instance."""
    global _ml_enhancer
    if _ml_enhancer is None:
        if db_session is None or mongo_db is None:
            from app.core.database import SessionLocal, get_mongo_db
            db_session = SessionLocal()
            mongo_db = get_mongo_db()
        _ml_enhancer = MLRiskEnhancer(db_session, mongo_db)
    return _ml_enhancer


if __name__ == "__main__":
    # Test ML enhancer
    import sys
    from pathlib import Path
    backend_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    
    from app.core.database import SessionLocal, get_mongo_db
    
    enhancer = MLRiskEnhancer(SessionLocal(), get_mongo_db())
    
    print("Testing ML Risk Enhancer:")
    print("=" * 80)
    
    # Test comprehensive analysis
    result = enhancer.get_comprehensive_ml_analysis("IND")
    
    print(f"\nAnalysis for {result['country_code']}:")
    print(f"Components available: {result['summary']['components_available']}/{result['summary']['total_components']}")
    
    for name, component in result["components"].items():
        print(f"\n{name}: {component['status']}")
        if component['status'] == 'success' and 'data' in component:
            data = component['data']
            if name == "topic_modeling" and "num_topics" in data:
                print(f"  Topics found: {data['num_topics']}")
            elif name == "risk_forecast" and "outlook" in data:
                print(f"  Outlook: {data['outlook'].get('outlook')}")
            elif name == "anomaly_detection" and "anomaly_count" in data:
                print(f"  Anomalies: {data['anomaly_count']}")
            elif name == "event_clustering" and "cluster_count" in data:
                print(f"  Clusters: {data['cluster_count']}")
