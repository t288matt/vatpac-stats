#!/usr/bin/env python3
"""
VATSIM Service Interface for VATSIM Data Collection System

This interface defines the contract for VATSIM API interaction services.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime


class VATSIMServiceInterface(ABC):
    """Interface for VATSIM API interaction services."""
    
    @abstractmethod
    async def get_current_data(self) -> Dict[str, Any]:
        """Fetch current data from VATSIM API."""
        pass
    
    @abstractmethod
    async def get_api_status(self) -> Dict[str, Any]:
        """Get VATSIM API status and health information."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if VATSIM API is accessible."""
        pass
    
    @abstractmethod
    async def parse_controllers(self, controllers_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse controller data from VATSIM API response."""
        pass
    
    @abstractmethod
    async def parse_flights(self, flights_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse flight data from VATSIM API response."""
        pass
    
    @abstractmethod
    async def parse_sectors(self, sectors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse sector data from VATSIM API response."""
        pass
    
    @abstractmethod
    async def parse_transceivers(self, transceivers_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse transceiver data from VATSIM API response."""
        pass
    
    @abstractmethod
    async def validate_api_response(self, response: Dict[str, Any]) -> bool:
        """Validate VATSIM API response structure."""
        pass
    
    @abstractmethod
    async def get_api_endpoints(self) -> Dict[str, str]:
        """Get available VATSIM API endpoints."""
        pass 