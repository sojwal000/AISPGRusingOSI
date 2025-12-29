"""
GDELT 2.0 Event Database Integration
Real-time global conflict and political event data ingestion

GDELT provides:
- 300+ event categories (CAMEO codes)
- Real-time updates (15-minute intervals)
- Global coverage with geo-coordinates
- Actor identification
- Goldstein scale (-10 to +10 for impact)
- Free access, no API key required

Data source: http://data.gdeltproject.org/events/index.html
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import zipfile
import io
import csv
from app.core.database import SessionLocal
from app.models.sql_models import ConflictEvent
from app.core.logging import setup_logger

logger = setup_logger(__name__)


class GDELTIngestion:
    """
    Ingest conflict and political event data from GDELT 2.0 Event Database.
    
    GDELT publishes event data every 15 minutes in CSV format.
    Each file contains global events from that time period.
    """
    
    # GDELT base URL for event files
    BASE_URL = "http://data.gdeltproject.org/gdeltv2"
    
    # India country code in FIPS (used by GDELT)
    # Note: GDELT uses FIPS codes, not ISO-3166
    INDIA_FIPS_CODE = "IN"
    
    # CAMEO event codes mapping to conflict types
    # GDELT uses CAMEO codes: https://www.gdeltproject.org/data/documentation/CAMEO.Manual.1.1b3.pdf
    EVENT_TYPE_MAP = {
        # Violence
        "18": "Violence against civilians",  # Assault
        "19": "Battles",  # Fight
        "20": "Violence against civilians",  # Unconventional violence
        
        # Protests
        "14": "Protests",  # Protest
        
        # Coercion
        "15": "Strategic developments",  # Exhibit military posture
        "16": "Strategic developments",  # Reduce relations
        "17": "Strategic developments",  # Coerce
        
        # Riots
        "145": "Riots",  # Violent protest
    }
    
    def __init__(self):
        """Initialize GDELT ingestion"""
        self.db = SessionLocal()
        logger.info("GDELT ingestion initialized")
    
    def get_recent_events(self, hours_back: int = 24, country_focus: str = "IND") -> List[Dict]:
        """
        Fetch recent events from GDELT for specified country.
        
        Args:
            hours_back: How many hours of data to fetch (default 24)
            country_focus: Country to focus on (ISO-3 code, default IND)
        
        Returns:
            List of parsed event dictionaries
        """
        logger.info(f"Fetching GDELT events from last {hours_back} hours for {country_focus}")
        
        try:
            # GDELT publishes files every 15 minutes
            # File naming: YYYYMMDDHHMMSS.export.CSV.zip
            # We'll fetch files from the last N hours
            
            events = []
            now = datetime.utcnow()
            
            # Calculate how many 15-minute intervals to fetch
            intervals = (hours_back * 60) // 15
            
            for i in range(intervals):
                # Go back in 15-minute increments
                timestamp = now - timedelta(minutes=15 * i)
                
                # Round down to nearest 15-minute mark
                minute = (timestamp.minute // 15) * 15
                file_timestamp = timestamp.replace(minute=minute, second=0, microsecond=0)
                
                # Format: YYYYMMDDHHMMSS
                filename = file_timestamp.strftime("%Y%m%d%H%M%S") + ".export.CSV.zip"
                url = f"{self.BASE_URL}/{filename}"
                
                try:
                    # Fetch and parse this interval
                    interval_events = self._fetch_and_parse_file(url, country_focus)
                    events.extend(interval_events)
                    
                    if interval_events:
                        logger.info(f"Fetched {len(interval_events)} events from {filename}")
                
                except Exception as e:
                    # File might not exist yet (future time) or be missing
                    logger.debug(f"Could not fetch {filename}: {e}")
                    continue
            
            logger.info(f"Total GDELT events fetched: {len(events)}")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching GDELT events: {e}")
            return []
    
    def _fetch_and_parse_file(self, url: str, country_focus: str) -> List[Dict]:
        """
        Download and parse a single GDELT CSV file.
        
        Args:
            url: URL of the .zip file
            country_focus: Country to filter for
        
        Returns:
            List of parsed events
        """
        try:
            # Download ZIP file
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract CSV from ZIP
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # ZIP contains one CSV file
                csv_filename = zip_file.namelist()[0]
                csv_data = zip_file.read(csv_filename).decode('utf-8')
            
            # Parse CSV
            events = self._parse_csv(csv_data, country_focus)
            return events
            
        except requests.RequestException as e:
            logger.debug(f"Request error for {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return []
    
    def _parse_csv(self, csv_data: str, country_focus: str) -> List[Dict]:
        """
        Parse GDELT CSV and extract relevant events.
        
        GDELT CSV columns (58 total, key ones):
        0: GLOBALEVENTID
        1: SQLDATE (YYYYMMDD)
        27: EventCode (CAMEO)
        28: EventBaseCode
        29: EventRootCode
        30: QuadClass (1=Verbal Cooperation, 2=Material Cooperation, 3=Verbal Conflict, 4=Material Conflict)
        31: GoldsteinScale (-10 to +10)
        32: NumMentions
        33: NumSources
        34: NumArticles
        35: AvgTone (-100 to +100)
        53: Actor1CountryCode
        54: Actor2CountryCode
        55: ActionGeo_CountryCode
        56: ActionGeo_Lat
        57: ActionGeo_Long
        """
        events = []
        
        try:
            reader = csv.reader(io.StringIO(csv_data), delimiter='\t')
            
            for row in reader:
                if len(row) < 58:
                    continue
                
                # Check if event is related to target country
                actor1_country = row[53] if len(row) > 53 else ""
                actor2_country = row[54] if len(row) > 54 else ""
                location_country = row[55] if len(row) > 55 else ""
                
                # Convert country_focus from ISO-3 to FIPS (simple mapping)
                target_code = self._iso_to_fips(country_focus)
                
                # Event must involve target country as actor or location
                if not any([
                    actor1_country == target_code,
                    actor2_country == target_code,
                    location_country == target_code
                ]):
                    continue
                
                # Extract event details
                event_id = row[0]
                sql_date = row[1]  # YYYYMMDD
                event_code = row[27]
                event_root_code = row[29]
                quad_class = int(float(row[30])) if row[30] else 0  # Convert float to int
                goldstein_scale = float(row[31]) if row[31] else 0.0
                num_mentions = int(float(row[32])) if row[32] else 0  # Convert float to int
                avg_tone = float(row[35]) if row[35] else 0.0
                
                # Only process conflict events (QuadClass 3 or 4)
                if quad_class not in [3, 4]:  # 3=Verbal Conflict, 4=Material Conflict
                    continue
                
                # Only process significant events (Goldstein < -3 or multiple mentions)
                if goldstein_scale > -3.0 and num_mentions < 5:
                    continue
                
                # Parse date
                event_date = datetime.strptime(sql_date, "%Y%m%d")
                
                # Determine event type
                event_type = self._map_event_type(event_root_code)
                
                # Parse location
                lat = float(row[56]) if len(row) > 56 and row[56] else None
                lon = float(row[57]) if len(row) > 57 and row[57] else None
                
                # Get actors (names are in columns 6-7, codes in 15-16)
                actor1_name = row[6] if len(row) > 6 else ""
                actor2_name = row[7] if len(row) > 7 else ""
                
                events.append({
                    "external_id": f"GDELT_{event_id}",
                    "country_code": country_focus,
                    "event_date": event_date,
                    "event_type": event_type,
                    "sub_event_type": f"CAMEO_{event_code}",
                    "actor1": actor1_name[:200] if actor1_name else None,
                    "actor2": actor2_name[:200] if actor2_name else None,
                    "location": location_country,
                    "latitude": lat,
                    "longitude": lon,
                    "fatalities": self._estimate_fatalities(goldstein_scale, event_code),
                    "notes": f"Goldstein: {goldstein_scale}, Tone: {avg_tone}, Mentions: {num_mentions}",
                    "source": "GDELT"
                })
        
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
        
        return events
    
    def _iso_to_fips(self, iso_code: str) -> str:
        """Convert ISO-3166 country code to FIPS (simple mapping for India)"""
        mapping = {
            "IND": "IN",
            "PAK": "PK",
            "CHN": "CH",
            "BGD": "BG",
            # Add more as needed
        }
        return mapping.get(iso_code, iso_code[:2])
    
    def _map_event_type(self, cameo_root: str) -> str:
        """Map CAMEO root code to our event types"""
        
        # CAMEO root codes
        cameo_map = {
            "14": "Protests",
            "15": "Strategic developments",
            "16": "Strategic developments",
            "17": "Strategic developments",
            "18": "Violence against civilians",
            "19": "Battles",
            "20": "Violence against civilians"
        }
        
        return cameo_map.get(cameo_root, "Other conflict")
    
    def _estimate_fatalities(self, goldstein: float, event_code: str) -> int:
        """
        Estimate fatalities based on Goldstein scale and event type.
        GDELT doesn't provide fatality counts, so we estimate.
        """
        # Very rough estimation
        # Goldstein scale: -10 (most negative) to +10 (most positive)
        
        if goldstein >= -3:
            return 0  # Minor event
        elif goldstein >= -5:
            return 1  # Low intensity
        elif goldstein >= -7:
            return 5  # Medium intensity
        elif goldstein >= -9:
            return 10  # High intensity
        else:
            return 20  # Very high intensity
    
    def store_events(self, events: List[Dict]) -> int:
        """
        Store GDELT events in database.
        
        Args:
            events: List of parsed event dictionaries
        
        Returns:
            Number of events stored (excluding duplicates)
        """
        stored_count = 0
        
        try:
            for event_data in events:
                # Check for duplicate
                existing = self.db.query(ConflictEvent).filter(
                    ConflictEvent.external_id == event_data["external_id"]
                ).first()
                
                if existing:
                    continue
                
                # Create new event
                event = ConflictEvent(**event_data)
                self.db.add(event)
                stored_count += 1
            
            self.db.commit()
            logger.info(f"Stored {stored_count} new GDELT events")
            
        except Exception as e:
            logger.error(f"Error storing events: {e}")
            self.db.rollback()
        
        return stored_count
    
    def ingest(self, hours_back: int = 24, country_code: str = "IND") -> Dict:
        """
        Complete ingestion workflow: fetch → parse → store.
        
        Args:
            hours_back: Hours of data to fetch
            country_code: Country to focus on (ISO-3)
        
        Returns:
            Summary dictionary
        """
        logger.info(f"Starting GDELT ingestion for {country_code} ({hours_back}h)")
        
        try:
            # Fetch events
            events = self.get_recent_events(hours_back=hours_back, country_focus=country_code)
            
            if not events:
                logger.warning("No GDELT events fetched")
                return {
                    "status": "success",
                    "events_fetched": 0,
                    "events_stored": 0,
                    "message": "No events found in time range"
                }
            
            # Store events
            stored = self.store_events(events)
            
            return {
                "status": "success",
                "events_fetched": len(events),
                "events_stored": stored,
                "hours_back": hours_back,
                "country_code": country_code
            }
            
        except Exception as e:
            logger.error(f"GDELT ingestion failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            self.db.close()


if __name__ == "__main__":
    # Test ingestion
    ingestion = GDELTIngestion()
    result = ingestion.ingest(hours_back=24, country_code="IND")
    print(f"GDELT Ingestion Result: {result}")
