#!/usr/bin/env python3
"""
VATSIM API service for ATC Position Recommendation Engine.

This service handles all VATSIM API interactions following our
architecture principles of maintainability and supportability.
"""

import asyncio
import httpx
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from ..config import get_config
from ..utils.logging import get_logger_for_module


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


@dataclass
class VATSIMFlight:
    """VATSIM flight data structure."""
    
    callsign: str
    pilot_name: str
    aircraft_type: str
    departure: str
    arrival: str
    route: str
    altitude: int
    speed: int
    position: Optional[Dict[str, float]] = None
    controller_id: Optional[str] = None


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


class VATSIMService:
    """
    Service for handling VATSIM API interactions.
    
    This service provides a clean interface for fetching and processing
    VATSIM network data, following our architecture principles.
    """
    
    def __init__(self):
        """Initialize VATSIM service with configuration."""
        self.config = get_config()
        self.logger = get_logger_for_module(__name__)
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_client()
    
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
            flights = self._parse_flights(parsed_data.get("pilots", []))
            sectors = parsed_data.get("sectors", [])
            
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
                timestamp=datetime.utcnow(),
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
                    controller_id=str(controller_data.get("cid", "")),
                    controller_name=controller_data.get("name", ""),
                    controller_rating=controller_data.get("rating", 0)
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
                
                flight = VATSIMFlight(
                    callsign=flight_data.get("callsign", ""),
                    pilot_name=flight_data.get("name", ""),
                    aircraft_type=flight_data.get("aircraft_type", ""),
                    departure=flight_plan.get("departure", ""),
                    arrival=flight_plan.get("arrival", ""),
                    route=flight_plan.get("route", ""),
                    altitude=int(flight_data.get("altitude", 0)),
                    speed=int(flight_data.get("groundspeed", 0)),
                    position=position,
                    controller_id=flight_data.get("controller", "")
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
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
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
    return _vatsim_service 