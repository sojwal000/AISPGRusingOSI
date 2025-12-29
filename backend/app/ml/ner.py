"""
Named Entity Recognition using spaCy.
Extracts entities (persons, organizations, locations) from text.
"""

from typing import Dict, List, Optional
from app.core.logging import setup_logger

logger = setup_logger(__name__)


class EntityExtractor:
    """
    Named Entity Recognition using spaCy.
    Extracts key entities from news articles and government reports.
    """
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize entity extractor with spaCy model.
        
        Note: spaCy model must be downloaded first:
            python -m spacy download en_core_web_sm
        
        Args:
            model_name: spaCy model name
        """
        self.model_name = model_name
        self.nlp = None
        
        # Lazy loading - only load when needed
        logger.info(f"EntityExtractor initialized (model will load on first use)")
    
    def _ensure_model_loaded(self):
        """Lazy load spaCy model on first use."""
        if self.nlp is None:
            try:
                import spacy
                logger.info(f"Loading spaCy model: {self.model_name}")
                self.nlp = spacy.load(self.model_name)
                logger.info("spaCy model loaded successfully")
            except ImportError:
                logger.warning("spaCy not installed - NER disabled for Phase 2.1")
                self.nlp = "not_available"
            except Exception as e:
                logger.warning(f"Failed to load spaCy model: {e}")
                self.nlp = "not_available"
    
    def extract_entities(self, text: str) -> List[Dict]:
        """
        Extract named entities from text.
        
        Args:
            text: Text to analyze
        
        Returns:
            List of entities with type, text, and confidence
        """
        self._ensure_model_loaded()
        
        if self.nlp == "not_available":
            return []
        
        if not text or len(text.strip()) == 0:
            return []
        
        try:
            # Process text
            doc = self.nlp(text[:10000])  # Limit to 10k chars
            
            entities = []
            for ent in doc.ents:
                entities.append({
                    "type": ent.label_,
                    "text": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    def extract_key_actors(self, text: str) -> Dict:
        """
        Extract key actors (people, organizations) from text.
        
        Args:
            text: Text to analyze
        
        Returns:
            Dictionary with persons and organizations
        """
        entities = self.extract_entities(text)
        
        persons = [e["text"] for e in entities if e["type"] in ["PERSON", "PER"]]
        organizations = [e["text"] for e in entities if e["type"] in ["ORG", "ORGANIZATION"]]
        locations = [e["text"] for e in entities if e["type"] in ["GPE", "LOC", "LOCATION"]]
        
        return {
            "persons": list(set(persons)),  # Remove duplicates
            "organizations": list(set(organizations)),
            "locations": list(set(locations))
        }


# Singleton instance
_entity_extractor = None


def get_entity_extractor() -> EntityExtractor:
    """Get or create singleton entity extractor instance."""
    global _entity_extractor
    if _entity_extractor is None:
        _entity_extractor = EntityExtractor()
    return _entity_extractor


if __name__ == "__main__":
    # Test entity extraction
    extractor = EntityExtractor()
    
    test_text = """
    Prime Minister Narendra Modi announced a new infrastructure plan today.
    The BJP government has allocated funds for development in Maharashtra and Gujarat.
    External Affairs Minister S. Jaishankar met with US officials in Washington.
    """
    
    print("Testing Entity Extraction:")
    print("=" * 80)
    print(f"Text: {test_text}")
    print()
    
    entities = extractor.extract_entities(test_text)
    print(f"All Entities: {entities}")
    print()
    
    actors = extractor.extract_key_actors(test_text)
    print(f"Key Actors: {actors}")
