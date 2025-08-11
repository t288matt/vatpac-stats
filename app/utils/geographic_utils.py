#!/usr/bin/env python3
"""
Geographic Utilities Module

This module provides utilities for geographic boundary filtering using polygon-based
airspace definitions. It supports GeoJSON format files and uses Shapely for
efficient polygon calculations.

Author: VATSIM Data System
Created: 2025-01-08
Status: Sprint 1, Task 1.2 - Geographic Utilities Module
"""

import json
import logging
from typing import List, Tuple, Dict, Any, Optional
from shapely.geometry import Point, Polygon, shape
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def load_polygon_from_geojson(json_file_path: str) -> Polygon:
    """
    Load polygon from GeoJSON file and return Shapely Polygon object.
    
    Supports multiple GeoJSON formats:
    1. Standard GeoJSON: {"type": "Polygon", "coordinates": [[[lon, lat], ...]]}
    2. Simple format: {"coordinates": [[lat, lon], [lat, lon], ...]}
    
    Args:
        json_file_path: Path to GeoJSON file with polygon coordinates
        
    Returns:
        Shapely Polygon object ready for point-in-polygon testing
        
    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        ValueError: If JSON format is invalid or unsupported
        TypeError: If coordinates are not properly formatted
    """
    try:
        file_path = Path(json_file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"GeoJSON file not found: {json_file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if "coordinates" not in data:
            raise ValueError("JSON file must contain 'coordinates' key")
        
        coords = data["coordinates"]
        
        # Detect GeoJSON format vs simple format
        if "type" in data and data["type"] == "Polygon":
            logger.info("📍 Detected GeoJSON format")
            # Standard GeoJSON: coordinates are [[[lon, lat], [lon, lat], ...]]
            if not coords or not coords[0]:
                raise ValueError("Invalid GeoJSON polygon coordinates")
            polygon_coords = coords[0]  # First ring (exterior boundary)
            # GeoJSON is already in [lon, lat] format for Shapely
            polygon = Polygon(polygon_coords)
        else:
            logger.info("📍 Detected simple coordinate format")
            # Simple format: coordinates are [[lat, lon], [lat, lon], ...]
            if not coords:
                raise ValueError("Invalid simple format coordinates")
            # Convert from [lat, lon] to [lon, lat] for Shapely
            polygon_coords = [(coord[1], coord[0]) for coord in coords]
            polygon = Polygon(polygon_coords)
        
        # Validate the polygon
        if not polygon.is_valid:
            logger.warning(f"Invalid polygon detected, attempting to fix with buffer")
            polygon = polygon.buffer(0)
            if not polygon.is_valid:
                raise ValueError("Could not create valid polygon from coordinates")
        
        logger.info(f"✅ Loaded polygon with {len(polygon.exterior.coords)} points")
        return polygon
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    except Exception as e:
        logger.error(f"Error loading polygon from {json_file_path}: {e}")
        raise

def is_point_in_polygon(lat: float, lon: float, polygon: Polygon) -> bool:
    """
    Check if a point (lat, lon) is inside a polygon using Shapely.
    
    Args:
        lat: Latitude in decimal degrees (-90 to 90)
        lon: Longitude in decimal degrees (-180 to 180)
        polygon: Shapely Polygon object
        
    Returns:
        True if point is inside the polygon, False otherwise
        
    Raises:
        ValueError: If coordinates are invalid
        TypeError: If polygon is not a Shapely Polygon
    """
    try:
        # Validate inputs
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError("Latitude and longitude must be numeric")
        
        if not (-90 <= lat <= 90):
            raise ValueError(f"Invalid latitude: {lat} (must be -90 to 90)")
        
        if not (-180 <= lon <= 180):
            raise ValueError(f"Invalid longitude: {lon} (must be -180 to 180)")
        
        if not isinstance(polygon, Polygon):
            raise TypeError("polygon must be a Shapely Polygon object")
        
        # Create point in Shapely format (lon, lat)
        point = Point(lon, lat)
        
        # Check if point is inside polygon
        return polygon.contains(point)
        
    except Exception as e:
        logger.error(f"Error in polygon detection for point ({lat}, {lon}): {e}")
        return False

def is_point_in_polygon_from_coords(lat: float, lon: float, polygon_coords: List[Tuple[float, float]]) -> bool:
    """
    Check if a point (lat, lon) is inside a polygon defined by coordinate list.
    
    This is a convenience function that creates a Polygon from coordinates
    and then checks point inclusion.
    
    Args:
        lat: Latitude in decimal degrees (-90 to 90)
        lon: Longitude in decimal degrees (-180 to 180)
        polygon_coords: List of (lat, lon) tuples defining the polygon
        
    Returns:
        True if point is inside the polygon, False otherwise
        
    Raises:
        ValueError: If coordinates are invalid
        TypeError: If polygon_coords is not properly formatted
    """
    try:
        # Validate inputs
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError("Latitude and longitude must be numeric")
        
        if not polygon_coords or len(polygon_coords) < 3:
            raise ValueError("Polygon must have at least 3 points")
        
        # Convert polygon coordinates from (lat, lon) to (lon, lat) for Shapely
        shapely_coords = [(coord[1], coord[0]) for coord in polygon_coords]
        polygon = Polygon(shapely_coords)
        
        if not polygon.is_valid:
            logger.warning(f"Invalid polygon detected, using buffer to fix")
            polygon = polygon.buffer(0)
        
        # Use the main function
        return is_point_in_polygon(lat, lon, polygon)
        
    except Exception as e:
        logger.error(f"Error in polygon detection: {e}")
        return False

def validate_polygon_coordinates(polygon_coords: List[Tuple[float, float]]) -> bool:
    """
    Validate polygon coordinates for basic correctness.
    
    Args:
        polygon_coords: List of (lat, lon) tuples
        
    Returns:
        True if coordinates are valid, False otherwise
    """
    try:
        if not polygon_coords or len(polygon_coords) < 3:
            logger.warning("Polygon must have at least 3 points")
            return False
        
        for i, (lat, lon) in enumerate(polygon_coords):
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                logger.warning(f"Non-numeric coordinates at index {i}: ({lat}, {lon})")
                return False
            
            if not (-90 <= lat <= 90):
                logger.warning(f"Invalid latitude at index {i}: {lat} (must be -90 to 90)")
                return False
            
            if not (-180 <= lon <= 180):
                logger.warning(f"Invalid longitude at index {i}: {lon} (must be -180 to 180)")
                return False
        
        # Check if polygon is closed (first and last points are the same)
        if polygon_coords[0] != polygon_coords[-1]:
            logger.info("Polygon is not closed (first != last point), but this is acceptable")
        
        return True
        
    except (TypeError, ValueError) as e:
        logger.warning(f"Error validating polygon coordinates: {e}")
        return False

def validate_geojson_polygon(json_file_path: str) -> bool:
    """
    Validate a GeoJSON polygon file without loading it into memory.
    
    Args:
        json_file_path: Path to GeoJSON file
        
    Returns:
        True if file is valid, False otherwise
    """
    try:
        file_path = Path(json_file_path)
        if not file_path.exists():
            logger.error(f"File not found: {json_file_path}")
            return False
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check required fields
        if "coordinates" not in data:
            logger.error("Missing 'coordinates' field in JSON")
            return False
        
        coords = data["coordinates"]
        
        # Validate based on format
        if "type" in data and data["type"] == "Polygon":
            # GeoJSON format validation
            if not isinstance(coords, list) or not coords:
                logger.error("Invalid GeoJSON coordinates structure")
                return False
            
            if not isinstance(coords[0], list) or len(coords[0]) < 3:
                logger.error("GeoJSON polygon must have at least 3 coordinate pairs")
                return False
            
            # Validate coordinate pairs
            for coord in coords[0]:
                if not isinstance(coord, list) or len(coord) != 2:
                    logger.error("Each coordinate must be [lon, lat] pair")
                    return False
                
                lon, lat = coord
                if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                    logger.error(f"Invalid coordinates: [{lon}, {lat}]")
                    return False
        else:
            # Simple format validation
            if not isinstance(coords, list) or len(coords) < 3:
                logger.error("Simple format must have at least 3 coordinate pairs")
                return False
            
            # Validate coordinate pairs
            for coord in coords:
                if not isinstance(coord, list) or len(coord) != 2:
                    logger.error("Each coordinate must be [lat, lon] pair")
                    return False
                
                lat, lon = coord
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    logger.error(f"Invalid coordinates: [{lat}, {lon}]")
                    return False
        
        logger.info(f"✅ GeoJSON file validation passed: {json_file_path}")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        return False
    except Exception as e:
        logger.error(f"Error validating GeoJSON file: {e}")
        return False

def create_polygon_from_geojson_dict(geojson_data: Dict[str, Any]) -> Polygon:
    """
    Create a Shapely Polygon from a GeoJSON dictionary.
    
    Args:
        geojson_data: Dictionary containing GeoJSON polygon data
        
    Returns:
        Shapely Polygon object
        
    Raises:
        ValueError: If GeoJSON data is invalid
    """
    try:
        if geojson_data.get("type") == "Polygon":
            # Use Shapely's shape function for standard GeoJSON
            return shape(geojson_data)
        else:
            # Handle simple format
            coords = geojson_data.get("coordinates", [])
            if not coords:
                raise ValueError("No coordinates found in data")
            
            # Convert from [lat, lon] to [lon, lat] for Shapely
            polygon_coords = [(coord[1], coord[0]) for coord in coords]
            return Polygon(polygon_coords)
            
    except Exception as e:
        logger.error(f"Error creating polygon from GeoJSON data: {e}")
        raise ValueError(f"Invalid GeoJSON data: {e}")

# Performance optimization: Cache loaded polygons
_polygon_cache: Dict[str, Polygon] = {}

def get_cached_polygon(json_file_path: str, force_reload: bool = False) -> Polygon:
    """
    Get a polygon from cache or load it if not cached.
    
    Args:
        json_file_path: Path to GeoJSON file
        force_reload: If True, reload even if cached
        
    Returns:
        Shapely Polygon object
    """
    cache_key = str(Path(json_file_path).absolute())
    
    if not force_reload and cache_key in _polygon_cache:
        logger.debug(f"Using cached polygon for {json_file_path}")
        return _polygon_cache[cache_key]
    
    logger.info(f"Loading polygon from {json_file_path}")
    polygon = load_polygon_from_geojson(json_file_path)
    _polygon_cache[cache_key] = polygon
    
    return polygon
