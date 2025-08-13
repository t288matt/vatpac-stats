#!/usr/bin/env python3
"""
Geographic Boundary Filter Module

This module provides geographic boundary filtering for VATSIM data,
allowing users to filter flights, controllers, and transceivers
based on whether they are within a defined geographic boundary.

Author: VATSIM Data System
Created: 2025-01-08
Status: Sprint 1, Task 1.4 - Geographic Boundary Filter
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from shapely.geometry import Polygon

# Import our geographic utilities
from app.utils.geographic_utils import (
    is_point_in_polygon,
    get_cached_polygon,
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
        
        # Only load boundary data if filter is enabled
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
        if hasattr(logging, self.config.log_level):
            logger.setLevel(getattr(logging, self.config.log_level))
    
    def _load_boundary_data(self):
        """Load boundary data from the configured file path"""
        try:
            if not self.config.boundary_data_path:
                error_msg = "No boundary data path configured - geographic filtering is enabled but not configured"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Load polygon using cached loading for performance
            self.polygon = get_cached_polygon(self.config.boundary_data_path)
            
            if not self.polygon:
                error_msg = f"Failed to load valid polygon from {self.config.boundary_data_path}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            self.is_initialized = True
            logger.info(f"✅ Loaded boundary polygon from {self.config.boundary_data_path}")
            logger.info(f"📊 Polygon points: {len(self.polygon.exterior.coords)}")
            
        except Exception as e:
            error_msg = f"CRITICAL: Failed to load boundary data from {self.config.boundary_data_path}: {e}"
            logger.error(error_msg)
            # This is a fatal error - the system cannot function without proper filtering
            raise RuntimeError(error_msg)
    
    def _is_flight_in_boundary(self, flight_data: Dict[str, Any]) -> bool:
        """Check if a flight is within the geographic boundary"""
        # If filter is disabled, allow everything through
        if not self.config.enabled:
            return True
        
        # If filter is enabled but not working, that's a fatal error
        if not self.is_initialized:
            raise RuntimeError("Geographic boundary filter is enabled but not initialized")
        
        # Extract position data
        latitude = flight_data.get('latitude')
        longitude = flight_data.get('longitude')
        
        if latitude is None or longitude is None:
            self.stats['flights_no_position'] += 1
            return True
        
        try:
            lat, lon = float(latitude), float(longitude)
            is_inside = is_point_in_polygon(lat, lon, self.polygon)
            
            if is_inside:
                self.stats['flights_included'] += 1
            else:
                self.stats['flights_excluded'] += 1
            
            return is_inside
            
        except (ValueError, TypeError):
            self.stats['flights_no_position'] += 1
            return True
    
    def filter_flights_list(self, flights: List[Dict]) -> List[Dict]:
        """Filter flights to only include those within the boundary"""
        if not self.config.enabled:
            return flights or []
        if not flights:
            return []
        
        # Reset statistics for this run
        self.stats['total_processed'] = len(flights)
        self.stats['flights_included'] = 0
        self.stats['flights_excluded'] = 0
        self.stats['flights_no_position'] = 0
        
        filtered_flights = [flight for flight in flights if self._is_flight_in_boundary(flight)]
        
        # Log filtering results
        if len(flights) != len(filtered_flights):
            logger.info(f"Geographic filter: {len(flights)} flights -> {len(filtered_flights)} flights (filtered)")
        else:
            logger.debug(f"Geographic filter: {len(flights)} flights -> {len(filtered_flights)} flights")
        
        return filtered_flights
    
    def _is_transceiver_in_boundary(self, transceiver_data: Dict[str, Any]) -> bool:
        """Check if a transceiver is within the geographic boundary"""
        # If filter is disabled, allow everything through
        if not self.config.enabled:
            return True
        
        # If filter is enabled but not working, that's a fatal error
        if not self.is_initialized:
            raise RuntimeError("Geographic boundary filter is enabled but not initialized")
        
        # Extract position data
        latitude = transceiver_data.get('position_lat')
        longitude = transceiver_data.get('position_lon')
        
        if latitude is None or longitude is None:
            self.stats['transceivers_no_position'] += 1
            return True
        
        try:
            lat, lon = float(latitude), float(longitude)
            is_inside = is_point_in_polygon(lat, lon, self.polygon)
            
            if is_inside:
                self.stats['transceivers_included'] += 1
            else:
                self.stats['transceivers_excluded'] += 1
            
            return is_inside
            
        except (ValueError, TypeError):
            self.stats['transceivers_no_position'] += 1
            return True
    
    def _is_controller_in_boundary(self, controller_data: Dict[str, Any]) -> bool:
        """Check if a controller is within the geographic boundary"""
        # If filter is disabled, allow everything through
        if not self.config.enabled:
            return True
        
        # If filter is enabled but not working, that's a fatal error
        if not self.is_initialized:
            raise RuntimeError("Geographic boundary filter is enabled but not initialized")
        
        # Controllers don't have position data, so allow all through
        self.stats['controllers_included'] += 1
        return True
    
    def filter_transceivers_list(self, transceivers: List[Dict]) -> List[Dict]:
        """Filter transceivers to only include those within the boundary"""
        if not self.config.enabled:
            return transceivers or []
        if not transceivers:
            return []
        
        # Reset statistics for this run
        self.stats['total_transceivers_processed'] = len(transceivers)
        self.stats['transceivers_included'] = 0
        self.stats['transceivers_excluded'] = 0
        self.stats['transceivers_no_position'] = 0
        
        filtered_transceivers = [t for t in transceivers if self._is_transceiver_in_boundary(t)]
        
        # Log filtering results
        if len(transceivers) != len(filtered_transceivers):
            logger.info(f"Geographic filter: {len(transceivers)} transceivers -> {len(filtered_transceivers)} transceivers (filtered)")
        else:
            logger.debug(f"Geographic filter: {len(transceivers)} transceivers -> {len(filtered_transceivers)} transceivers")
        
        return filtered_transceivers
    
    def filter_controllers_list(self, controllers: List[Dict]) -> List[Dict]:
        """Filter controllers to only include those within the boundary"""
        if not self.config.enabled:
            return controllers or []
        if not controllers:
            return []
        
        # Reset statistics for this run
        self.stats['total_controllers_processed'] = len(controllers)
        self.stats['controllers_included'] = 0
        self.stats['controllers_excluded'] = 0
        
        filtered_controllers = [c for c in controllers if self._is_controller_in_boundary(c)]
        
        # Log filtering results
        if len(controllers) != len(filtered_controllers):
            logger.info(f"Geographic filter: {len(controllers)} controllers -> {len(filtered_controllers)} controllers (filtered)")
        else:
            logger.debug(f"Geographic filter: {len(controllers)} controllers -> {len(filtered_controllers)} controllers")
        
        return filtered_controllers
    
    def filter_vatsim_data(self, vatsim_data: Dict) -> Dict:
        """Filter VATSIM data to only include flights within the boundary"""
        if not self.config.enabled:
            return vatsim_data
        
        filtered_data = vatsim_data.copy()
        flights = filtered_data.get("pilots", [])
        
        if flights:
            filtered_data["pilots"] = self.filter_flights_list(flights)
        
        return filtered_data
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter statistics and status"""
        polygon_info = {}
        if self.is_initialized and self.polygon:
            polygon_info = {
                "polygon_points": len(self.polygon.exterior.coords),
                "boundary_file": self.config.boundary_data_path
            }
        
        return {
            "enabled": self.config.enabled,
            "initialized": self.is_initialized,
            **polygon_info,
            **self.stats
        }
    
    def get_filter_status(self) -> Dict[str, Any]:
        """Get the current status of the geographic boundary filter"""
        status = {
            "enabled": self.config.enabled,
            "initialized": self.is_initialized,
            "boundary_data_path": self.config.boundary_data_path,
            "polygon_loaded": self.polygon is not None,
            "polygon_points": len(self.polygon.exterior.coords) if self.polygon else 0,
            "configuration_valid": self.is_initialized and self.polygon is not None and len(self.polygon.exterior.coords) >= 3 if self.polygon else False
        }
        
        if not status["configuration_valid"] and self.config.enabled:
            status["error"] = "Filter is enabled but not properly configured - this is a critical error"
        elif not self.config.enabled:
            status["status"] = "Filter is disabled - all data passes through without filtering"
        
        return status
    
    def reload_boundary_data(self):
        """Reload boundary data from file (useful for configuration changes)"""
        logger.info("Reloading boundary data...")
        self.is_initialized = False
        self.polygon = None
        
        if self.config.enabled:
            self._load_boundary_data()
        else:
            logger.info("Filter is disabled, skipping boundary data reload")
    
    def get_boundary_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the loaded boundary polygon"""
        if not self.is_initialized or not self.polygon:
            return None
        
        return {
            "file_path": self.config.boundary_data_path,
            "polygon_points": len(self.polygon.exterior.coords),
            "area_sq_degrees": self.polygon.area,  # Approximate area in square degrees
            "is_valid": self.polygon.is_valid
        }
