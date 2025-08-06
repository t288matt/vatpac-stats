#!/usr/bin/env python3
"""
Airport Coordinate Validation Script (Database Version)

This script validates the accuracy of our coordinate conversion from Airspace.xml
against publicly available airport data for 20 major Australian airports.
Accuracy within 3km is considered acceptable.

Usage:
    python tools/validate_airport_coordinates_db.py
"""

import math
import os
import sys
from typing import Dict, List, Tuple, Optional
import logging

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models import Airports

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points using the Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in kilometers
    radius = 6371
    
    return radius * c

def get_public_airport_data() -> Dict[str, Dict]:
    """
    Get publicly available airport coordinates for major Australian airports.
    
    Returns:
        Dictionary of airport data with ICAO codes as keys
    """
    # Major Australian airports with publicly available coordinates
    airports = {
        'YSSY': {  # Sydney Airport
            'name': 'Sydney Airport',
            'public_lat': -33.9399,
            'public_lon': 151.1753,
            'source': 'Wikipedia'
        },
        'YBBN': {  # Brisbane Airport
            'name': 'Brisbane Airport',
            'public_lat': -27.3842,
            'public_lon': 153.1175,
            'source': 'Wikipedia'
        },
        'YMML': {  # Melbourne Airport
            'name': 'Melbourne Airport',
            'public_lat': -37.8136,
            'public_lon': 144.9631,
            'source': 'Wikipedia'
        },
        'YPPH': {  # Perth Airport
            'name': 'Perth Airport',
            'public_lat': -31.9403,
            'public_lon': 115.9670,
            'source': 'Wikipedia'
        },
        'YBCS': {  # Cairns Airport
            'name': 'Cairns Airport',
            'public_lat': -16.8858,
            'public_lon': 145.7553,
            'source': 'Wikipedia'
        },
        'YPDN': {  # Darwin Airport
            'name': 'Darwin Airport',
            'public_lat': -12.4081,
            'public_lon': 130.8728,
            'source': 'Wikipedia'
        },
        'YSCB': {  # Canberra Airport
            'name': 'Canberra Airport',
            'public_lat': -35.3069,
            'public_lon': 149.1950,
            'source': 'Wikipedia'
        },
        'YMHB': {  # Hobart Airport
            'name': 'Hobart Airport',
            'public_lat': -42.8361,
            'public_lon': 147.5103,
            'source': 'Wikipedia'
        },
        'YBAF': {  # Brisbane West Wellcamp Airport
            'name': 'Brisbane West Wellcamp Airport',
            'public_lat': -27.4094,
            'public_lon': 151.8083,
            'source': 'Wikipedia'
        },
        'YBCG': {  # Gold Coast Airport
            'name': 'Gold Coast Airport',
            'public_lat': -28.1644,
            'public_lon': 153.5047,
            'source': 'Wikipedia'
        },
        'YMAV': {  # Avalon Airport
            'name': 'Avalon Airport',
            'public_lat': -38.0394,
            'public_lon': 144.4689,
            'source': 'Wikipedia'
        },
        'YPAD': {  # Adelaide Airport
            'name': 'Adelaide Airport',
            'public_lat': -34.9454,
            'public_lon': 138.5306,
            'source': 'Wikipedia'
        },
        'YBRK': {  # Rockhampton Airport
            'name': 'Rockhampton Airport',
            'public_lat': -23.3819,
            'public_lon': 150.4753,
            'source': 'Wikipedia'
        },
        'YARM': {  # Armidale Airport
            'name': 'Armidale Airport',
            'public_lat': -30.5281,
            'public_lon': 151.6172,
            'source': 'Wikipedia'
        },
        'YAPH': {  # Alpha Airport
            'name': 'Alpha Airport',
            'public_lat': -23.6467,
            'public_lon': 146.5833,
            'source': 'Wikipedia'
        },
        'YAUG': {  # Augusta Airport
            'name': 'Augusta Airport',
            'public_lat': -34.3153,
            'public_lon': 115.1653,
            'source': 'Wikipedia'
        },
        'YAUR': {  # Aurukun Airport
            'name': 'Aurukun Airport',
            'public_lat': -13.3539,
            'public_lon': 141.7208,
            'source': 'Wikipedia'
        },
        'YARG': {  # Argyle Airport
            'name': 'Argyle Airport',
            'public_lat': -16.6369,
            'public_lon': 128.4514,
            'source': 'Wikipedia'
        },
        'YARK': {  # Arkaroola Airport
            'name': 'Arkaroola Airport',
            'public_lat': -30.3181,
            'public_lon': 139.3258,
            'source': 'Wikipedia'
        },
        'YARA': {  # Ararat Airport
            'name': 'Ararat Airport',
            'public_lat': -37.3094,
            'public_lon': 142.9889,
            'source': 'Wikipedia'
        }
    }
    
    return airports

