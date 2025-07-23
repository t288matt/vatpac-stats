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
class VATSIMData:
    """Complete VATSIM network data."""
    
    controllers: List[VATSIMController]
    flights: List[VATSIMFlight]
    sectors: List[Dict[str, Any]]
    timestamp: datetime
    total_controllers: int
    total_flights: int
    total_sectors: int


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
            
            # Create VATSIM data object
            vatsim_data = VATSIMData(
                controllers=controllers,
                flights=flights,
                sectors=sectors,
                timestamp=datetime.utcnow(),
                total_controllers=len(controllers),
                total_flights=len(flights),
                total_sectors=len(sectors)
            )
            
            self.logger.info("Successfully fetched VATSIM data", extra={
                "controllers_count": vatsim_data.total_controllers,
                "flights_count": vatsim_data.total_flights,
                "sectors_count": vatsim_data.total_sectors
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
                controller = VATSIMController(
                    callsign=controller_data.get("callsign", ""),
                    facility=controller_data.get("facility", ""),
                    position=controller_data.get("position", ""),
                    frequency=controller_data.get("frequency", ""),
                    status=controller_data.get("status", "offline")
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