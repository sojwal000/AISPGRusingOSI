"""
Machine Learning module for AI-powered analysis.
Phase 2 & 3 implementation with advanced ML algorithms.
"""

from .sentiment import SentimentAnalyzer, get_sentiment_analyzer
from .ner import EntityExtractor, get_entity_extractor
from .topic_modeling import TopicModeler, get_topic_modeler
from .forecasting import RiskForecaster, get_risk_forecaster
from .anomaly_detection import AnomalyDetector, get_anomaly_detector
from .geopolitical_sentiment import GeopoliticalSentimentAnalyzer, get_geopolitical_analyzer
from .event_clustering import EventClusterer, get_event_clusterer

__all__ = [
    # Core ML
    "SentimentAnalyzer",
    "get_sentiment_analyzer",
    "EntityExtractor", 
    "get_entity_extractor",
    
    # Advanced ML - Phase 3
    "TopicModeler",
    "get_topic_modeler",
    "RiskForecaster",
    "get_risk_forecaster",
    "AnomalyDetector",
    "get_anomaly_detector",
    "GeopoliticalSentimentAnalyzer",
    "get_geopolitical_analyzer",
    "EventClusterer",
    "get_event_clusterer",
]
