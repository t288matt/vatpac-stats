#!/usr/bin/env python3
"""
Flight Processing Interface for VATSIM Data Collection System

This interface defines the contract for flight data processing and filtering services.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime


class FlightProcessingInterface(ABC):
    """Interface for flight data processing and filtering services."""
    
    @abstractmethod
    async def filter_flights(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter flights based on configured criteria."""
        pass
    
    @abstractmethod
    async def process_flight_data(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate individual flight data."""
        pass
    
    @abstractmethod
    async def validate_flight_plan(self, flight_plan: Dict[str, Any]) -> bool:
        """Validate flight plan data structure."""
        pass
    
    @abstractmethod
    async def extract_airport_codes(self, flight_data: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """Extract departure and arrival airport codes from flight data."""
        pass
    
    @abstractmethod
    async def is_australian_flight(self, flight_data: Dict[str, Any]) -> bool:
        """Check if flight has Australian origin or destination."""
        pass
    
    @abstractmethod
    async def get_filter_stats(self) -> Dict[str, Any]:
        """Get flight filter statistics and configuration."""
        pass
    
    @abstractmethod
    async def update_filter_config(self, config: Dict[str, Any]) -> bool:
        """Update flight filter configuration."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the flight processing service."""
        pass 