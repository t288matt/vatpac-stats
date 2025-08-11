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
