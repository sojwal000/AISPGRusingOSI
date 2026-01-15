"""
Enhanced Geopolitical Sentiment Analysis.
Domain-specific sentiment with geopolitical lexicon and context-aware scoring.
"""

from typing import Dict, List, Optional, Tuple
import logging
import re

# Setup logger
try:
    from app.core.logging import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class GeopoliticalSentimentAnalyzer:
    """
    Enhanced sentiment analysis for geopolitical content.
    Combines transformer models with domain-specific lexicon.
    """
    
    # Geopolitical risk lexicon with intensity weights
    # Positive values = negative sentiment/higher risk
    GEOPOLITICAL_LEXICON = {
        # Conflict & Military (High Risk)
        "war": 0.9,
        "warfare": 0.9,
        "invasion": 0.95,
        "invade": 0.9,
        "attack": 0.8,
        "airstrike": 0.85,
        "bombing": 0.9,
        "bombardment": 0.85,
        "shelling": 0.8,
        "missile": 0.85,
        "rocket": 0.75,
        "military": 0.5,
        "troops": 0.5,
        "soldiers": 0.5,
        "army": 0.4,
        "combat": 0.7,
        "battle": 0.75,
        "fighting": 0.7,
        "clash": 0.65,
        "skirmish": 0.55,
        "hostilities": 0.75,
        "offensive": 0.7,
        "operation": 0.3,
        
        # Terrorism (Very High Risk)
        "terrorism": 0.95,
        "terrorist": 0.95,
        "terror": 0.9,
        "extremist": 0.85,
        "militant": 0.8,
        "insurgent": 0.75,
        "insurgency": 0.75,
        "radical": 0.65,
        "jihadist": 0.9,
        "suicide bomber": 0.95,
        "car bomb": 0.9,
        "ied": 0.85,
        "explosion": 0.7,
        
        # Violence & Casualties
        "killed": 0.85,
        "dead": 0.8,
        "death": 0.75,
        "deaths": 0.75,
        "fatalities": 0.8,
        "casualties": 0.75,
        "wounded": 0.7,
        "injured": 0.65,
        "victims": 0.7,
        "massacre": 0.95,
        "genocide": 0.98,
        "atrocity": 0.9,
        "violence": 0.7,
        "violent": 0.65,
        
        # Civil Unrest
        "protest": 0.5,
        "protests": 0.5,
        "protester": 0.45,
        "demonstration": 0.45,
        "riot": 0.75,
        "riots": 0.75,
        "rioting": 0.75,
        "unrest": 0.65,
        "uprising": 0.7,
        "rebellion": 0.75,
        "revolt": 0.7,
        "civil war": 0.9,
        "coup": 0.85,
        "overthrow": 0.8,
        
        # Political Instability
        "crisis": 0.7,
        "emergency": 0.65,
        "martial law": 0.8,
        "curfew": 0.6,
        "lockdown": 0.5,
        "instability": 0.65,
        "unstable": 0.6,
        "collapse": 0.75,
        "failed state": 0.85,
        "authoritarian": 0.55,
        "dictatorship": 0.65,
        "repression": 0.7,
        "crackdown": 0.65,
        
        # Economic Risk
        "sanctions": 0.65,
        "embargo": 0.7,
        "blockade": 0.75,
        "tariff": 0.45,
        "trade war": 0.6,
        "recession": 0.7,
        "inflation": 0.5,
        "hyperinflation": 0.8,
        "default": 0.75,
        "bankruptcy": 0.7,
        "economic crisis": 0.75,
        "currency crisis": 0.7,
        
        # Nuclear & WMD (Extreme Risk)
        "nuclear": 0.8,
        "nuclear war": 0.98,
        "nuclear weapon": 0.9,
        "atomic": 0.75,
        "uranium": 0.7,
        "plutonium": 0.75,
        "enrichment": 0.65,
        "icbm": 0.85,
        "ballistic missile": 0.8,
        "wmd": 0.9,
        "chemical weapon": 0.9,
        "biological weapon": 0.9,
        
        # Border & Territory
        "border": 0.4,
        "border dispute": 0.65,
        "territorial": 0.5,
        "territory": 0.45,
        "incursion": 0.7,
        "intrusion": 0.65,
        "violation": 0.6,
        "sovereignty": 0.45,
        "annexation": 0.8,
        "occupation": 0.75,
        
        # Diplomatic (Mixed)
        "diplomacy": -0.3,
        "diplomatic": -0.2,
        "negotiation": -0.3,
        "talks": -0.2,
        "summit": -0.2,
        "agreement": -0.4,
        "treaty": -0.4,
        "ceasefire": -0.3,
        "peace": -0.5,
        "peaceful": -0.4,
        "reconciliation": -0.4,
        "cooperation": -0.4,
        "alliance": -0.2,
        "partnership": -0.3,
        
        # Humanitarian
        "humanitarian": 0.4,
        "refugee": 0.6,
        "refugees": 0.6,
        "displaced": 0.55,
        "evacuation": 0.5,
        "aid": -0.1,
        "relief": -0.15,
        "rescue": -0.1,
        "disaster": 0.65,
        "famine": 0.75,
        "starvation": 0.8,
        
        # Threat & Warning
        "threat": 0.65,
        "threaten": 0.6,
        "warning": 0.5,
        "warn": 0.45,
        "danger": 0.6,
        "dangerous": 0.55,
        "risk": 0.4,
        "risky": 0.4,
        "alert": 0.5,
        "escalation": 0.7,
        "escalate": 0.65,
        "tension": 0.55,
        "tensions": 0.55,
    }
    
    # Intensifier words
    INTENSIFIERS = {
        "very": 1.3,
        "extremely": 1.5,
        "highly": 1.3,
        "significantly": 1.25,
        "massive": 1.4,
        "major": 1.25,
        "severe": 1.35,
        "serious": 1.25,
        "critical": 1.35,
        "intense": 1.3,
        "unprecedented": 1.4,
        "dramatic": 1.2,
        "sharp": 1.2,
        "sudden": 1.15,
    }
    
    # Negation words
    NEGATIONS = ["not", "no", "never", "neither", "nobody", "nothing", "nowhere", 
                 "without", "despite", "deny", "denied", "denies", "fail", "failed"]
    
    def __init__(self, use_transformer: bool = True):
        """
        Initialize geopolitical sentiment analyzer.
        
        Args:
            use_transformer: Whether to use transformer model as base
        """
        self.use_transformer = use_transformer
        self._transformer_analyzer = None
        logger.info(f"GeopoliticalSentimentAnalyzer initialized (transformer={use_transformer})")
    
    def _get_transformer_analyzer(self):
        """Lazy load transformer analyzer."""
        if self._transformer_analyzer is None and self.use_transformer:
            try:
                from app.ml.sentiment import get_sentiment_analyzer
                self._transformer_analyzer = get_sentiment_analyzer()
                logger.info("Loaded transformer sentiment analyzer")
            except Exception as e:
                logger.warning(f"Could not load transformer: {e}")
                self._transformer_analyzer = "not_available"
        return self._transformer_analyzer
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis."""
        # Lowercase
        text = text.lower()
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _find_lexicon_matches(self, text: str) -> List[Dict]:
        """
        Find geopolitical lexicon matches in text.
        
        Args:
            text: Preprocessed text
        
        Returns:
            List of matches with word, position, and weight
        """
        matches = []
        words = text.split()
        
        # Check single words
        for i, word in enumerate(words):
            # Clean word
            clean_word = re.sub(r'[^\w\s-]', '', word)
            
            if clean_word in self.GEOPOLITICAL_LEXICON:
                weight = self.GEOPOLITICAL_LEXICON[clean_word]
                
                # Check for negation
                if i > 0 and words[i-1] in self.NEGATIONS:
                    weight = -weight * 0.5
                
                # Check for intensifier
                if i > 0 and words[i-1] in self.INTENSIFIERS:
                    weight *= self.INTENSIFIERS[words[i-1]]
                
                matches.append({
                    "word": clean_word,
                    "position": i,
                    "weight": weight,
                    "negated": i > 0 and words[i-1] in self.NEGATIONS
                })
        
        # Check bigrams
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            clean_bigram = re.sub(r'[^\w\s-]', '', bigram)
            
            if clean_bigram in self.GEOPOLITICAL_LEXICON:
                weight = self.GEOPOLITICAL_LEXICON[clean_bigram]
                
                # Check for negation
                if i > 0 and words[i-1] in self.NEGATIONS:
                    weight = -weight * 0.5
                
                matches.append({
                    "word": clean_bigram,
                    "position": i,
                    "weight": weight,
                    "negated": i > 0 and words[i-1] in self.NEGATIONS
                })
        
        return matches
    
    def analyze_lexicon(self, text: str) -> Dict:
        """
        Analyze text using geopolitical lexicon only.
        
        Args:
            text: Text to analyze
        
        Returns:
            Lexicon-based sentiment analysis
        """
        if not text or len(text.strip()) == 0:
            return {
                "lexicon_score": 0.0,
                "risk_indicators": [],
                "positive_indicators": [],
                "match_count": 0
            }
        
        processed_text = self._preprocess_text(text)
        matches = self._find_lexicon_matches(processed_text)
        
        if not matches:
            return {
                "lexicon_score": 0.0,
                "risk_indicators": [],
                "positive_indicators": [],
                "match_count": 0
            }
        
        # Separate positive (risk-increasing) and negative (risk-decreasing) indicators
        risk_indicators = [m for m in matches if m['weight'] > 0]
        positive_indicators = [m for m in matches if m['weight'] < 0]
        
        # Calculate weighted score
        total_weight = sum(m['weight'] for m in matches)
        avg_weight = total_weight / len(matches) if matches else 0
        
        # Normalize to 0-1 (with center at 0.5)
        normalized_score = max(0, min(1, 0.5 + avg_weight * 0.5))
        
        return {
            "lexicon_score": round(normalized_score, 4),
            "average_weight": round(avg_weight, 4),
            "risk_indicators": [{"word": m['word'], "weight": m['weight']} for m in risk_indicators[:10]],
            "positive_indicators": [{"word": m['word'], "weight": m['weight']} for m in positive_indicators[:5]],
            "match_count": len(matches),
            "risk_indicator_count": len(risk_indicators),
            "positive_indicator_count": len(positive_indicators)
        }
    
    def analyze(self, text: str) -> Dict:
        """
        Full geopolitical sentiment analysis combining transformer and lexicon.
        
        Args:
            text: Text to analyze
        
        Returns:
            Combined sentiment analysis
        """
        if not text or len(text.strip()) == 0:
            return {
                "combined_score": 0.5,
                "risk_level": "neutral",
                "confidence": 0.0,
                "components": {}
            }
        
        # Get lexicon analysis
        lexicon_result = self.analyze_lexicon(text)
        
        # Try transformer analysis
        transformer_result = None
        analyzer = self._get_transformer_analyzer()
        
        if analyzer and analyzer != "not_available":
            try:
                transformer_result = analyzer.analyze(text)
            except Exception as e:
                logger.warning(f"Transformer analysis failed: {e}")
        
        # Combine results
        if transformer_result and lexicon_result['match_count'] > 0:
            # Both available - weighted combination
            # Lexicon weighted more for geopolitical content
            lexicon_weight = min(0.6, 0.3 + lexicon_result['match_count'] * 0.05)
            transformer_weight = 1.0 - lexicon_weight
            
            # Convert transformer score: normalized_score is -1 to +1
            # Convert to risk score: -1 (positive news) -> 0.2, +1 (negative news) -> 0.8
            transformer_risk = 0.5 - transformer_result['normalized_score'] * 0.3
            
            combined_score = (
                lexicon_result['lexicon_score'] * lexicon_weight +
                transformer_risk * transformer_weight
            )
            
            confidence = (transformer_result['confidence'] + 0.8) / 2  # Avg with lexicon confidence
            
        elif transformer_result:
            # Only transformer
            combined_score = 0.5 - transformer_result['normalized_score'] * 0.3
            confidence = transformer_result['confidence']
            
        else:
            # Only lexicon
            combined_score = lexicon_result['lexicon_score']
            confidence = 0.6 if lexicon_result['match_count'] > 3 else 0.4
        
        # Determine risk level
        if combined_score >= 0.75:
            risk_level = "critical"
        elif combined_score >= 0.6:
            risk_level = "high"
        elif combined_score >= 0.4:
            risk_level = "moderate"
        elif combined_score >= 0.25:
            risk_level = "low"
        else:
            risk_level = "minimal"
        
        return {
            "combined_score": round(combined_score, 4),
            "risk_level": risk_level,
            "confidence": round(confidence, 4),
            "components": {
                "lexicon": lexicon_result,
                "transformer": transformer_result
            },
            "top_risk_indicators": lexicon_result.get('risk_indicators', [])[:5],
            "top_positive_indicators": lexicon_result.get('positive_indicators', [])[:3]
        }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        Analyze multiple texts efficiently.
        
        Args:
            texts: List of texts to analyze
        
        Returns:
            List of analysis results
        """
        return [self.analyze(text) for text in texts]
    
    def calculate_document_risk(self, analysis: Dict) -> float:
        """
        Calculate overall risk score from analysis (0-100).
        
        Args:
            analysis: Output from analyze()
        
        Returns:
            Risk score 0-100
        """
        combined = analysis.get('combined_score', 0.5)
        
        # Map 0-1 to 0-100 with emphasis on high scores
        risk_score = combined * 100
        
        # Boost if many risk indicators found
        lexicon = analysis.get('components', {}).get('lexicon', {})
        risk_count = lexicon.get('risk_indicator_count', 0)
        
        if risk_count > 5:
            risk_score = min(100, risk_score * 1.1)
        
        return round(risk_score, 2)
    
    def extract_key_risks(self, text: str) -> List[Dict]:
        """
        Extract key risk factors from text.
        
        Args:
            text: Text to analyze
        
        Returns:
            List of identified risk factors
        """
        processed = self._preprocess_text(text)
        matches = self._find_lexicon_matches(processed)
        
        # Group by category
        categories = {
            "conflict": ["war", "military", "attack", "battle", "combat", "troops", "fighting"],
            "terrorism": ["terror", "extremist", "militant", "bomb", "explosion"],
            "violence": ["killed", "death", "violence", "massacre", "casualties"],
            "unrest": ["protest", "riot", "uprising", "coup", "rebellion"],
            "economic": ["sanctions", "recession", "crisis", "default", "inflation"],
            "nuclear": ["nuclear", "missile", "uranium", "icbm", "wmd"],
            "diplomatic": ["diplomacy", "talks", "agreement", "peace", "treaty"]
        }
        
        risks = []
        seen_categories = set()
        
        for match in matches:
            if match['weight'] <= 0:
                continue
            
            # Find category
            word = match['word']
            for cat, keywords in categories.items():
                if any(kw in word for kw in keywords):
                    if cat not in seen_categories:
                        risks.append({
                            "category": cat,
                            "keyword": word,
                            "intensity": match['weight'],
                            "severity": "high" if match['weight'] > 0.7 else "medium"
                        })
                        seen_categories.add(cat)
                    break
        
        return sorted(risks, key=lambda x: x['intensity'], reverse=True)


