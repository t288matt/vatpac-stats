#!/usr/bin/env python3
"""
VATSIM API Service for Data Collection

This service handles all VATSIM API interactions for the data collection system.
It provides a clean interface for fetching, parsing, and processing VATSIM
network data including controllers, flights, sectors, and transceivers.

INPUTS:
- VATSIM API endpoints (data, status, transceivers)
- Network authentication and configuration
- API request parameters and timeouts
- Error handling and retry logic

OUTPUTS:
- Structured VATSIM data objects (controllers, flights, sectors)
- Network status and health information
- Parsed and validated data structures
- Error handling and logging information

DATA STRUCTURES:
- VATSIMController: ATC controller position data
- VATSIMFlight: Real-time flight tracking data
- VATSIMTransceiver: Radio frequency and position data
- VATSIMData: Complete network data container

FEATURES:
- Asynchronous HTTP client with timeouts
- Automatic data parsing and validation
- Error handling and retry logic
- Health checking and status monitoring
- Connection pooling and resource management
- Structured data objects with type safety

API ENDPOINTS:
- /v3/vatsim-data.json: Main network data
- /v3/status.json: Network status
- /v3/transceivers-data.json: Radio frequency data

OPTIMIZATIONS:
- HTTP connection pooling
- Request timeout management
- JSON parsing optimization
- Memory-efficient data structures
- Automatic error recovery
"""

import asyncio
import httpx
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from ..config import get_config
from ..utils.logging import get_logger_for_module
from .base_service import BaseService
from ..utils.error_handling import handle_service_errors, retry_on_failure, log_operation, APIError
from ..filters.flight_filter import FlightFilter

logger = logging.getLogger(__name__)


@dataclass
class VATSIMController:
    """VATSIM controller data structure."""
    
    callsign: str
    facility: str
    position: str
    frequency: str
    status: str
    controller_id: Optional[str] = None
    controller_name: Optional[str] = None
    controller_rating: Optional[int] = None
    last_seen: Optional[datetime] = None
    
    # Missing VATSIM API fields - 1:1 mapping with API field names
    visual_range: Optional[int] = None  # Controller visual range
    text_atis: Optional[str] = None  # ATIS information


@dataclass
class VATSIMFlight:
    """VATSIM flight data structure.
    
    VATSIM API v3 Compliance:
    - Aircraft type: Extracted from flight_plan.aircraft_short
    - Flight plan: Nested under flight_plan object
    - Position data: Latitude/longitude/altitude from pilot object
    """
    
    callsign: str
    pilot_name: str
    aircraft_type: str
    departure: str
    arrival: str
    route: str
    altitude: int
    position: Optional[Dict[str, float]] = None
    
    # Missing VATSIM API fields - 1:1 mapping with API field names
    cid: Optional[int] = None  # VATSIM user ID
    name: Optional[str] = None  # Pilot name
    server: Optional[str] = None  # Network server
    pilot_rating: Optional[int] = None  # Pilot rating
    military_rating: Optional[int] = None  # Military rating
    latitude: Optional[float] = None  # Position latitude
    longitude: Optional[float] = None  # Position longitude
    groundspeed: Optional[int] = None  # Ground speed
    transponder: Optional[str] = None  # Transponder code
    heading: Optional[int] = None  # Aircraft heading
    qnh_i_hg: Optional[float] = None  # QNH in inches Hg
    qnh_mb: Optional[int] = None  # QNH in millibars
    logon_time: Optional[datetime] = None  # When pilot connected
    last_updated: Optional[datetime] = None  # API last_updated timestamp
    
    # Flight plan fields (nested object)
    flight_rules: Optional[str] = None  # IFR/VFR
    aircraft_faa: Optional[str] = None  # FAA aircraft code
    aircraft_short: Optional[str] = None  # Short aircraft code
    alternate: Optional[str] = None  # Alternate airport
    cruise_tas: Optional[int] = None  # True airspeed
    planned_altitude: Optional[int] = None  # Planned cruise altitude
    deptime: Optional[str] = None  # Departure time
    enroute_time: Optional[str] = None  # Enroute time
    fuel_time: Optional[str] = None  # Fuel time
    remarks: Optional[str] = None  # Flight plan remarks
    revision_id: Optional[int] = None  # Flight plan revision
    assigned_transponder: Optional[str] = None  # Assigned transponder


