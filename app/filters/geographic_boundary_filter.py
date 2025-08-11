#!/usr/bin/env python3
"""
Geographic Boundary Filter for VATSIM Data Collection

This module implements a geographic boundary filter to only include flights that are
physically located within a specified geographic polygon boundary (e.g., Australian airspace).

INPUTS:
- Raw VATSIM API data (JSON structure)
- Geographic boundary polygon data (GeoJSON format)
- Flight position data (latitude, longitude)

OUTPUTS:
- Filtered VATSIM API data with identical structure
- Flights outside the geographic boundary completely discarded
- All other data (controllers, servers, etc.) unchanged

FEATURES:
- Shapely-based point-in-polygon calculations for accuracy
- GeoJSON polygon support with coordinate validation
- Performance monitoring with configurable thresholds
- Comprehensive logging of filtering decisions
- Conservative approach: includes flights with missing position data
- Environment-based configuration
- Real-time filtering statistics
- Independent operation from other filters

USAGE:
    filter = GeographicBoundaryFilter()
    filtered_data = filter.filter_vatsim_data(raw_vatsim_data)
    stats = filter.get_filter_stats()
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# Import our geographic utilities
from ..utils.geographic_utils import (
    load_polygon_from_geojson,
    is_point_in_polygon,
    validate_geojson_polygon,
    get_polygon_bounds,
    get_cached_polygon
)

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class GeographicBoundaryConfig:
    """Geographic boundary filter configuration"""
    enabled: bool = False
    boundary_data_path: str = ""
    log_level: str = "INFO"

class GeographicBoundaryFilter:
    """
    Geographic Boundary Filter
    
    Filters VATSIM data to only include flights within a specified geographic boundary.
    Uses Shapely for efficient point-in-polygon calculations.
    """
    
    def __init__(self):
        """Initialize geographic boundary filter with configuration."""
        self.config = self._get_filter_config()
        self.polygon = None
        self.is_initialized = False
        self._setup_logging()
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'flights_included': 0,
            'flights_excluded': 0,
            'flights_no_position': 0,
            'total_transceivers_processed': 0,
            'transceivers_included': 0,
            'transceivers_excluded': 0,
            'transceivers_no_position': 0,
            'total_controllers_processed': 0,
            'controllers_included': 0,
            'controllers_excluded': 0,
            'processing_time_ms': 0.0
        }
        
        logger.info(f"Geographic boundary filter initialized - enabled: {self.config.enabled}")
        
        if self.config.enabled:
            self._load_boundary_data()
    
    def _get_filter_config(self) -> GeographicBoundaryConfig:
        """Get filter configuration from environment variables"""
        return GeographicBoundaryConfig(
            enabled=os.getenv("ENABLE_BOUNDARY_FILTER", "false").lower() == "true",
            boundary_data_path=os.getenv("BOUNDARY_DATA_PATH", ""),
            log_level=os.getenv("BOUNDARY_FILTER_LOG_LEVEL", "INFO")
        )
    
    def _setup_logging(self):
        """Setup logging for the filter"""
        # Note: Don't call basicConfig here as it may interfere with existing logging setup
        # Just set the logger level if needed
        if hasattr(logging, self.config.log_level):
            logger.setLevel(getattr(logging, self.config.log_level))
    
    def _load_boundary_data(self):
        """Load boundary polygon data from file"""
        try:
            if not self.config.boundary_data_path:
                logger.error("Boundary data path not configured")
                return
            
            # Validate file exists and is valid GeoJSON
            if not validate_geojson_polygon(self.config.boundary_data_path):
                logger.error(f"Invalid boundary data file: {self.config.boundary_data_path}")
                return
            
            # Load polygon using cached loading for performance
            self.polygon = get_cached_polygon(self.config.boundary_data_path)
            
            # Get polygon bounds for logging
            bounds = get_polygon_bounds(self.polygon)
            
            self.is_initialized = True
            logger.info(f"✅ Loaded boundary polygon from {self.config.boundary_data_path}")
            logger.info(f"📍 Polygon bounds: {bounds}")
            logger.info(f"📊 Polygon points: {len(self.polygon.exterior.coords)}")
            
        except Exception as e:
            logger.error(f"Failed to load boundary data: {e}")
            self.is_initialized = False
    
    def _is_flight_in_boundary(self, flight_data: Dict[str, Any]) -> bool:
        """
        Check if a flight is within the geographic boundary
        
        Args:
            flight_data: Flight data from VATSIM API
            
        Returns:
            True if flight is within boundary, False otherwise
        """
        # Check if filter is properly initialized
        if not self.is_initialized:
            logger.debug("Filter not initialized, allowing flight through")
            return True
        
        # Extract position data - try different possible field names
        latitude = flight_data.get('latitude') or flight_data.get('lat')
        longitude = flight_data.get('longitude') or flight_data.get('lng') or flight_data.get('lon')
        
        if latitude is None or longitude is None:
            callsign = flight_data.get('callsign', 'UNKNOWN')
            logger.debug(f"Flight {callsign} has no position data, allowing through")
            self.stats['flights_no_position'] += 1
            return True  # Conservative: allow flights without position data
        
        try:
            # Convert to float if needed
            lat = float(latitude)
            lon = float(longitude)
            
            # Check if position is within boundary using our geographic utils
            is_inside = is_point_in_polygon(lat, lon, self.polygon)
            
            callsign = flight_data.get('callsign', 'UNKNOWN')
            if is_inside:
                logger.debug(f"Flight {callsign} is within boundary at ({lat:.4f}, {lon:.4f})")
                self.stats['flights_included'] += 1
            else:
                logger.debug(f"Flight {callsign} is outside boundary at ({lat:.4f}, {lon:.4f})")
                self.stats['flights_excluded'] += 1
            
            return is_inside
            
        except (ValueError, TypeError) as e:
            callsign = flight_data.get('callsign', 'UNKNOWN')
            logger.warning(f"Invalid coordinates for flight {callsign}: {e}")
            self.stats['flights_no_position'] += 1
            return True  # Conservative: allow flights with invalid coordinates
    
    def filter_flights_list(self, flights: List[Dict]) -> List[Dict]:
        """
        Filter a list of flight objects to only include those within the boundary
        
        Args:
            flights: List of flight data dictionaries
            
        Returns:
            Filtered list of flight data dictionaries
        """
        if not self.config.enabled:
            logger.debug("Geographic boundary filter is disabled, returning original flights")
            return flights
        
        if not flights:
            logger.debug("No flights provided to filter")
            return flights
        
        # Reset statistics for this run
        self.stats['total_processed'] = len(flights)
        self.stats['flights_included'] = 0
        self.stats['flights_excluded'] = 0
        self.stats['flights_no_position'] = 0
        
        start_time = time.time()
        
        filtered_flights = []
        
        for flight in flights:
            if self._is_flight_in_boundary(flight):
                filtered_flights.append(flight)
        
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        self.stats['processing_time_ms'] = processing_time_ms
        
        original_count = len(flights)
        filtered_count = len(filtered_flights)
        
        logger.info(f"Geographic boundary filter: {original_count} flights -> {filtered_count} flights "
                   f"({original_count - filtered_count} filtered out) in {processing_time_ms:.2f}ms")
        
        # Log processing time
        if processing_time_ms > 10.0:  # Log warning if processing takes more than 10ms
            logger.warning(f"Geographic boundary filter processing time: {processing_time_ms:.2f}ms")
        
        return filtered_flights
    
    def _is_transceiver_in_boundary(self, transceiver_data: Dict[str, Any]) -> bool:
        """
        Check if a transceiver is within the geographic boundary
        
        Args:
            transceiver_data: Transceiver data from VATSIM API
            
        Returns:
            True if transceiver is within boundary, False otherwise
        """
        # Check if filter is properly initialized
        if not self.is_initialized:
            logger.debug("Filter not initialized, allowing transceiver through")
            return True
        
        # Extract position data
        latitude = transceiver_data.get('position_lat') or transceiver_data.get('lat')
        longitude = transceiver_data.get('position_lon') or transceiver_data.get('lon')
        
        if latitude is None or longitude is None:
            callsign = transceiver_data.get('callsign', 'UNKNOWN')
            logger.debug(f"Transceiver {callsign} has no position data, allowing through")
            self.stats['transceivers_no_position'] += 1
            return True  # Conservative: allow transceivers without position data
        
        try:
            # Convert to float if needed
            lat = float(latitude)
            lon = float(longitude)
            
            # Check if position is within boundary using our geographic utils
            is_inside = is_point_in_polygon(lat, lon, self.polygon)
            
            callsign = transceiver_data.get('callsign', 'UNKNOWN')
            if is_inside:
                logger.debug(f"Transceiver {callsign} is within boundary at ({lat:.4f}, {lon:.4f})")
                self.stats['transceivers_included'] += 1
            else:
                logger.debug(f"Transceiver {callsign} is outside boundary at ({lat:.4f}, {lon:.4f})")
                self.stats['transceivers_excluded'] += 1
            
            return is_inside
            
        except (ValueError, TypeError) as e:
            callsign = transceiver_data.get('callsign', 'UNKNOWN')
            logger.warning(f"Invalid coordinates for transceiver {callsign}: {e}")
            self.stats['transceivers_no_position'] += 1
            return True  # Conservative: allow transceivers with invalid coordinates
    
    def _is_controller_in_boundary(self, controller_data: Dict[str, Any]) -> bool:
        """
        Check if a controller is within the geographic boundary
        
        Args:
            controller_data: Controller data from VATSIM API
            
        Returns:
            True if controller is within boundary, False otherwise
        """
        # Check if filter is properly initialized
        if not self.is_initialized:
            logger.debug("Filter not initialized, allowing controller through")
            return True
        
        # Extract position data - controllers may not have direct position data
        # We'll use a conservative approach and allow controllers through
        # since they represent ATC positions that may not have specific coordinates
        callsign = controller_data.get('callsign', 'UNKNOWN')
        logger.debug(f"Controller {callsign} - no position filtering applied (conservative approach)")
        self.stats['controllers_included'] += 1
        return True  # Allow all controllers through for now
    
    def filter_transceivers_list(self, transceivers: List[Dict]) -> List[Dict]:
        """
        Filter a list of transceiver objects to only include those within the boundary
        
        Args:
            transceivers: List of transceiver data dictionaries
            
        Returns:
            Filtered list of transceiver data dictionaries
        """
        if not self.config.enabled:
            logger.debug("Geographic boundary filter is disabled, returning original transceivers")
            return transceivers
        
        if not transceivers:
            logger.debug("No transceivers provided to filter")
            return transceivers
        
        # Reset statistics for this run
        self.stats['total_transceivers_processed'] = len(transceivers)
        self.stats['transceivers_included'] = 0
        self.stats['transceivers_excluded'] = 0
        self.stats['transceivers_no_position'] = 0
        
        start_time = time.time()
        
        filtered_transceivers = []
        
        for transceiver in transceivers:
            if self._is_transceiver_in_boundary(transceiver):
                filtered_transceivers.append(transceiver)
        
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        
        original_count = len(transceivers)
        filtered_count = len(filtered_transceivers)
        
        logger.info(f"Geographic boundary filter: {original_count} transceivers -> {filtered_count} transceivers "
                   f"({original_count - filtered_count} filtered out) in {processing_time_ms:.2f}ms")
        
        return filtered_transceivers
    
    def filter_controllers_list(self, controllers: List[Dict]) -> List[Dict]:
        """
        Filter a list of controller objects to only include those within the boundary
        
        Args:
            controllers: List of controller data dictionaries
            
        Returns:
            Filtered list of controller data dictionaries
        """
        if not self.config.enabled:
            logger.debug("Geographic boundary filter is disabled, returning original controllers")
            return controllers
        
        if not controllers:
            logger.debug("No controllers provided to filter")
            return controllers
        
        # Reset statistics for this run
        self.stats['total_controllers_processed'] = len(controllers)
        self.stats['controllers_included'] = 0
        self.stats['controllers_excluded'] = 0
        
        start_time = time.time()
        
        filtered_controllers = []
        
        for controller in controllers:
            if self._is_controller_in_boundary(controller):
                filtered_controllers.append(controller)
        
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        
        original_count = len(controllers)
        filtered_count = len(filtered_controllers)
        
        logger.info(f"Geographic boundary filter: {original_count} controllers -> {filtered_count} controllers "
                   f"({original_count - filtered_count} filtered out) in {processing_time_ms:.2f}ms")
        
        return filtered_controllers
    
    def filter_vatsim_data(self, vatsim_data: Dict) -> Dict:
        """
        Filter VATSIM data to only include flights within the geographic boundary
        
        Args:
            vatsim_data: Raw VATSIM API data
            
        Returns:
            Filtered VATSIM data with identical structure
        """
        if not self.config.enabled:
            logger.debug("Geographic boundary filter is disabled, returning original data")
            return vatsim_data
        
        # Create a copy of the data to avoid modifying the original
        filtered_data = vatsim_data.copy()
        
        # Get flights from the data (VATSIM API v3 uses "pilots" key)
        flights = filtered_data.get("pilots", [])
        if not flights:
            logger.debug("No flights found in VATSIM data")
            return filtered_data
        
        # Filter flights using the list method
        filtered_flights = self.filter_flights_list(flights)
        
        # Update the data with filtered flights
        filtered_data["pilots"] = filtered_flights
        
        return filtered_data
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """
        Get filter statistics and status
        
        Returns:
            Dictionary with filter statistics
        """
        polygon_info = {}
        if self.is_initialized and self.polygon:
            bounds = get_polygon_bounds(self.polygon)
            polygon_info = {
                "polygon_points": len(self.polygon.exterior.coords),
                "polygon_bounds": bounds,
                "boundary_file": self.config.boundary_data_path
            }
        
        return {
            "enabled": self.config.enabled,
            "initialized": self.is_initialized,
            "log_level": self.config.log_level,
            "filter_type": "Geographic boundary (point-in-polygon)",
            "inclusion_criteria": "Flights physically within the defined geographic boundary",
            "validation_method": "Shapely point-in-polygon calculations",
            "conservative_approach": "Allows flights with missing or invalid position data",
            **polygon_info,
            **self.stats
        }
    
    def reload_boundary_data(self):
        """
        Reload boundary data from file (useful for configuration changes)
        """
        logger.info("Reloading boundary data...")
        self.is_initialized = False
        self.polygon = None
        
        if self.config.enabled:
            self._load_boundary_data()
        else:
            logger.info("Filter is disabled, skipping boundary data reload")
    
    def get_boundary_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the loaded boundary polygon
        
        Returns:
            Dictionary with boundary information or None if not loaded
        """
        if not self.is_initialized or not self.polygon:
            return None
        
        bounds = get_polygon_bounds(self.polygon)
        
        return {
            "file_path": self.config.boundary_data_path,
            "polygon_points": len(self.polygon.exterior.coords),
            "bounds": bounds,
            "area_sq_degrees": self.polygon.area,  # Approximate area in square degrees
            "is_valid": self.polygon.is_valid
        }