# Singleton instance
_geo_analyzer = None


def get_geopolitical_analyzer() -> GeopoliticalSentimentAnalyzer:
    """Get or create singleton geopolitical analyzer."""
    global _geo_analyzer
    if _geo_analyzer is None:
        _geo_analyzer = GeopoliticalSentimentAnalyzer()
    return _geo_analyzer


if __name__ == "__main__":
    # Test geopolitical sentiment
    analyzer = GeopoliticalSentimentAnalyzer(use_transformer=False)  # Lexicon only for testing
    
    test_texts = [
        "Military forces launched a massive airstrike against terrorist positions, killing dozens",
        "Peace talks resume as diplomats negotiate ceasefire agreement",
        "Violent protests erupt in capital amid economic crisis and rising inflation",
        "Border tensions escalate as troops exchange fire in disputed territory",
        "Trade agreement signed, boosting economic cooperation between nations"
    ]
    
    print("Testing Geopolitical Sentiment Analysis:")
    print("=" * 80)
    
    for text in test_texts:
        result = analyzer.analyze(text)
        risk_score = analyzer.calculate_document_risk(result)
        
        print(f"\nText: {text[:70]}...")
        print(f"Risk Level: {result['risk_level']}")
        print(f"Combined Score: {result['combined_score']:.2f}")
        print(f"Risk Score (0-100): {risk_score}")
        
        if result['top_risk_indicators']:
            indicators = [f"{i['word']}({i['weight']:.2f})" for i in result['top_risk_indicators'][:3]]
            print(f"Risk Indicators: {', '.join(indicators)}")
        
        if result['top_positive_indicators']:
            positives = [f"{i['word']}" for i in result['top_positive_indicators']]
            print(f"Positive Indicators: {', '.join(positives)}")