def get_airport_from_db(icao_code: str) -> Optional[Dict]:
    """
    Get airport data from the database.
    
    Args:
        icao_code: ICAO code to search for
        
    Returns:
        Airport data dictionary or None if not found
    """
    db = SessionLocal()
    try:
        airport = db.query(Airports).filter(Airports.icao_code == icao_code).first()
        if airport:
            return {
                'icao_code': airport.icao_code,
                'name': airport.name,
                'latitude': airport.latitude,
                'longitude': airport.longitude,
                'elevation': airport.elevation
            }
        return None
    except Exception as e:
        logger.error(f"Database error for {icao_code}: {e}")
        return None
    finally:
        db.close()

def validate_airport_coordinates() -> None:
    """
    Validate airport coordinates against publicly available data.
    """
    # Get public airport data
    public_airports = get_public_airport_data()
    
    logger.info("Starting airport coordinate validation...")
    logger.info(f"Validating {len(public_airports)} airports against public data")
    
    results = []
    total_distance = 0
    valid_count = 0
    
    for icao_code, public_data in public_airports.items():
        # Get airport from database
        db_airport = get_airport_from_db(icao_code)
        
        if db_airport is None:
            logger.warning(f"Airport {icao_code} not found in database")
            continue
        
        # Calculate distance
        distance = calculate_distance(
            db_airport['latitude'], db_airport['longitude'],
            public_data['public_lat'], public_data['public_lon']
        )
        
        # Check if within 3km accuracy
        is_accurate = distance <= 3.0
        if is_accurate:
            valid_count += 1
        
        total_distance += distance
        
        result = {
            'icao_code': icao_code,
            'name': public_data['name'],
            'db_lat': db_airport['latitude'],
            'db_lon': db_airport['longitude'],
            'public_lat': public_data['public_lat'],
            'public_lon': public_data['public_lon'],
            'distance_km': distance,
            'is_accurate': is_accurate,
            'source': public_data['source']
        }
        
        results.append(result)
        
        # Log result
        status = "✅ ACCURATE" if is_accurate else "❌ INACCURATE"
        logger.info(f"{status} {icao_code} ({public_data['name']}): {distance:.2f}km")
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*80)
    
    accuracy_percentage = (valid_count / len(results)) * 100 if results else 0
    avg_distance = total_distance / len(results) if results else 0
    
    logger.info(f"Total airports validated: {len(results)}")
    logger.info(f"Accurate (≤3km): {valid_count}")
    logger.info(f"Inaccurate (>3km): {len(results) - valid_count}")
    logger.info(f"Accuracy rate: {accuracy_percentage:.1f}%")
    logger.info(f"Average distance: {avg_distance:.2f}km")
    
    if accuracy_percentage >= 80:
        logger.info("🎉 VALIDATION PASSED: Coordinate conversion is accurate!")
    else:
        logger.warning("⚠️  VALIDATION FAILED: Coordinate conversion needs improvement")
    
    # Print detailed results
    logger.info("\n" + "="*80)
    logger.info("DETAILED RESULTS")
    logger.info("="*80)
    
    for result in sorted(results, key=lambda x: x['distance_km'], reverse=True):
        status = "✅" if result['is_accurate'] else "❌"
        logger.info(f"{status} {result['icao_code']:6} {result['name']:25} "
                   f"Distance: {result['distance_km']:6.2f}km "
                   f"({result['db_lat']:8.4f}, {result['db_lon']:8.4f}) -> "
                   f"({result['public_lat']:8.4f}, {result['public_lon']:8.4f})")

def main():
    """Main function to validate airport coordinates."""
    validate_airport_coordinates()

if __name__ == "__main__":
    main() 