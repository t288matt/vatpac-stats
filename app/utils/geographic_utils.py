#!/usr/bin/env python3
"""
Geographic Utilities Module

Provides utilities for geographic boundary filtering using polygon-based
airspace definitions. Supports GeoJSON format files and uses Shapely for
efficient polygon calculations.
"""

import json
import logging
from typing import List, Tuple, Dict, Any, Optional
from shapely.geometry import Point, Polygon, shape
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def parse_ddmm_coordinate(coord_string: str) -> float:
    """Convert DDMMSS.SSSS format or decimal degrees to decimal degrees.
    
    Args:
        coord_string: Coordinate in DDMMSS.SSSS format (e.g., "-343848.000") or decimal degrees (e.g., "-23.426358")
        
    Returns:
        float: Coordinate in decimal degrees (e.g., -34.6413, -23.426358)
        
    Example:
        parse_ddmm_coordinate("-343848.000") -> -34.6467
        parse_ddmm_coordinate("+1494851.000") -> 149.8142
        parse_ddmm_coordinate("-23.426358") -> -23.426358
        
    Format: 
        DDMMSS.SSSS (6 digits before decimal) or DDDMMSS.SSSS (7 digits before decimal)
        OR decimal degrees (e.g., -23.426358)
        where:
        DD/DDD = degrees (2 or 3 digits)
        MM = minutes (2 digits) 
        SS.SSSS = seconds (2 digits + decimal)
    """
    try:
        # Remove any whitespace and convert to string
        coord_str = str(coord_string).strip()
        
        # Handle negative and positive coordinates
        is_negative = coord_str.startswith('-')
        if coord_str.startswith('+') or coord_str.startswith('-'):
            coord_str = coord_str[1:]  # Remove sign
        
        # Check if this is already in decimal degrees format
        # Decimal degrees have 1-3 digits before decimal point (e.g., 23.426358, 133.878056)
        if '.' in coord_str:
            digits_before_decimal = len(coord_str.split('.')[0])
            if digits_before_decimal <= 3:
                # This is likely decimal degrees (e.g., "23.426358", "133.878056")
                try:
                    decimal_degrees = float(coord_str)
                    if is_negative:
                        decimal_degrees = -decimal_degrees
                    return decimal_degrees
                except ValueError:
                    # If float conversion fails, continue with DDMMSS parsing
                    pass
        
        # Find decimal point to count digits before it
        if '.' not in coord_str:
            raise ValueError(f"Invalid coordinate format: {coord_string}")
        
        decimal_pos = coord_str.find('.')
        digits_before_decimal = len(coord_str[:decimal_pos])
        
        if digits_before_decimal not in [6, 7]:
            raise ValueError(f"Invalid coordinate format: {coord_string} - expected 6 or 7 digits before decimal")
        
        # Parse based on number of digits before decimal
        if digits_before_decimal == 7:
            # DDDMMSS.SSSS format (3 digits for degrees)
            degrees = int(coord_str[:3])      # First 3 digits = degrees
            minutes = int(coord_str[3:5])     # Next 2 digits = minutes
            seconds = float(coord_str[5:])    # Remaining = seconds
        else:
            # DDMMSS.SSSS format (2 digits for degrees)
            degrees = int(coord_str[:2])      # First 2 digits = degrees
            minutes = int(coord_str[2:4])     # Next 2 digits = minutes
            seconds = float(coord_str[4:])    # Remaining = seconds
        
        # Convert to decimal degrees: DD + MM/60 + SS/3600
        decimal_degrees = degrees + (minutes / 60.0) + (seconds / 3600.0)
        
        # Apply negative sign if needed
        if is_negative:
            decimal_degrees = -decimal_degrees
            
        return decimal_degrees
        
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing coordinate '{coord_string}': {e}")
        raise ValueError(f"Invalid coordinate format: {coord_string}") from e

