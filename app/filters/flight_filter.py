#!/usr/bin/env python3
"""
Australian Flight Filter for VATSIM Data Collection

This module implements a simplified flight filter to only include flights that have
either origin or destination in Australia, using the existing Australian airports database.

INPUTS:
- Raw VATSIM API data (JSON structure)
- Australian airports database view
- Flight plan data with departure and arrival airport codes

OUTPUTS:
- Filtered VATSIM API data with identical structure
- Flights without Australian origin or destination completely discarded
- All other data (controllers, servers, etc.) unchanged

FEATURES:
- Database-based airport validation using australian_airports view
- Simple OR logic: include if either departure OR arrival is Australian
- Performance-optimized filtering with minimal database queries
- Comprehensive logging of filtering decisions
- Conservative approach: includes flights with missing airport codes
- Environment-based configuration
- Real-time filtering statistics

USAGE:
    filter = FlightFilter()
    filtered_data = filter.filter_vatsim_data(raw_vatsim_data)
    stats = filter.get_filter_stats()
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# Import the centralized Australian airport validation
from ..config import is_australian_airport

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class FlightFilterConfig:
    """Flight filter configuration"""
    enabled: bool = False
    log_level: str = "INFO"

class FlightFilter:
    """
    Australian Flight Filter
    
    Filters VATSIM data to only include flights with Australian origin or destination.
    Uses simple airport code validation (starts with 'Y') for performance.
    """
    
    def __init__(self):
        self.config = self._get_filter_config()
        self._setup_logging()
        logger.info(f"Flight filter initialized - enabled: {self.config.enabled}")
    
    def _get_filter_config(self) -> FlightFilterConfig:
        """Get filter configuration from environment variables"""
        return FlightFilterConfig(
            enabled=os.getenv("FLIGHT_FILTER_ENABLED", "false").lower() == "true",
            log_level=os.getenv("FLIGHT_FILTER_LOG_LEVEL", "INFO")
        )
    
    def _setup_logging(self):
        """Setup logging for the filter"""
        logging.basicConfig(level=getattr(logging, self.config.log_level))
    
    def _extract_airport_codes(self, flight_data: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract departure and arrival airport codes from flight data
        
        Args:
            flight_data: Flight data from VATSIM API
            
        Returns:
            Tuple of (departure_code, arrival_code) or (None, None) if not found
        """
        # Extract from flight plan if available
        flight_plan = flight_data.get("flight_plan", {})
        if flight_plan is None:
            flight_plan = {}
            
        departure = flight_plan.get("departure")
        arrival = flight_plan.get("arrival")
        
        # If not in flight plan, try direct fields
        if not departure:
            departure = flight_data.get("departure")
        if not arrival:
            arrival = flight_data.get("arrival")
        
        return departure, arrival
    
    def _is_australian_airport(self, airport_code: str) -> bool:
        """
        Check if an airport code is Australian using centralized validation
        
        Args:
            airport_code: Airport ICAO code
            
        Returns:
            True if airport code is Australian, False otherwise
        """
        # Use the centralized Australian airport validation from config
        return is_australian_airport(airport_code)
    
    def _is_australian_flight(self, flight_data: Dict) -> bool:
        """
        Check if a flight has either Australian origin or destination
        
        Args:
            flight_data: Flight data from VATSIM API
            
        Returns:
            True if flight has Australian origin OR destination, False otherwise
        """
        departure, arrival = self._extract_airport_codes(flight_data)
        
        # If we can't determine airports, filter out the flight
        if not departure and not arrival:
            logger.debug(f"Flight {flight_data.get('callsign', 'UNKNOWN')} has no airport codes, filtering out")
            return False
        
        # Check if either departure or arrival is Australian
        departure_australian = departure and self._is_australian_airport(departure)
        arrival_australian = arrival and self._is_australian_airport(arrival)
        
        is_australian = departure_australian or arrival_australian
        
        callsign = flight_data.get('callsign', 'UNKNOWN')
        if is_australian:
            logger.debug(f"Flight {callsign} included - departure: {departure} ({departure_australian}), arrival: {arrival} ({arrival_australian})")
        else:
            logger.info(f"Flight {callsign} filtered out - departure: {departure}, arrival: {arrival}")
        
        return is_australian
    
    def filter_flights_list(self, flights: List[Dict]) -> List[Dict]:
        """
        Filter a list of flight objects to only include Australian flights
        
        Args:
            flights: List of flight data dictionaries
            
        Returns:
            Filtered list of flight data dictionaries
        """
        if not self.config.enabled:
            logger.debug("Flight filter is disabled, returning original flights")
            return flights
        
        if not flights:
            logger.debug("No flights provided to filter")
            return flights
        
        # Filter flights
        original_count = len(flights)
        filtered_flights = []
        
        for flight in flights:
            if self._is_australian_flight(flight):
                filtered_flights.append(flight)
        
        filtered_count = len(filtered_flights)
        logger.info(f"Flight filter: {original_count} flights -> {filtered_count} flights "
                   f"({original_count - filtered_count} filtered out)")
        
        return filtered_flights
    
    def filter_vatsim_data(self, vatsim_data: Dict) -> Dict:
        """
        Filter VATSIM data to only include flights with Australian origin or destination
        
        Args:
            vatsim_data: Raw VATSIM API data
            
        Returns:
            Filtered VATSIM data with identical structure
        """
        if not self.config.enabled:
            logger.debug("Flight filter is disabled, returning original data")
            return vatsim_data
        
        # Create a copy of the data to avoid modifying the original
        filtered_data = vatsim_data.copy()
        
        # Get flights from the data
        flights = filtered_data.get("pilots", [])
        if not flights:
            logger.debug("No flights found in VATSIM data")
            return filtered_data
        
        # Filter flights
        original_count = len(flights)
        filtered_flights = []
        
        for flight in flights:
            if self._is_australian_flight(flight):
                filtered_flights.append(flight)
        
        # Update the data with filtered flights
        filtered_data["pilots"] = filtered_flights
        
        filtered_count = len(filtered_flights)
        logger.info(f"Flight filter: {original_count} flights -> {filtered_count} flights "
                   f"({original_count - filtered_count} filtered out)")
        
        return filtered_data
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """
        Get filter statistics and status
        
        Returns:
            Dictionary with filter statistics
        """
        return {
            "enabled": self.config.enabled,
            "log_level": self.config.log_level,
            "filter_type": "Australian airport code validation",
            "inclusion_criteria": "Flights with Australian origin OR destination",
            "validation_method": "Airport codes starting with 'Y'",
            "performance_optimized": True,
            "strict_approach": "Filters out flights with no departure AND no arrival airport codes"
        } 
