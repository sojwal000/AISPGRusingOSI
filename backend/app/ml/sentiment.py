"""
Sentiment Analysis using HuggingFace Transformers.
Analyzes text sentiment for news articles and government reports.
"""

from typing import Dict, List, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
import logging

# Setup logger
try:
    from app.core.logging import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    # Fallback for standalone execution
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Sentiment analysis using pre-trained transformer models.
    Uses DistilBERT for efficient, accurate sentiment scoring.
    """
    
    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        """
        Initialize sentiment analyzer with specified model.
        
        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.device = 0 if torch.cuda.is_available() else -1
        
        logger.info(f"Loading sentiment model: {model_name}")
        logger.info(f"Using device: {'GPU' if self.device == 0 else 'CPU'}")
        
        try:
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=model_name,
                device=self.device,
                truncation=True,
                max_length=512
            )
            logger.info("Sentiment model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentiment model: {e}")
            raise
    
    def analyze(self, text: str, return_all: bool = False) -> Dict:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Text to analyze
            return_all: If True, return all model outputs
        
        Returns:
            Dictionary with sentiment label, score, and normalized score (-1 to +1)
        """
        if not text or len(text.strip()) == 0:
            return {
                "label": "NEUTRAL",
                "score": 0.0,
                "normalized_score": 0.0,
                "confidence": 0.0
            }
        
        try:
            # Truncate very long texts
            text = text[:5000] if len(text) > 5000 else text
            
            result = self.pipeline(text)[0]
            
            # Normalize score to -1 (negative) to +1 (positive)
            label = result["label"].upper()
            confidence = result["score"]
            
            if label == "POSITIVE":
                normalized_score = confidence
            elif label == "NEGATIVE":
                normalized_score = -confidence
            else:
                normalized_score = 0.0
            
            return {
                "label": label,
                "score": confidence,
                "normalized_score": round(normalized_score, 4),
                "confidence": round(confidence, 4)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "label": "NEUTRAL",
                "score": 0.0,
                "normalized_score": 0.0,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def analyze_batch(self, texts: List[str], batch_size: int = 8) -> List[Dict]:
        """
        Analyze sentiment for multiple texts in batches for efficiency.
        
        Args:
            texts: List of texts to analyze
            batch_size: Number of texts to process in parallel
        
        Returns:
            List of sentiment analysis results
        """
        if not texts:
            return []
        
        # Filter empty texts
        valid_texts = [t[:5000] if len(t) > 5000 else t for t in texts if t and len(t.strip()) > 0]
        
        if not valid_texts:
            return [{"label": "NEUTRAL", "score": 0.0, "normalized_score": 0.0, "confidence": 0.0}] * len(texts)
        
        try:
            results = []
            
            # Process in batches
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i+batch_size]
                batch_results = self.pipeline(batch)
                
                for result in batch_results:
                    label = result["label"].upper()
                    confidence = result["score"]
                    
                    if label == "POSITIVE":
                        normalized_score = confidence
                    elif label == "NEGATIVE":
                        normalized_score = -confidence
                    else:
                        normalized_score = 0.0
                    
                    results.append({
                        "label": label,
                        "score": confidence,
                        "normalized_score": round(normalized_score, 4),
                        "confidence": round(confidence, 4)
                    })
            
            logger.info(f"Analyzed sentiment for {len(results)} texts")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch sentiment analysis: {e}")
            return [{"label": "NEUTRAL", "score": 0.0, "normalized_score": 0.0, "confidence": 0.0}] * len(texts)
    
    def analyze_article(self, article: Dict) -> Dict:
        """
        Analyze sentiment for a news article (title + content).
        
        Args:
            article: Dictionary with 'title' and 'content' keys
        
        Returns:
            Combined sentiment analysis result
        """
        title = article.get("title", "")
        content = article.get("content", "")
        
        # Combine title and content, prioritize title
        combined_text = f"{title}. {content}"
        
        sentiment = self.analyze(combined_text)
        
        # Weight title sentiment more heavily (60%) if available
        if title and content:
            title_sentiment = self.analyze(title)
            content_sentiment = self.analyze(content[:1000])  # First 1000 chars
            
            # Weighted average
            sentiment["normalized_score"] = round(
                title_sentiment["normalized_score"] * 0.6 + 
                content_sentiment["normalized_score"] * 0.4,
                4
            )
            sentiment["confidence"] = round(
                (title_sentiment["confidence"] + content_sentiment["confidence"]) / 2,
                4
            )
        
        return sentiment
    
    def calculate_aggregate_sentiment(self, sentiments: List[Dict]) -> Dict:
        """
        Calculate aggregate sentiment statistics from multiple analyses.
        
        Args:
            sentiments: List of sentiment analysis results
        
        Returns:
            Aggregate statistics
        """
        if not sentiments:
            return {
                "mean_score": 0.0,
                "median_score": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0
            }
        
        scores = [s["normalized_score"] for s in sentiments]
        
        positive_count = sum(1 for s in sentiments if s["label"] == "POSITIVE")
        negative_count = sum(1 for s in sentiments if s["label"] == "NEGATIVE")
        neutral_count = len(sentiments) - positive_count - negative_count
        
        total = len(sentiments)
        
        return {
            "mean_score": round(sum(scores) / total, 4),
            "median_score": round(sorted(scores)[total // 2], 4),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "positive_ratio": round(positive_count / total, 4),
            "negative_ratio": round(negative_count / total, 4),
            "total_analyzed": total
        }
    
    def convert_sentiment_to_risk_score(self, sentiment: Dict, baseline: float = 50.0) -> float:
        """
        Convert sentiment score to risk score (0-100).
        More negative sentiment = higher risk.
        
        Args:
            sentiment: Sentiment analysis result
            baseline: Baseline risk score (default 50)
        
        Returns:
            Risk score (0-100)
        """
        normalized_score = sentiment["normalized_score"]
        confidence = sentiment["confidence"]
        
        # Map sentiment to risk:
        # -1 (very negative) -> +50 risk points
        # +1 (very positive) -> -30 risk points
        # Weight by confidence
        
        risk_adjustment = -normalized_score * 40 * confidence
        risk_score = baseline + risk_adjustment
        
        # Clamp to 0-100
        return max(0.0, min(risk_score, 100.0))


# Singleton instance for reuse
_sentiment_analyzer = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create singleton sentiment analyzer instance."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer


if __name__ == "__main__":
    # Add backend to path for testing
    import sys
    from pathlib import Path
    backend_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    
    # Test sentiment analysis
    analyzer = SentimentAnalyzer()
    
    test_texts = [
        "Breaking: Violent protests erupt in major city, several injured",
        "Economic growth exceeds expectations, markets rally",
        "Government announces new infrastructure development plan",
        "Tensions escalate after border incident, military on alert"
    ]
    
    print("Testing Sentiment Analysis:")
    print("=" * 80)
    
    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\nText: {text}")
        print(f"Sentiment: {result['label']} (score: {result['normalized_score']:.2f})")
        print(f"Risk Score: {analyzer.convert_sentiment_to_risk_score(result):.2f}")
    
    print("\n" + "=" * 80)
    print("Batch Analysis:")
    batch_results = analyzer.analyze_batch(test_texts)
    aggregate = analyzer.calculate_aggregate_sentiment(batch_results)
    print(f"Aggregate: {aggregate}")
