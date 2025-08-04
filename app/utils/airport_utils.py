#!/usr/bin/env python3
"""
Airport utilities for dynamic airport loading from JSON database.
Replaces hardcoded airport lists with configurable region-based filtering.
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Cache for loaded airports to avoid repeated file reads
_airports_cache: Optional[Dict[str, Dict[str, float]]] = None

def load_airports_from_json() -> Dict[str, Dict[str, float]]:
    """
    Load airports from the JSON database file.
    Returns a dictionary of airport codes to coordinates.
    """
    global _airports_cache
    
    if _airports_cache is not None:
        return _airports_cache
    
    try:
        # Try to find the airport coordinates file
        json_path = Path("airport_coordinates.json")
        if not json_path.exists():
            # Try relative to app directory
            json_path = Path("app/airport_coordinates.json")
        if not json_path.exists():
            # Try in parent directory
            json_path = Path("../airport_coordinates.json")
        
        if not json_path.exists():
            logger.warning("airport_coordinates.json not found, using empty database")
            _airports_cache = {}
            return _airports_cache
        
        with open(json_path, 'r') as f:
            airports = json.load(f)
        
        _airports_cache = airports
        logger.info(f"Loaded {len(airports)} airports from database")
        return airports
        
    except Exception as e:
        logger.error(f"Error loading airports from JSON: {e}")
        _airports_cache = {}
        return _airports_cache

def get_airports_by_region(region: str = "Australia") -> List[str]:
    """
    Get airports for a specific region based on ICAO code patterns.
    
    Args:
        region: Region name (e.g., "Australia", "USA", "Europe")
    
    Returns:
        List of airport ICAO codes for the region
    """
    airports = load_airports_from_json()
    
    if not airports:
        logger.warning("No airports loaded, returning empty list")
        return []
    
    # Define region patterns based on ICAO code prefixes
    region_patterns = {
        "Australia": ["Y"],  # Australian airports start with Y
        "USA": ["K"],        # US airports start with K
        "Europe": ["E", "L", "G", "F", "D", "S", "N", "O", "U", "V", "W", "X"],  # European prefixes
        "Asia": ["R", "V", "Z", "B", "W"],  # Asian prefixes
        "Africa": ["F", "H", "N"],  # African prefixes
        "South America": ["S", "C"],  # South American prefixes
        "North America": ["K", "C", "M"],  # North American prefixes
        "Global": []  # All airports
    }
    
    if region not in region_patterns:
        logger.warning(f"Unknown region '{region}', using all airports")
        return list(airports.keys())
    
    patterns = region_patterns[region]
    
    if region == "Global":
        return list(airports.keys())
    
    # Filter airports by region patterns
    region_airports = []
    for airport_code in airports.keys():
        for pattern in patterns:
            if airport_code.startswith(pattern):
                region_airports.append(airport_code)
                break
    
    logger.info(f"Found {len(region_airports)} airports for region '{region}'")
    return region_airports

def get_airport_coordinates(airport_code: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a specific airport.
    
    Args:
        airport_code: ICAO airport code
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    airports = load_airports_from_json()
    
    if airport_code not in airports:
        return None
    
    coords = airports[airport_code]
    return (coords["latitude"], coords["longitude"])

def is_airport_in_region(airport_code: str, region: str = "Australia") -> bool:
    """
    Check if an airport is in the specified region.
    
    Args:
        airport_code: ICAO airport code
        region: Region name
    
    Returns:
        True if airport is in the region, False otherwise
    """
    region_airports = get_airports_by_region(region)
    return airport_code in region_airports

def get_region_statistics(region: str = "Australia") -> Dict[str, int]:
    """
    Get statistics about airports in a region.
    
    Args:
        region: Region name
    
    Returns:
        Dictionary with region statistics
    """
    airports = get_airports_by_region(region)
    
    return {
        "region": region,
        "total_airports": len(airports),
        "airports": airports
    }

def clear_airports_cache():
    """Clear the airports cache to force reload."""
    global _airports_cache
    _airports_cache = None
    logger.info("Airports cache cleared") 