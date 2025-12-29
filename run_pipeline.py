"""
Main pipeline runner for geopolitical risk analysis.
Executes data ingestion and risk scoring for India.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.logging import setup_logger
from app.ingestion.news_rss import NewsRSSIngestion
from app.ingestion.gdelt import GDELTIngestion
from app.ingestion.worldbank import WorldBankIngestion
from app.ingestion.government_data import GovernmentDataIngestion  # Phase 2.2
from app.scoring.risk_engine import RiskScoringEngine
import json

logger = setup_logger("pipeline", "INFO")

# Valid ISO 3-letter country codes mapping
COUNTRY_CODE_MAP = {
    "india": "IND",
    "usa": "USA",
    "united states": "USA",
    "china": "CHN",
    "russia": "RUS",
    "pakistan": "PAK",
    "bangladesh": "BGD",
    "uk": "GBR",
    "france": "FRA",
    "germany": "DEU",
    "japan": "JPN"
}


def validate_country_code(country_code: str) -> str:
    """
    Validate and normalize country code to ISO 3-letter format.
    
    Args:
        country_code: Country code or name
        
    Returns:
        Valid 3-letter ISO country code
        
    Raises:
        ValueError: If country code is invalid
    """
    # Convert to uppercase and strip whitespace
    code = country_code.strip().upper()
    
    # Check if it's already a valid 3-letter code
    if len(code) == 3 and code.isalpha():
        return code
    
    # Try to map from common names
    code_lower = country_code.strip().lower()
    if code_lower in COUNTRY_CODE_MAP:
        return COUNTRY_CODE_MAP[code_lower]
    
    # Invalid format
    raise ValueError(
        f"Invalid country code: '{country_code}'. "
        f"Must be a 3-letter ISO code (e.g., USA, CHN, IND) or common name. "
        f"Valid examples: IND, USA, CHN, RUS, PAK, BGD"
    )


def run_full_pipeline(country_code: str = "IND"):
    """
    Run complete data ingestion and risk scoring pipeline.
    
    Args:
        country_code: ISO 3-letter country code (default: IND for India)
    """
    # Validate and normalize country code
    try:
        country_code = validate_country_code(country_code)
    except ValueError as e:
        logger.error(f"❌ {e}")
        return
    
    logger.info("=" * 80)
    logger.info("GEOPOLITICAL RISK ANALYSIS PIPELINE - PHASE 2")
    logger.info("=" * 80)
    logger.info(f"🌍 Target Country: {country_code}")
    
    results = {
        "country": country_code,
        "ingestion": {},
        "risk_score": None
    }
    
    # Step 1: Ingest News Data
    logger.info("\n[STEP 1/4] Ingesting news data from RSS feeds...")
    try:
        news_ingestion = NewsRSSIngestion()
        news_result = news_ingestion.ingest_all_feeds(days_back=7)
        results["ingestion"]["news"] = news_result
        logger.info(f"✓ News ingestion complete: {news_result}")
    except Exception as e:
        logger.error(f"✗ News ingestion failed: {e}")
        results["ingestion"]["news"] = {"error": str(e)}
    
    # Step 2: Ingest GDELT Conflict Data
    logger.info("\n[STEP 2/4] Ingesting conflict events from GDELT...")
    try:
        gdelt_ingestion = GDELTIngestion()
        # Reduce to last 48 hours to avoid processing thousands of files
        # GDELT publishes every 15 mins = 96 files per day × 2 days = ~192 files
        gdelt_result = gdelt_ingestion.ingest(hours_back=60, country_code=country_code)
        results["ingestion"]["gdelt"] = gdelt_result
        logger.info(f"✓ GDELT ingestion complete: {gdelt_result}")
    except Exception as e:
        logger.error(f"✗ GDELT ingestion failed: {e}")
        results["ingestion"]["gdelt"] = {"error": str(e)}
    
    # Step 3: Ingest World Bank Economic Data
    logger.info("\n[STEP 3/5] Ingesting economic indicators from World Bank...")
    try:
        wb_ingestion = WorldBankIngestion()
        wb_result = wb_ingestion.ingest_country(country_code, years_back=5)
        results["ingestion"]["worldbank"] = wb_result
        logger.info(f"✓ World Bank ingestion complete: {wb_result}")
    except Exception as e:
        logger.error(f"✗ World Bank ingestion failed: {e}")
        results["ingestion"]["worldbank"] = {"error": str(e)}
    
    # Step 4: Ingest Government Data (Phase 2.2)
    logger.info("\n[STEP 4/5] Ingesting government data from PIB, MEA, PMO...")
    try:
        gov_ingestion = GovernmentDataIngestion()
        gov_result = gov_ingestion.ingest_all_sources(days_back=7)
        results["ingestion"]["government"] = gov_result
        logger.info(f"✓ Government data ingestion complete: {gov_result}")
    except Exception as e:
        logger.error(f"✗ Government data ingestion failed: {e}")
        results["ingestion"]["government"] = {"error": str(e)}
    
    # Step 5: Calculate Risk Score
    logger.info("\n[STEP 5/5] Calculating geopolitical risk score...")
    try:
        risk_engine = RiskScoringEngine()
        risk_result = risk_engine.calculate_overall_risk(country_code)
        results["risk_score"] = risk_result
        logger.info(f"✓ Risk score calculated: {risk_result['overall_score']:.2f}")
    except Exception as e:
        logger.error(f"✗ Risk scoring failed: {e}")
        results["risk_score"] = {"error": str(e)}
    
    # Display Results
    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE EXECUTION COMPLETE")
    logger.info("=" * 80)
    
    display_results(results)
    
    return results


def display_results(results: dict):
    """Display formatted pipeline results"""
    
    print("\n" + "=" * 80)
    print("GEOPOLITICAL RISK ANALYSIS - RESULTS")
    print("=" * 80)
    
    # Country Info
    print(f"\n📍 Country: {results['country']}")
    
    # Ingestion Summary
    print("\n📥 DATA INGESTION SUMMARY:")
    print("-" * 80)
    
    if "news" in results["ingestion"]:
        news = results["ingestion"]["news"]
        if "error" not in news:
            print(f"  • News Articles:        {news.get('stored', 0)} stored from {news.get('sources', 0)} sources")
        else:
            print(f"  • News Articles:        Failed - {news['error']}")
    
    if "gdelt" in results["ingestion"]:
        gdelt = results["ingestion"]["gdelt"]
        if "error" not in gdelt:
            print(f"  • Conflict Events:      {gdelt.get('stored', 0)} events stored")
        else:
            print(f"  • Conflict Events:      Failed - {gdelt['error']}")
    
    if "worldbank" in results["ingestion"]:
        wb = results["ingestion"]["worldbank"]
        if "error" not in wb:
            print(f"  • Economic Indicators:  {wb.get('total_stored', 0)} data points stored")
        else:
            print(f"  • Economic Indicators:  Failed - {wb['error']}")
    
    if "government" in results["ingestion"]:
        gov = results["ingestion"]["government"]
        if "error" not in gov:
            total = gov.get('total_documents', 0)
            by_source = gov.get('by_source', {})
            sources_str = ", ".join([f"{k}({v})" for k, v in by_source.items()])
            print(f"  • Government Reports:   {total} documents ({sources_str})")
        else:
            print(f"  • Government Reports:   Failed - {gov['error']}")
    
    # Risk Score
    if results["risk_score"] and "error" not in results["risk_score"]:
        risk = results["risk_score"]
        
        print("\n🎯 RISK ASSESSMENT:")
        print("-" * 80)
        print(f"  Overall Risk Score:     {risk['overall_score']:.2f} / 100")
        print(f"  Risk Level:             {risk['risk_level'].upper()}")
        print(f"  Trend:                  {risk.get('trend', 'N/A').upper()}")
        print(f"  Calculated At:          {risk.get('calculated_at', 'N/A')}")
        
        print("\n📊 SIGNAL BREAKDOWN:")
        print("-" * 80)
        signals = risk.get("signals", {})
        
        if "news" in signals:
            news_sig = signals["news"]
            method = news_sig.get('method', 'keyword')
            print(f"  • News Signal:          {news_sig['score']:.2f} / 100 (Weight: 20%) [{method.upper()}]")
            print(f"    - Articles analyzed:  {news_sig.get('article_count', 0)}")
            if 'mean_sentiment' in news_sig:
                print(f"    - Mean sentiment:     {news_sig.get('mean_sentiment', 0):.2f}")
            else:
                print(f"    - Negative mentions:  {news_sig.get('negative_count', 0)}")
        
        if "conflict" in signals:
            conf_sig = signals["conflict"]
            print(f"\n  • Conflict Signal:      {conf_sig['score']:.2f} / 100 (Weight: 40%)")
            print(f"    - Events recorded:    {conf_sig.get('event_count', 0)}")
            print(f"    - Total fatalities:   {conf_sig.get('total_fatalities', 0)}")
        
        if "economic" in signals:
            econ_sig = signals["economic"]
            print(f"\n  • Economic Signal:      {econ_sig['score']:.2f} / 100 (Weight: 30%)")
            print(f"    - GDP score:          {econ_sig.get('gdp_score', 0):.2f}")
            print(f"    - Inflation score:    {econ_sig.get('inflation_score', 0):.2f}")
            print(f"    - Unemployment score: {econ_sig.get('unemployment_score', 0):.2f}")
        
        if "government" in signals:
            gov_sig = signals["government"]
            method = gov_sig.get('method', 'none')
            print(f"\n  • Government Signal:    {gov_sig['score']:.2f} / 100 (Weight: 10%) [{method.upper()}]")
            reports = gov_sig.get('reports_analyzed', 0)
            if reports > 0:
                print(f"    - Reports analyzed:   {reports}")
                if 'mean_sentiment' in gov_sig:
                    print(f"    - Mean sentiment:     {gov_sig.get('mean_sentiment', 0):.2f}")
            else:
                print(f"    - Status:             {gov_sig.get('note', 'No data')}")
    
    else:
        print("\n🎯 RISK ASSESSMENT:")
        print("-" * 80)
        print(f"  ✗ Risk scoring failed: {results['risk_score'].get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print("\n💡 Next Steps:")
    print("  1. Start API server: python run_api.py")
    print("  2. Query risk score: GET http://localhost:8000/api/v1/risk-score/IND")
    print("  3. View all endpoints: GET http://localhost:8000/")
    print("=" * 80 + "\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Geopolitical Risk Analysis Pipeline")
    parser.add_argument(
        "--country",
        default="IND",
        help="ISO 3-letter country code (default: IND)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    try:
        results = run_full_pipeline(args.country)
        
        if args.json:
            print(json.dumps(results, indent=2, default=str))
    
    except KeyboardInterrupt:
        logger.info("\nPipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