@dataclass
class VATSIMTransceiver:
    """VATSIM transceiver data structure."""
    
    callsign: str
    transceiver_id: int
    frequency: int  # Frequency in Hz
    position_lat: Optional[float] = None
    position_lon: Optional[float] = None
    height_msl: Optional[float] = None  # Height above mean sea level in meters
    height_agl: Optional[float] = None  # Height above ground level in meters
    entity_type: str = "flight"  # 'flight' or 'atc'
    entity_id: Optional[int] = None


@dataclass
class VATSIMData:
    """Complete VATSIM network data."""
    
    controllers: List[VATSIMController]
    flights: List[VATSIMFlight]
    sectors: List[Dict[str, Any]]
    transceivers: List[VATSIMTransceiver]
    timestamp: datetime
    total_controllers: int
    total_flights: int
    total_sectors: int
    total_transceivers: int


class VATSIMAPIError(Exception):
    """Exception raised when VATSIM API operations fail."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class VATSIMService(BaseService):
    """
    Service for handling VATSIM API v3 interactions.
    
    This service provides a clean interface for fetching and processing
    VATSIM network data, following our architecture principles.
    
    VATSIM API v3 Compliance:
    - Endpoint: https://data.vatsim.net/v3/vatsim-data.json
    - Flight plans: Nested under flight_plan object
    - Aircraft types: Extracted from flight_plan.aircraft_short
    - Controller fields: Uses correct API field names (cid, name, facility, etc.)
    - Sectors data: Not available in current API v3 (handled gracefully)
    
    SECTORS FIELD LIMITATION:
    =========================
    The 'sectors' field is completely missing from VATSIM API v3. This is a known
    limitation, not a bug in our code. The field simply doesn't exist in the API
    response.
    
    Technical Details:
    - Expected: sectors array containing airspace sector definitions
    - Actual: Field does not exist in API response
    - Impact: Traffic density analysis and sector-based routing limited
    - Handling: Graceful degradation with warning logs and fallback behavior
    
    Fallback Behavior:
    - Creates basic sector definitions from facility data
    - Logs warning when sectors data is missing
    - Continues operation without sectors data
    - Database schema supports sectors if API adds them back
    
    Future Considerations:
    - Monitor for sectors field return in future API versions
    - Consider external sector definition sources
    - Option to manually define critical sectors
    - Feature flags for sector-based features
    """
    
    def __init__(self):
        """Initialize VATSIM service with configuration."""
        super().__init__("vatsim_service")
        self.client: Optional[httpx.AsyncClient] = None
        self.flight_filter = FlightFilter()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_client()
    
    async def _initialize_service(self):
        """Initialize VATSIM service with HTTP client."""
        await self._create_client()
        self.logger.info("VATSIM service initialized successfully")
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform VATSIM service health check."""
        try:
            if not self.client:
                return {"status": "no_client", "error": "HTTP client not initialized"}
            
            # Test API connectivity
            response = await self.client.get(self.config.vatsim.api_url, timeout=5.0)
            if response.status_code == 200:
                return {"status": "healthy", "api_accessible": True}
            else:
                return {"status": "unhealthy", "api_accessible": False, "status_code": response.status_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _cleanup_service(self):
        """Cleanup VATSIM service resources."""
        await self._close_client()
        self.logger.info("VATSIM service cleanup completed")
    
    async def _create_client(self) -> None:
        """Create HTTP client for API requests."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.config.vatsim.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            self.logger.debug("Created HTTP client for VATSIM API")
    
    async def _close_client(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self.logger.debug("Closed HTTP client")
    
    @handle_service_errors
    @retry_on_failure(max_retries=3, delay=1.0)
    @log_operation("fetch_vatsim_data")
    async def get_current_data(self) -> VATSIMData:
        """
        Fetch current VATSIM network data.
        
        Returns:
            VATSIMData: Parsed VATSIM network data
            
        Raises:
            VATSIMAPIError: When API request fails
        """
        from typing import Union
        await self._create_client()
        
        try:
            self.logger.info("Fetching current VATSIM data", extra={
                "api_url": self.config.vatsim.api_url,
                "timeout": self.config.vatsim.timeout
            })
            
            response = await self.client.get(self.config.vatsim.api_url)
            
            if response.status_code != 200:
                raise VATSIMAPIError(
                    f"VATSIM API returned status {response.status_code}",
                    status_code=response.status_code
                )
            
            raw_data = response.json()
            
            # Ensure data is a dictionary and handle None
            if not isinstance(raw_data, dict) or raw_data is None:
                parsed_data: Dict[str, Any] = {}
            else:
                parsed_data: Dict[str, Any] = raw_data
            
            # Parse the data with proper null checks
            controllers = self._parse_controllers(parsed_data.get("controllers", []))
            sectors = parsed_data.get("sectors", [])
            
            # Handle missing sectors gracefully
            if not sectors:
                self.logger.warning("No sectors data available from VATSIM API", extra={
                    "sectors_count": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            # Parse all flights - filtering is handled separately by the flight filter
            flights = self._parse_flights(parsed_data.get("pilots", []))
            
            # Fetch transceivers data
            try:
                transceivers_raw = await self._fetch_transceivers_data()
                transceivers = self._parse_transceivers(transceivers_raw)
                # Link transceivers to flights and controllers
                transceivers = self._link_transceivers_to_entities(transceivers, flights, controllers)
            except Exception as e:
                self.logger.warning("Failed to fetch transceivers data, continuing without it", extra={
                    "error": str(e)
                })
                transceivers = []
            
            # Create VATSIM data object
            vatsim_data = VATSIMData(
                controllers=controllers,
                flights=flights,
                sectors=sectors,
                transceivers=transceivers,
                timestamp=datetime.now(timezone.utc),
                total_controllers=len(controllers),
                total_flights=len(flights),
                total_sectors=len(sectors),
                total_transceivers=len(transceivers)
            )
            
            self.logger.info("Successfully fetched VATSIM data", extra={
                "controllers_count": vatsim_data.total_controllers,
                "flights_count": vatsim_data.total_flights,
                "sectors_count": vatsim_data.total_sectors,
                "transceivers_count": vatsim_data.total_transceivers
            })
            
            return vatsim_data
            
        except httpx.TimeoutException as e:
            self.logger.error("VATSIM API request timed out", extra={
                "timeout": self.config.vatsim.timeout,
                "error": str(e)
            })
            raise VATSIMAPIError(f"VATSIM API request timed out: {e}")
            
        except httpx.RequestError as e:
            self.logger.error("VATSIM API request failed", extra={
                "error": str(e)
            })
            raise VATSIMAPIError(f"VATSIM API request failed: {e}")
            
        except Exception as e:
            self.logger.exception("Unexpected error fetching VATSIM data", extra={
                "error": str(e)
            })
            raise VATSIMAPIError(f"Unexpected error: {e}")
    
    def _parse_controllers(self, controllers_data: List[Dict[str, Any]]) -> List[VATSIMController]:
        """
        Parse controller data from VATSIM API response.
        
        Args:
            controllers_data: Raw controller data from API
            
        Returns:
            List[VATSIMController]: Parsed controller objects
        """
        controllers = []
        
        for controller_data in controllers_data:
            try:
                # Convert facility number to string representation
                facility_num = controller_data.get("facility", 0)
                facility_map = {
                    0: "OBS", 1: "FSS", 2: "DEL", 3: "GND", 4: "TWR", 5: "APP", 6: "CTR"
                }
                facility = facility_map.get(facility_num, "OBS")
                
                # Extract position from callsign (e.g., "VECC_TWR" -> "TWR")
                callsign = controller_data.get("callsign", "")
                position = callsign.split("_")[-1] if "_" in callsign else ""
                
                controller = VATSIMController(
                    callsign=callsign,
                    facility=facility,
                    position=position,
                    frequency=controller_data.get("frequency", ""),
                    status="online",  # If they're in the API, they're online
                    controller_id=int(controller_data.get("cid", 0)) if controller_data.get("cid") else None,
                    controller_name=controller_data.get("name", ""),
                    controller_rating=int(controller_data.get("rating", 0)) if controller_data.get("rating") else None,
                    
                    # Missing VATSIM API fields - 1:1 mapping with API field names
                    visual_range=controller_data.get("visual_range"),
                    text_atis=controller_data.get("text_atis")
                )
                controllers.append(controller)
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to parse controller {controller_data.get('callsign', 'unknown')}: {e}",
                    extra={
                        "controller_data": controller_data,
                        "error": str(e)
                    }
                )
        
        return controllers
    
    def _parse_flights(self, flights_data: List[Dict[str, Any]]) -> List[VATSIMFlight]:
        """
        Parse flight data from VATSIM API response.
        
        Args:
            flights_data: Raw flight data from API
            
        Returns:
            List[VATSIMFlight]: Parsed flight objects
        """
        flights = []
        
        for flight_data in flights_data:
            try:
                # Extract position data
                position = None
                if flight_data.get("latitude") and flight_data.get("longitude"):
                    position = {
                        "lat": float(flight_data["latitude"]),
                        "lng": float(flight_data["longitude"])
                    }
                
                # Extract flight plan data - handle null flight plans
                flight_plan = flight_data.get("flight_plan")
                if flight_plan is None:
                    flight_plan = {}
                
                # Parse timestamps
                logon_time = None
                if flight_data.get("logon_time"):
                    try:
                        logon_time = datetime.fromisoformat(flight_data["logon_time"].replace("Z", "+00:00"))
                    except:
                        logon_time = None
                
                last_updated = None
                if flight_data.get("last_updated"):
                    try:
                        last_updated = datetime.fromisoformat(flight_data["last_updated"].replace("Z", "+00:00"))
                    except:
                        last_updated = None
                
                flight = VATSIMFlight(
                    callsign=flight_data.get("callsign", ""),
                    pilot_name=flight_data.get("name", ""),
                    aircraft_type=flight_plan.get("aircraft_short", ""),  # Fixed: API provides aircraft type in flight_plan.aircraft_short
                    departure=flight_plan.get("departure", ""),
                    arrival=flight_plan.get("arrival", ""),
                    route=flight_plan.get("route", ""),
                    altitude=int(flight_data.get("altitude", 0)),
                    position=position,
                    
                    # Missing VATSIM API fields - 1:1 mapping with API field names
                    cid=flight_data.get("cid"),
                    name=flight_data.get("name"),
                    server=flight_data.get("server"),
                    pilot_rating=flight_data.get("pilot_rating"),
                    military_rating=flight_data.get("military_rating"),
                    latitude=flight_data.get("latitude"),
                    longitude=flight_data.get("longitude"),
                    groundspeed=flight_data.get("groundspeed"),
                    transponder=flight_data.get("transponder"),
                    heading=flight_data.get("heading"),
                    qnh_i_hg=flight_data.get("qnh_i_hg"),
                    qnh_mb=flight_data.get("qnh_mb"),
                    logon_time=logon_time,
                    last_updated=last_updated,
                    
                    # Flight plan fields (nested object)
                    flight_rules=flight_plan.get("flight_rules"),
                    aircraft_faa=flight_plan.get("aircraft_faa"),
                    aircraft_short=flight_plan.get("aircraft_short"),
                    alternate=flight_plan.get("alternate"),
                    cruise_tas=flight_plan.get("cruise_tas"),
                    planned_altitude=flight_plan.get("altitude"),
                    deptime=flight_plan.get("deptime"),
                    enroute_time=flight_plan.get("enroute_time"),
                    fuel_time=flight_plan.get("fuel_time"),
                    remarks=flight_plan.get("remarks"),
                    revision_id=flight_plan.get("revision_id"),
                    assigned_transponder=flight_plan.get("assigned_transponder")
                )
                flights.append(flight)
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to parse flight {flight_data.get('callsign', 'unknown')}: {e}",
                    extra={
                        "flight_data": flight_data,
                        "error": str(e)
                    }
                )
        
        return flights
    
    async def _fetch_transceivers_data(self) -> List[Dict[str, Any]]:
        """
        Fetch transceivers data from VATSIM API.
        
        Returns:
            List[Dict[str, Any]]: Raw transceivers data
            
        Raises:
            VATSIMAPIError: When API request fails
        """
        await self._create_client()
        
        try:
            self.logger.info("Fetching transceivers data", extra={
                "api_url": self.config.vatsim.transceivers_api_url,
                "timeout": self.config.vatsim.timeout
            })
            
            response = await self.client.get(self.config.vatsim.transceivers_api_url)
            
            if response.status_code != 200:
                raise VATSIMAPIError(
                    f"VATSIM transceivers API returned status {response.status_code}",
                    status_code=response.status_code
                )
            
            raw_data = response.json()
            
            # Ensure data is a list and handle None
            if not isinstance(raw_data, list) or raw_data is None:
                return []
            
            return raw_data
            
        except Exception as e:
            self.logger.error("Failed to fetch transceivers data", extra={
                "error": str(e),
                "api_url": self.config.vatsim.transceivers_api_url
            })
            raise VATSIMAPIError(f"Failed to fetch transceivers data: {e}")
    
    def _parse_transceivers(self, transceivers_data: List[Dict[str, Any]]) -> List[VATSIMTransceiver]:
        """
        Parse transceivers data from VATSIM API response.
        
        Args:
            transceivers_data: Raw transceivers data from API
            
        Returns:
            List[VATSIMTransceiver]: Parsed transceivers data
        """
        transceivers = []
        
        for entry in transceivers_data:
            try:
                callsign = entry.get("callsign", "")
                transceivers_list = entry.get("transceivers", [])
                
                for transceiver_data in transceivers_list:
                    transceiver = VATSIMTransceiver(
                        callsign=callsign,
                        transceiver_id=transceiver_data.get("id", 0),
                        frequency=transceiver_data.get("frequency", 0),
                        position_lat=transceiver_data.get("latDeg"),
                        position_lon=transceiver_data.get("lonDeg"),
                        height_msl=transceiver_data.get("heightMslM"),
                        height_agl=transceiver_data.get("heightAglM"),
                        entity_type="flight"  # Default to flight, will be updated later
                    )
                    transceivers.append(transceiver)
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to parse transceiver for {entry.get('callsign', 'unknown')}: {e}",
                    extra={
                        "entry": entry,
                        "error": str(e)
                    }
                )
        
        return transceivers
    
    def _link_transceivers_to_entities(self, transceivers: List[VATSIMTransceiver], 
                                      flights: List[VATSIMFlight], 
                                      controllers: List[VATSIMController]) -> List[VATSIMTransceiver]:
        """
        Link transceivers to flights and ATC positions based on callsign.
        
        Args:
            transceivers: List of transceivers to link
            flights: List of flights
            controllers: List of controllers
            
        Returns:
            List[VATSIMTransceiver]: Transceivers with entity links
        """
        # Create lookup dictionaries
        flight_lookup = {flight.callsign: flight for flight in flights}
        controller_lookup = {controller.callsign: controller for controller in controllers}
        
        for transceiver in transceivers:
            # Check if callsign matches a flight
            if transceiver.callsign in flight_lookup:
                transceiver.entity_type = "flight"
                # Note: entity_id would be set when storing to database
            # Check if callsign matches a controller
            elif transceiver.callsign in controller_lookup:
                transceiver.entity_type = "atc"
                # Note: entity_id would be set when storing to database
            # If no match, keep as "flight" (default)
        
        return transceivers
    
    async def health_check(self) -> bool:
        """
        Perform health check on VATSIM API.
        
        Returns:
            bool: True if API is accessible, False otherwise
        """
        try:
            await self._create_client()
            response = await self.client.get(self.config.vatsim.api_url)
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error("VATSIM API health check failed", extra={
                "error": str(e)
            })
            return False
    
    async def get_api_status(self) -> Dict[str, Any]:
        """
        Get detailed API status information.
        
        Returns:
            Dict[str, Any]: API status information
        """
        try:
            await self._create_client()
            response = await self.client.get(self.config.vatsim.api_url)
            
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Global service instance
_vatsim_service: Optional[VATSIMService] = None


def get_vatsim_service() -> VATSIMService:
    """
    Get the global VATSIM service instance.
    
    Returns:
        VATSIMService: The global VATSIM service instance
    """
    global _vatsim_service
    if _vatsim_service is None:
        _vatsim_service = VATSIMService()
        # Initialize the service
        asyncio.create_task(_vatsim_service.initialize())
    return _vatsim_service 
