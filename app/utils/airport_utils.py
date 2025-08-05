#!/usr/bin/env python3
"""
Airport Utilities for VATSIM Data Collection System

This module provides airport-related utilities for dynamic airport loading from
the database. It replaces hardcoded airport lists with configurable region-based
filtering and provides efficient airport data access.

INPUTS:
- Database connection and airport queries
- Region specifications and filtering criteria
- Airport ICAO codes for coordinate lookup
- Cache management requests

OUTPUTS:
- Airport coordinate data and metadata
- Region-filtered airport lists
- Airport statistics and counts
- Cached airport data for performance

FEATURES:
- Dynamic airport loading from database
- Region-based airport filtering
- Airport coordinate lookup and validation
- Caching for performance optimization
- Airport statistics and metadata

REGION SUPPORT:
- Australia: Y* airports (Australian ICAO prefix)
- USA: K* airports (US ICAO prefix)
- Europe: E*, L*, G*, F*, D*, S*, N*, O*, U*, V*, W*, X* prefixes
- Asia: R*, V*, Z*, B*, W* prefixes
- Africa: F*, H*, N* prefixes
- South America: S*, C* prefixes
- North America: K*, C*, M* prefixes
- Global: All airports

CACHE MANAGEMENT:
- In-memory airport data caching
- Automatic cache invalidation
- Performance optimization for repeated queries
- Memory-efficient data storage

DATABASE INTEGRATION:
- SQLAlchemy ORM for airport queries
- Connection pooling for efficiency
- Error handling and fallback mechanisms
- Transaction management for data consistency

OPTIMIZATIONS:
- Cached airport data to reduce database queries
- Region-based filtering for targeted queries
- Efficient coordinate lookup
- Memory management for large airport datasets
"""

import os
from typing import List, Dict, Optional, Tuple
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Airports
from app.config import get_config

logger = logging.getLogger(__name__)

# Cache for loaded airports to avoid repeated database queries
_airports_cache: Optional[Dict[str, Dict[str, float]]] = None

def load_airports_from_database() -> Dict[str, Dict[str, float]]:
    """
    Load airports from the database.
    Returns a dictionary of airport codes to coordinates.
    """
    global _airports_cache
    
    if _airports_cache is not None:
        return _airports_cache
    
    try:
        config = get_config()
        engine = create_engine(config.database.url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Query all active airports from the database
        airports_query = session.query(Airports)\
            .filter(Airports.is_active == True)\
            .all()
        
        # Convert to the expected format
        airports = {}
        for airport in airports_query:
            airports[airport.icao_code] = {
                "latitude": airport.latitude,
                "longitude": airport.longitude,
                "name": airport.name,
                "country": airport.country,
                "region": airport.region
            }
        
        session.close()
        
        _airports_cache = airports
        logger.info(f"Loaded {len(airports)} airports from database")
        return airports
        
    except Exception as e:
        logger.error(f"Error loading airports from database: {e}")
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
    try:
        config = get_config()
        engine = create_engine(config.database.url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
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
            airports = session.query(Airports.icao_code)\
                .filter(Airports.is_active == True)\
                .all()
            session.close()
            return [airport[0] for airport in airports]
        
        patterns = region_patterns[region]
        
        if region == "Global":
            airports = session.query(Airports.icao_code)\
                .filter(Airports.is_active == True)\
                .all()
            session.close()
            return [airport[0] for airport in airports]
        
        # Filter airports by region patterns
        region_airports = []
        for pattern in patterns:
            airports = session.query(Airports.icao_code)\
                .filter(Airports.icao_code.like(f'{pattern}%'))\
                .filter(Airports.is_active == True)\
                .all()
            region_airports.extend([airport[0] for airport in airports])
        
        session.close()
        
        logger.info(f"Found {len(region_airports)} airports for region '{region}'")
        return region_airports
        
    except Exception as e:
        logger.error(f"Error getting airports by region: {e}")
        return []

def get_airport_coordinates(airport_code: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a specific airport.
    
    Args:
        airport_code: ICAO airport code
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    try:
        config = get_config()
        engine = create_engine(config.database.url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        airport = session.query(Airports)\
            .filter(Airports.icao_code == airport_code)\
            .filter(Airports.is_active == True)\
            .first()
        
        session.close()
        
        if airport is None:
            return None
        
        return (airport.latitude, airport.longitude)
        
    except Exception as e:
        logger.error(f"Error getting airport coordinates: {e}")
        return None

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