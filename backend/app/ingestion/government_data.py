"""
Government data ingestion module.
Coordinates scraping from multiple government sources.
"""

from typing import Dict
from app.core.logging import setup_logger
from app.scraping.government import scrape_all_government_sources

logger = setup_logger(__name__)


class GovernmentDataIngestion:
    """Ingest data from government sources (PIB, MEA, PMO)"""
    
    def __init__(self):
        logger.info("GovernmentDataIngestion initialized")
    
    def ingest_all_sources(self, days_back: int = 7) -> Dict:
        """
        Ingest data from all government sources
        
        Args:
            days_back: Number of days to look back
        
        Returns:
            Summary of ingestion results
        """
        logger.info(f"Starting government data ingestion for last {days_back} days...")
        
        try:
            # Scrape all sources
            results = scrape_all_government_sources(days_back=days_back)
            
            # Calculate totals
            total_documents = sum(len(docs) for docs in results.values())
            
            summary = {
                "total_documents": total_documents,
                "by_source": {
                    source: len(docs) for source, docs in results.items()
                },
                "days_back": days_back
            }
            
            logger.info(f"Government data ingestion complete: {total_documents} documents")
            return summary
            
        except Exception as e:
            logger.error(f"Error in government data ingestion: {e}")
            return {
                "total_documents": 0,
                "error": str(e)
            }


if __name__ == "__main__":
    # Test ingestion
    ingestion = GovernmentDataIngestion()
    result = ingestion.ingest_all_sources(days_back=7)
    print(f"Ingestion result: {result}")
