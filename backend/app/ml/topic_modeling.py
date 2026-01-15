"""
Topic Modeling using BERTopic for automatic theme discovery.
Identifies emerging topics in news articles and government reports.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import numpy as np

# Setup logger
try:
    from app.core.logging import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class TopicModeler:
    """
    Topic modeling using BERTopic for dynamic topic discovery.
    Identifies geopolitical themes from text data.
    """
    
    # Geopolitical seed topics for guided modeling
    SEED_TOPICS = [
        ["war", "military", "conflict", "army", "defense", "attack", "troops"],
        ["economy", "inflation", "gdp", "trade", "market", "recession", "growth"],
        ["terrorism", "extremism", "attack", "violence", "militant", "insurgency"],
        ["diplomacy", "relations", "treaty", "summit", "agreement", "talks"],
        ["election", "vote", "government", "parliament", "democracy", "political"],
        ["protest", "demonstration", "strike", "unrest", "riot", "civil"],
        ["border", "territory", "dispute", "sovereignty", "incursion"],
        ["sanctions", "embargo", "restrictions", "tariff", "trade war"],
        ["nuclear", "missile", "weapons", "proliferation", "arms"],
        ["humanitarian", "crisis", "refugee", "aid", "disaster", "relief"]
    ]
    
    # Risk multipliers for different topics
    TOPIC_RISK_WEIGHTS = {
        "conflict": 1.5,
        "terrorism": 1.4,
        "nuclear": 1.6,
        "protest": 1.2,
        "economy_negative": 1.3,
        "border": 1.3,
        "sanctions": 1.1,
        "diplomacy": 0.8,  # Positive indicator
        "election": 1.0,
        "humanitarian": 1.2
    }
    
    def __init__(self, min_topic_size: int = 5, n_topics: int = 15):
        """
        Initialize topic modeler.
        
        Args:
            min_topic_size: Minimum documents per topic
            n_topics: Target number of topics (auto if None)
        """
        self.min_topic_size = min_topic_size
        self.n_topics = n_topics
        self.model = None
        self.embedding_model = None
        self._initialized = False
        
        logger.info(f"TopicModeler initialized (lazy loading enabled)")
    
    def _ensure_initialized(self):
        """Lazy initialize BERTopic model."""
        if self._initialized:
            return True
        
        try:
            from bertopic import BERTopic
            from sentence_transformers import SentenceTransformer
            from sklearn.feature_extraction.text import CountVectorizer
            
            logger.info("Initializing BERTopic model...")
            
            # Use a lightweight embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Custom vectorizer for better topic representation
            vectorizer = CountVectorizer(
                stop_words="english",
                min_df=2,
                max_df=0.95,
                ngram_range=(1, 2)
            )
            
            # Initialize BERTopic with guided topics
            self.model = BERTopic(
                embedding_model=self.embedding_model,
                vectorizer_model=vectorizer,
                min_topic_size=self.min_topic_size,
                nr_topics=self.n_topics,
                seed_topic_list=self.SEED_TOPICS,
                calculate_probabilities=True,
                verbose=False
            )
            
            self._initialized = True
            logger.info("BERTopic model initialized successfully")
            return True
            
        except ImportError as e:
            logger.warning(f"BERTopic dependencies not installed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize BERTopic: {e}")
            return False
    
    def fit_transform(self, documents: List[str]) -> Tuple[List[int], Optional[np.ndarray]]:
        """
        Fit topic model and transform documents.
        
        Args:
            documents: List of text documents
        
        Returns:
            Tuple of (topic assignments, probabilities)
        """
        if not documents or len(documents) < self.min_topic_size:
            logger.warning(f"Not enough documents for topic modeling: {len(documents)}")
            return [-1] * len(documents), None
        
        if not self._ensure_initialized():
            return [-1] * len(documents), None
        
        try:
            topics, probs = self.model.fit_transform(documents)
            logger.info(f"Fit topic model on {len(documents)} documents, found {len(set(topics))} topics")
            return topics, probs
        except Exception as e:
            logger.error(f"Error in topic modeling: {e}")
            return [-1] * len(documents), None
    
    def get_topics(self) -> Dict[int, List[Tuple[str, float]]]:
        """
        Get discovered topics with keywords.
        
        Returns:
            Dictionary mapping topic ID to list of (keyword, weight) tuples
        """
        if not self._initialized or self.model is None:
            return {}
        
        try:
            return self.model.get_topics()
        except Exception as e:
            logger.error(f"Error getting topics: {e}")
            return {}
    
    def get_topic_info(self) -> List[Dict]:
        """
        Get topic information including counts and keywords.
        
        Returns:
            List of topic info dictionaries
        """
        if not self._initialized or self.model is None:
            return []
        
        try:
            topic_info = self.model.get_topic_info()
            return topic_info.to_dict('records')
        except Exception as e:
            logger.error(f"Error getting topic info: {e}")
            return []
    
    def classify_topic_risk(self, topic_keywords: List[str]) -> Tuple[str, float]:
        """
        Classify a topic's risk category and weight.
        
        Args:
            topic_keywords: Top keywords for the topic
        
        Returns:
            Tuple of (risk_category, risk_multiplier)
        """
        keywords_lower = [k.lower() for k in topic_keywords]
        keywords_text = " ".join(keywords_lower)
        
        # Define risk category patterns
        risk_patterns = {
            "conflict": ["war", "military", "conflict", "attack", "troops", "army", "combat"],
            "terrorism": ["terror", "extremist", "militant", "attack", "violence", "bomb"],
            "nuclear": ["nuclear", "missile", "weapons", "atomic", "proliferation"],
            "protest": ["protest", "demonstration", "riot", "unrest", "strike"],
            "economy_negative": ["recession", "crisis", "collapse", "crash", "inflation"],
            "border": ["border", "territory", "incursion", "intrusion", "sovereignty"],
            "sanctions": ["sanction", "embargo", "tariff", "restriction", "ban"],
            "diplomacy": ["diplomacy", "talk", "summit", "agreement", "treaty", "peace"],
            "election": ["election", "vote", "democracy", "parliament", "political"],
            "humanitarian": ["humanitarian", "refugee", "crisis", "aid", "disaster"]
        }
        
        # Find best matching category
        best_category = "general"
        best_score = 0
        
        for category, patterns in risk_patterns.items():
            score = sum(1 for p in patterns if p in keywords_text)
            if score > best_score:
                best_score = score
                best_category = category
        
        risk_multiplier = self.TOPIC_RISK_WEIGHTS.get(best_category, 1.0)
        return best_category, risk_multiplier
    
    def analyze_documents(self, documents: List[str], 
                         metadata: Optional[List[Dict]] = None) -> Dict:
        """
        Full topic analysis on documents.
        
        Args:
            documents: List of text documents
            metadata: Optional list of metadata dicts for each document
        
        Returns:
            Complete analysis results
        """
        if not documents:
            return {"error": "No documents provided", "topics": []}
        
        # Fit model and get topics
        topics, probs = self.fit_transform(documents)
        
        # Get topic information
        topic_info = self.get_topic_info()
        
        # Analyze each topic
        analyzed_topics = []
        for topic in topic_info:
            if topic.get('Topic', -1) == -1:  # Skip outliers
                continue
            
            topic_id = topic.get('Topic', 0)
            keywords = self.get_topics().get(topic_id, [])
            keyword_list = [k[0] for k in keywords[:10]]
            
            # Classify risk
            risk_category, risk_multiplier = self.classify_topic_risk(keyword_list)
            
            analyzed_topics.append({
                "topic_id": topic_id,
                "count": topic.get('Count', 0),
                "name": topic.get('Name', f'Topic_{topic_id}'),
                "keywords": keyword_list,
                "risk_category": risk_category,
                "risk_multiplier": risk_multiplier
            })
        
        # Calculate overall topic distribution
        topic_distribution = {}
        for t in topics:
            if t != -1:  # Exclude outliers
                topic_distribution[t] = topic_distribution.get(t, 0) + 1
        
        # Calculate weighted risk factor from topics
        total_docs = sum(topic_distribution.values()) if topic_distribution else 1
        weighted_risk = 0.0
        for topic in analyzed_topics:
            topic_count = topic_distribution.get(topic['topic_id'], 0)
            topic_weight = topic_count / total_docs
            weighted_risk += topic_weight * topic['risk_multiplier']
        
        return {
            "total_documents": len(documents),
            "num_topics": len(analyzed_topics),
            "topics": analyzed_topics,
            "topic_distribution": topic_distribution,
            "weighted_risk_factor": round(weighted_risk, 4),
            "outlier_count": topics.count(-1)
        }
    
    def get_trending_topics(self, current_analysis: Dict, 
                           previous_analysis: Optional[Dict] = None) -> List[Dict]:
        """
        Identify trending (growing) topics by comparing analyses.
        
        Args:
            current_analysis: Current topic analysis
            previous_analysis: Previous period analysis
        
        Returns:
            List of trending topics with growth metrics
        """
        if not previous_analysis:
            # No comparison available, return top topics by count
            topics = current_analysis.get('topics', [])
            return sorted(topics, key=lambda x: x.get('count', 0), reverse=True)[:5]
        
        current_dist = current_analysis.get('topic_distribution', {})
        previous_dist = previous_analysis.get('topic_distribution', {})
        
        # Calculate growth for each topic
        trending = []
        for topic in current_analysis.get('topics', []):
            topic_id = topic['topic_id']
            current_count = current_dist.get(topic_id, 0)
            previous_count = previous_dist.get(topic_id, 1)  # Avoid division by zero
            
            growth_rate = (current_count - previous_count) / previous_count
            
            trending.append({
                **topic,
                "growth_rate": round(growth_rate, 4),
                "previous_count": previous_count,
                "is_emerging": previous_count == 0 or growth_rate > 0.5
            })
        
        # Sort by growth rate
        return sorted(trending, key=lambda x: x.get('growth_rate', 0), reverse=True)


# Singleton instance
_topic_modeler = None


def get_topic_modeler() -> TopicModeler:
    """Get or create singleton topic modeler instance."""
    global _topic_modeler
    if _topic_modeler is None:
        _topic_modeler = TopicModeler()
    return _topic_modeler


if __name__ == "__main__":
    # Test topic modeling
    modeler = TopicModeler()
    
    test_docs = [
        "Military forces deployed along the border region amid rising tensions",
        "Army conducts exercises near disputed territory",
        "Border clashes reported between patrol forces",
        "Trade negotiations resume after months of sanctions",
        "Economic summit discusses tariff reductions",
        "Bilateral trade agreement signed by ministers",
        "Protesters gather in capital demanding reforms",
        "Demonstration against government policies turns violent",
        "Police deploy tear gas to disperse crowds",
        "Election campaign kicks off with rallies",
        "Voters head to polls in closely watched election",
        "Political parties debate economic policies",
        "Humanitarian aid reaches disaster-affected areas",
        "Relief organizations coordinate response to crisis",
        "Refugee camps established near conflict zone"
    ]
    
    print("Testing Topic Modeling:")
    print("=" * 80)
    
    result = modeler.analyze_documents(test_docs)
    print(f"Total documents: {result['total_documents']}")
    print(f"Topics found: {result['num_topics']}")
    print(f"Weighted risk factor: {result['weighted_risk_factor']}")
    print()
    
    for topic in result['topics']:
        print(f"Topic {topic['topic_id']}: {topic['risk_category']}")
        print(f"  Keywords: {', '.join(topic['keywords'][:5])}")
        print(f"  Count: {topic['count']}, Risk multiplier: {topic['risk_multiplier']}")
        print()
