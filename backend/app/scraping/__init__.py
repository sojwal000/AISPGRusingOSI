"""
Web scraping module for government data sources.
Phase 2.2 implementation.
"""

from .government import PIBScraper, MEAScraper, PMOScraper

__all__ = ["PIBScraper", "MEAScraper", "PMOScraper"]