def load_polygon_from_geojson(json_file_path: str) -> Polygon:
    """Load polygon from GeoJSON file and return Shapely Polygon object."""
    try:
        file_path = Path(json_file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"GeoJSON file not found: {json_file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if "coordinates" not in data:
            raise ValueError("JSON file must contain 'coordinates' key")
        
        coords = data["coordinates"]
        
        # Handle GeoJSON vs simple format
        if "type" in data and data["type"] == "Polygon":
            # Standard GeoJSON: coordinates are [[[lon, lat], [lon, lat], ...]]
            if not coords or not coords[0]:
                raise ValueError("Invalid GeoJSON polygon coordinates")
            polygon_coords = coords[0]  # First ring (exterior boundary)
            polygon = Polygon(polygon_coords)
        else:
            # Simple format: coordinates are [[lat, lon], [lat, lon], ...]
            if not coords:
                raise ValueError("Invalid simple format coordinates")
            # Convert from [lat, lon] to [lon, lat] for Shapely
            polygon_coords = [(coord[1], coord[0]) for coord in coords]
            polygon = Polygon(polygon_coords)
        
        # Fix invalid polygon if needed
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
            if not polygon.is_valid:
                raise ValueError("Could not create valid polygon from coordinates")
        
        logger.info(f"Loaded polygon with {len(polygon.exterior.coords)} points")
        return polygon
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    except Exception as e:
        logger.error(f"Error loading polygon from {json_file_path}: {e}")
        raise

def is_point_in_polygon(lat: float, lon: float, polygon: Polygon) -> bool:
    """Check if a point (lat, lon) is inside a polygon using Shapely."""
    try:
        # Basic validation
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
        
        if not isinstance(polygon, Polygon):
            return False
        
        # Create point in Shapely format (lon, lat) and check
        point = Point(lon, lat)
        return polygon.contains(point)
        
    except Exception as e:
        logger.error(f"Error in polygon detection for point ({lat}, {lon}): {e}")
        return False

def validate_polygon_coordinates(polygon_coords: List[Tuple[float, float]]) -> bool:
    """Validate polygon coordinates for basic correctness."""
    try:
        if not polygon_coords or len(polygon_coords) < 3:
            return False
        
        for lat, lon in polygon_coords:
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return False
        
        return True
        
    except (TypeError, ValueError):
        return False

def create_polygon_from_geojson_dict(geojson_data: Dict[str, Any]) -> Polygon:
    """Create a Shapely Polygon from a GeoJSON dictionary."""
    try:
        if geojson_data.get("type") == "Polygon":
            return shape(geojson_data)
        else:
            coords = geojson_data.get("coordinates", [])
            if not coords:
                raise ValueError("No coordinates found in data")
            
            # Convert from [lat, lon] to [lon, lat] for Shapely
            polygon_coords = [(coord[1], coord[0]) for coord in coords]
            return Polygon(polygon_coords)
            
    except Exception as e:
        raise ValueError(f"Invalid GeoJSON data: {e}")

# Performance optimization: Cache loaded polygons
_polygon_cache: Dict[str, Polygon] = {}

def get_cached_polygon(json_file_path: str, force_reload: bool = False) -> Polygon:
    """Get a polygon from cache or load it if not cached."""
    cache_key = str(Path(json_file_path).absolute())
    
    if not force_reload and cache_key in _polygon_cache:
        return _polygon_cache[cache_key]
    
    polygon = load_polygon_from_geojson(json_file_path)
    _polygon_cache[cache_key] = polygon
    
    return polygon

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Euclidean distance.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point  
        lat2: Latitude of second point
        lon2: Longitude of second point
        
    Returns:
        float: Distance in coordinate units
    """
    try:
        # Basic validation
        if not all(-90 <= lat <= 90 for lat in [lat1, lat2]):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not all(-180 <= lon <= 180 for lon in [lon1, lon2]):
            raise ValueError("Longitude must be between -180 and 180 degrees")
        
        # Calculate Euclidean distance
        lat_diff = lat2 - lat1
        lon_diff = lon2 - lon1
        distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5
        
        return distance
        
    except Exception as e:
        logger.error(f"Error calculating distance between ({lat1}, {lon1}) and ({lat2}, {lon2}): {e}")
        raise

def is_within_proximity(lat1: float, lon1: float, lat2: float, lon2: float, threshold: float) -> bool:
    """Check if two points are within a specified proximity threshold.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point  
        lon2: Longitude of second point
        threshold: Maximum allowed distance
        
    Returns:
        bool: True if points are within threshold, False otherwise
    """
    try:
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        return distance <= threshold
        
    except Exception as e:
        logger.error(f"Error checking proximity: {e}")
        return False
