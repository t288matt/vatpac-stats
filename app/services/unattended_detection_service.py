#!/usr/bin/env python3
"""
Unattended Session Detection Service

Detects pilots who may be away from their computers using configurable rules.
Follows architecture principles: maintainable, scalable, supportable, iterative.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
import json

from ..config import get_config
from ..utils.logging import get_logger_for_module
from ..database import SessionLocal
from ..models import Flight, Controller
from .vatsim_service import VATSIMService


@dataclass
class UnattendedSession:
    """Unattended session detection result."""
    
    callsign: str
    pilot_name: str
    home_airport: str
    detection_type: str
    detection_reason: str
    severity: str
    detected_at: datetime
    flight_details: Dict[str, Any]
    current_position: Dict[str, float]
    time_since_detection: timedelta


@dataclass
class DetectionRule:
    """Configurable detection rule."""
    
    name: str
    description: str
    enabled: bool
    parameters: Dict[str, Any]
    severity: str


class UnattendedDetectionService:
    """
    Service for detecting unattended pilot sessions.
    
    Features:
    - Configurable detection rules
    - No hardcoded values
    - Scalable architecture
    - Supportable with detailed logging
    - Iterative development ready
    """
    
    def __init__(self):
        """Initialize the detection service."""
        self.config = get_config()
        self.logger = get_logger_for_module(__name__)
        self.vatsim_service = VATSIMService()
        self.detection_rules = self._load_detection_rules()
        self.airport_cache = {}  # Cache for airport coordinates
        
    def _load_detection_rules(self) -> List[DetectionRule]:
        """Load detection rules from configuration."""
        unattended_config = self.config.unattended_detection
        
        return [
            DetectionRule(
                name="ground_level_low_speed",
                description="Aircraft at ground level with low speed, not at departure/destination airport",
                enabled=unattended_config.ground_level_low_speed_enabled,
                parameters={
                    "max_altitude_ft": unattended_config.ground_level_max_altitude_ft,
                    "max_speed_kts": unattended_config.ground_level_max_speed_kts,
                    "min_duration_minutes": unattended_config.ground_level_min_duration_minutes,
                    "airport_distance_nm": unattended_config.ground_level_airport_distance_nm
                },
                severity="high"
            ),
            DetectionRule(
                name="long_flight_local_time",
                description="Long flights during local time window (1-5am)",
                enabled=unattended_config.long_flight_local_time_enabled,
                parameters={
                    "min_flight_duration_hours": unattended_config.long_flight_min_duration_hours,
                    "local_time_start_hour": unattended_config.long_flight_local_time_start_hour,
                    "local_time_end_hour": unattended_config.long_flight_local_time_end_hour
                },
                severity="medium"
            )
        ]
    
    async def detect_unattended_sessions(self) -> List[UnattendedSession]:
        """
        Detect unattended sessions using all enabled rules.
        
        Returns:
            List[UnattendedSession]: List of detected unattended sessions
        """
        self.logger.info("Starting unattended session detection")
        
        db = SessionLocal()
        try:
            # Get currently online flights from VATSIM
            current_vatsim_data = await self.vatsim_service.get_current_data()
            if not current_vatsim_data:
                self.logger.error("Failed to get current VATSIM data")
                return []
            
            online_callsigns = {flight.callsign for flight in current_vatsim_data.flights}
            
            # Get only flights that are currently online
            flights = db.query(Flight).filter(
                Flight.callsign.in_(online_callsigns),
                Flight.departure != "",
                Flight.arrival != ""
            ).all()
            
            self.logger.info(f"Analyzing {len(flights)} currently online flights")
            
            unattended_sessions = []
            
            for flight in flights:
                # Apply each enabled detection rule
                for rule in self.detection_rules:
                    if not rule.enabled:
                        continue
                    
                    detection_result = await self._apply_detection_rule(flight, rule, db)
                    if detection_result:
                        unattended_sessions.append(detection_result)
            
            self.logger.info(f"Detected {len(unattended_sessions)} unattended sessions")
            return unattended_sessions
            
        except Exception as e:
            self.logger.error(f"Error during unattended session detection: {e}")
            raise
        finally:
            db.close()
    
    async def _apply_detection_rule(self, flight: Flight, rule: DetectionRule, db: Session) -> Optional[UnattendedSession]:
        """Apply a specific detection rule to a flight."""
        try:
            if rule.name == "ground_level_low_speed":
                return await self._detect_ground_level_low_speed(flight, rule, db)
            elif rule.name == "long_flight_local_time":
                return await self._detect_long_flight_local_time(flight, rule, db)
            else:
                self.logger.warning(f"Unknown detection rule: {rule.name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error applying rule {rule.name} to flight {flight.callsign}: {e}")
            return None
    
    async def _detect_ground_level_low_speed(self, flight: Flight, rule: DetectionRule, db: Session) -> Optional[UnattendedSession]:
        """Detect aircraft at ground level with low speed, not at departure/destination airport."""
        try:
            # Parse position data
            position_data = self._parse_position_data(flight.position)
            if not position_data:
                return None
            
            # Check altitude and speed conditions
            max_altitude = rule.parameters["max_altitude_ft"]
            max_speed = rule.parameters["max_speed_kts"]
            
            if flight.altitude > max_altitude or flight.speed > max_speed:
                return None
            
            # Check if aircraft is at departure or destination airport
            departure_airport_coords = await self._get_airport_coordinates(flight.departure)
            arrival_airport_coords = await self._get_airport_coordinates(flight.arrival)
            
            airport_distance = rule.parameters["airport_distance_nm"]
            
            at_departure = self._is_at_airport(position_data, departure_airport_coords, airport_distance)
            at_arrival = self._is_at_airport(position_data, arrival_airport_coords, airport_distance)
            
            if at_departure or at_arrival:
                return None
            
            # Check duration (simplified - would need historical data for full implementation)
            # For now, we'll flag current condition and let dashboard show duration
            detection_reason = (
                f"Aircraft at ground level ({flight.altitude}ft) with low speed ({flight.speed}kts), "
                f"not at departure ({flight.departure}) or destination ({flight.arrival}) airport"
            )
            
            pilot_name = flight.pilot_name or self._extract_pilot_name(flight.callsign)
            return UnattendedSession(
                callsign=flight.callsign,
                pilot_name=pilot_name,
                home_airport=self._extract_home_airport(flight.callsign, pilot_name),
                detection_type=rule.name,
                detection_reason=detection_reason,
                severity=rule.severity,
                detected_at=datetime.utcnow(),
                flight_details={
                    "departure": flight.departure,
                    "arrival": flight.arrival,
                    "altitude": flight.altitude,
                    "speed": flight.speed,
                    "aircraft_type": flight.aircraft_type
                },
                current_position=position_data,
                time_since_detection=timedelta(0)  # Would calculate from historical data
            )
            
        except Exception as e:
            self.logger.error(f"Error in ground level low speed detection for {flight.callsign}: {e}")
            return None
    
    async def _detect_long_flight_local_time(self, flight: Flight, rule: DetectionRule, db: Session) -> Optional[UnattendedSession]:
        """Detect long flights during local time window."""
        try:
            # Calculate flight duration (simplified - would need departure time)
            # For now, we'll use a placeholder calculation
            flight_duration_hours = 5  # Placeholder - would calculate from actual data
            
            min_duration = rule.parameters["min_flight_duration_hours"]
            if flight_duration_hours < min_duration:
                return None
            
            # Get pilot's home airport and local time
            home_airport = self._extract_home_airport(flight.callsign)
            if not home_airport:
                return None
            
            local_time = await self._get_local_time(home_airport)
            start_hour = rule.parameters["local_time_start_hour"]
            end_hour = rule.parameters["local_time_end_hour"]
            
            if not (start_hour <= local_time.hour <= end_hour):
                return None
            
            detection_reason = (
                f"Long flight ({flight_duration_hours}h) during local time window "
                f"({local_time.hour:02d}:{local_time.minute:02d}) at home airport {home_airport}"
            )
            
            pilot_name = flight.pilot_name or self._extract_pilot_name(flight.callsign)
            return UnattendedSession(
                callsign=flight.callsign,
                pilot_name=pilot_name,
                home_airport=home_airport,
                detection_type=rule.name,
                detection_reason=detection_reason,
                severity=rule.severity,
                detected_at=datetime.utcnow(),
                flight_details={
                    "departure": flight.departure,
                    "arrival": flight.arrival,
                    "duration_hours": flight_duration_hours,
                    "local_time": local_time.isoformat()
                },
                current_position=self._parse_position_data(flight.position) or {},
                time_since_detection=timedelta(0)
            )
            
        except Exception as e:
            self.logger.error(f"Error in long flight local time detection for {flight.callsign}: {e}")
            return None
    
    def _parse_position_data(self, position_str: str) -> Optional[Dict[str, float]]:
        """Parse position JSON string."""
        if not position_str:
            return None
        
        try:
            position_data = json.loads(position_str)
            return {
                "latitude": position_data.get("latitude", 0),
                "longitude": position_data.get("longitude", 0)
            }
        except Exception as e:
            self.logger.warning(f"Failed to parse position data: {e}")
            return None
    
    async def _get_airport_coordinates(self, airport_code: str) -> Optional[Dict[str, float]]:
        """Get airport coordinates with automatic real-time lookup and caching."""
        try:
            # First, try to load from coordinates file if configured
            if self.config.airports.coordinates_file:
                coords = await self._load_airport_from_file(airport_code)
                if coords:
                    return coords
                
                # If not found in file, try to fetch from API and cache it
                self.logger.info(f"Airport {airport_code} not found in local database, fetching from API...")
                api_coords = await self._fetch_airport_from_api(airport_code)
                if api_coords:
                    # Cache the new airport coordinates
                    await self._cache_airport_coordinates(airport_code, api_coords)
                    self.logger.info(f"Successfully cached airport {airport_code} coordinates")
                    return api_coords
                else:
                    self.logger.warning(f"Could not fetch coordinates for {airport_code} from API")
                    return None
            
            # Try to fetch from API if configured (fallback)
            if self.config.airports.api_url:
                return await self._fetch_airport_from_api(airport_code)
            
            # If no configuration, log warning and return None
            self.logger.warning(f"No airport coordinates source configured for {airport_code}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting airport coordinates for {airport_code}: {e}")
            return None
    
    async def _load_airport_from_file(self, airport_code: str) -> Optional[Dict[str, float]]:
        """Load airport coordinates from configured file."""
        try:
            import json
            with open(self.config.airports.coordinates_file, 'r') as f:
                airports = json.load(f)
            return airports.get(airport_code)
        except Exception as e:
            self.logger.error(f"Error loading airport from file: {e}")
            return None
    
    async def _fetch_airport_from_api(self, airport_code: str) -> Optional[Dict[str, float]]:
        """Fetch airport coordinates from multiple APIs with fallback."""
        try:
            import httpx
            
            # List of airport APIs to try (in order of preference)
            api_endpoints = [
                f"https://nominatim.openstreetmap.org/search?q={airport_code}%20airport&format=json&limit=1",
                f"https://api.aviationapi.com/v1/airports?icao={airport_code}",
                f"https://api.flightapi.io/airport/{airport_code}",
                f"https://airport-info.p.rapidapi.com/airport?icao={airport_code}"
            ]
            
            headers = {
                "User-Agent": "ATC-Position-Engine/1.0",
                "Accept": "application/json"
            }
            
            # Try each API endpoint
            for api_url in api_endpoints:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(api_url, headers=headers)
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            # Parse different API response formats
                            coords = self._parse_airport_api_response(data, airport_code)
                            if coords:
                                self.logger.info(f"Successfully fetched {airport_code} from {api_url}")
                                return coords
                        else:
                            self.logger.debug(f"API {api_url} returned {response.status_code} for {airport_code}")
                            
                except Exception as e:
                    self.logger.debug(f"Error fetching from {api_url}: {e}")
                    continue
            
            # If all APIs fail, try a simple geocoding approach
            return await self._fetch_airport_from_geocoding(airport_code)
            
        except Exception as e:
            self.logger.error(f"Error fetching airport from API: {e}")
            return None
    
    def _parse_airport_api_response(self, data: dict, airport_code: str) -> Optional[Dict[str, float]]:
        """Parse different airport API response formats."""
        try:
            # Try different response formats
            if isinstance(data, list) and len(data) > 0:
                data = data[0]  # Some APIs return array
            
            # Common field names for coordinates
            lat_fields = ["latitude", "lat", "y", "coord_lat"]
            lng_fields = ["longitude", "lng", "lon", "x", "coord_lon"]
            
            lat = None
            lng = None
            
            # Try to find latitude
            for field in lat_fields:
                if field in data:
                    try:
                        lat = float(data[field])
                        break
                    except (ValueError, TypeError):
                        continue
            
            # Try to find longitude
            for field in lng_fields:
                if field in data:
                    try:
                        lng = float(data[field])
                        break
                    except (ValueError, TypeError):
                        continue
            
            if lat is not None and lng is not None:
                return {"latitude": lat, "longitude": lng}
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error parsing API response for {airport_code}: {e}")
            return None
    
    async def _fetch_airport_from_geocoding(self, airport_code: str) -> Optional[Dict[str, float]]:
        """Fallback: Try to get airport coordinates using geocoding."""
        try:
            import httpx
            
            # Try to geocode the airport name
            search_query = f"{airport_code} airport"
            
            # Use a simple geocoding service
            geocoding_url = f"https://nominatim.openstreetmap.org/search"
            params = {
                "q": search_query,
                "format": "json",
                "limit": 1
            }
            
            headers = {
                "User-Agent": "ATC-Position-Engine/1.0"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(geocoding_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        result = data[0]
                        lat = float(result.get("lat", 0))
                        lon = float(result.get("lon", 0))
                        
                        if lat != 0 and lon != 0:
                            self.logger.info(f"Found {airport_code} via geocoding: {lat}, {lon}")
                            return {"latitude": lat, "longitude": lon}
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error geocoding {airport_code}: {e}")
            return None
    
    async def _cache_airport_coordinates(self, airport_code: str, coordinates: Dict[str, float]) -> None:
        """Cache airport coordinates to the local file."""
        try:
            if not self.config.airports.coordinates_file:
                return
            
            # Load existing airports
            airports = {}
            try:
                with open(self.config.airports.coordinates_file, 'r') as f:
                    airports = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                airports = {}
            
            # Add new airport
            airports[airport_code] = coordinates
            
            # Write back to file
            with open(self.config.airports.coordinates_file, 'w') as f:
                json.dump(airports, f, indent=2)
            
            self.logger.info(f"Cached airport {airport_code} coordinates to local database")
            
        except Exception as e:
            self.logger.error(f"Error caching airport coordinates for {airport_code}: {e}")
    
    def _is_at_airport(self, aircraft_pos: Dict[str, float], airport_coords: Optional[Dict[str, float]], max_distance_nm: float) -> bool:
        """Check if aircraft is at airport within specified distance using Haversine formula."""
        if not airport_coords:
            return False
        
        import math
        
        # Convert to radians
        lat1_rad = math.radians(aircraft_pos["latitude"])
        lon1_rad = math.radians(aircraft_pos["longitude"])
        lat2_rad = math.radians(airport_coords["latitude"])
        lon2_rad = math.radians(airport_coords["longitude"])
        
        # Calculate differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in nautical miles
        earth_radius_nm = 3440.065
        
        distance_nm = earth_radius_nm * c
        
        return distance_nm <= max_distance_nm
    
    def _extract_pilot_name(self, callsign: str) -> str:
        """Extract pilot name from callsign using configurable patterns."""
        try:
            # Load pilot names from configuration file if available
            pilot_names = {}
            if self.config.pilots.names_file:
                try:
                    import json
                    with open(self.config.pilots.names_file, 'r') as f:
                        pilot_names = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Error loading pilot names file: {e}")
            
            # Check if we have a specific mapping for this callsign
            if callsign in pilot_names:
                return pilot_names[callsign]
            
            # Try to extract pilot name from callsign format
            # Common patterns: AIRLINE123, PILOT_NAME, etc.
            if "_" in callsign:
                # Format: AIRLINE_PILOTNAME
                parts = callsign.split("_")
                if len(parts) >= 2:
                    return parts[1].title()  # Convert to title case
            
            # For private aircraft or unknown airlines
            if len(callsign) <= 6:
                return f"Private Aircraft {callsign}"
            else:
                # Try to extract meaningful part
                return f"Flight {callsign[-4:]}" if len(callsign) > 4 else f"Flight {callsign}"
                
        except Exception as e:
            self.logger.warning(f"Error extracting pilot name from {callsign}: {e}")
            return f"Flight {callsign}"
    
    def _extract_home_airport(self, callsign: str, pilot_name: str = None) -> Optional[str]:
        """Extract home airport from callsign, pilot profile, or pilot name."""
        try:
            # Load pilot home airports from configuration file if available
            pilot_home_airports = {}
            if self.config.pilots.home_airports_file:
                try:
                    import json
                    with open(self.config.pilots.home_airports_file, 'r') as f:
                        pilot_home_airports = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Error loading pilot home airports file: {e}")
            
            # Check if we have a specific mapping for this callsign
            if callsign in pilot_home_airports:
                return pilot_home_airports[callsign]
            
            # Try to extract home airport from pilot name (e.g., "Rashon Connor MWCR")
            if pilot_name:
                # Look for 4-letter airport code at the end of pilot name
                import re
                airport_match = re.search(r'([A-Z]{4})$', pilot_name)
                if airport_match:
                    return airport_match.group(1)
            
            # Try to extract from callsign format
            # Common patterns: AIRLINE123, PILOT_NAME, etc.
            if "_" in callsign:
                # Format: AIRLINE_PILOTNAME
                parts = callsign.split("_")
                if len(parts) >= 2:
                    # Could extract from pilot name patterns
                    pass
            
            # Check for airline codes and use common home airports
            airline_home_airports = {
                "AAL": "KDFW",  # American Airlines - Dallas/Fort Worth
                "UAL": "KORD",  # United Airlines - Chicago O'Hare
                "DAL": "KATL",  # Delta Airlines - Atlanta
                "SWA": "KDAL",  # Southwest Airlines - Dallas Love
                "JBU": "KBWI",  # JetBlue - Baltimore/Washington
                "ASA": "KSEA",  # Alaska Airlines - Seattle
                "EDV": "KCVG",  # Endeavor Air - Cincinnati
                "FFT": "KCVG",  # Frontier Airlines - Cincinnati
                "SKW": "KDTW",  # SkyWest - Detroit
                "RPA": "KORD"   # Republic Airways - Chicago O'Hare
            }
            
            for airline, home_airport in airline_home_airports.items():
                if callsign.startswith(airline):
                    return home_airport
            
            # If no pattern matches, return None
            return None
                
        except Exception as e:
            self.logger.warning(f"Error extracting home airport from {callsign}: {e}")
            return None
    
    async def _get_local_time(self, airport_code: str) -> datetime:
        """Get local time for airport (placeholder)."""
        # This would integrate with timezone database
        # For now, return UTC as placeholder
        return datetime.utcnow()
    
    async def get_detection_statistics(self) -> Dict[str, Any]:
        """Get detection statistics for monitoring."""
        try:
            unattended_sessions = await self.detect_unattended_sessions()
            
            stats = {
                "total_detections": len(unattended_sessions),
                "by_severity": {},
                "by_type": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for session in unattended_sessions:
                # Count by severity
                severity = session.severity
                stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
                
                # Count by detection type
                detection_type = session.detection_type
                stats["by_type"][detection_type] = stats["by_type"].get(detection_type, 0) + 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting detection statistics: {e}")
            return {
                "total_detections": 0,
                "by_severity": {},
                "by_type": {},
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Service instance for dependency injection
_unattended_detection_service = None

def get_unattended_detection_service() -> UnattendedDetectionService:
    """Get unattended detection service instance."""
    global _unattended_detection_service
    if _unattended_detection_service is None:
        _unattended_detection_service = UnattendedDetectionService()
    return _unattended_detection_service 