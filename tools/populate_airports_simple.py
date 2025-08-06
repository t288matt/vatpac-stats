#!/usr/bin/env python3
"""
Simple Airport Population Script for Docker Environment

This script extracts airport data from the Airspace.xml file and populates
the airports table in the database. Designed to work in the Docker environment.
"""

import xml.etree.ElementTree as ET
import os
import sys
import logging
from typing import Dict, List, Tuple, Optional

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models import Airports

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_position(position_str: str) -> Tuple[float, float]:
    """
    Parse the position string from Airspace.xml format to latitude/longitude.
    
    The format appears to be: "-DDMMSS.SSS+DDDMMSS.SSS" where:
    - First part is latitude (negative for South)
    - Second part is longitude (positive for East)
    - Format is DDMMSS.SSS (degrees, minutes, seconds)
    
    Args:
        position_str: Position string in format "-DDMMSS.SSS+DDDMMSS.SSS"
        
    Returns:
        Tuple of (latitude, longitude) in decimal degrees
    """
    try:
        # Remove any whitespace
        position_str = position_str.strip()
        
        # Split by '+' to separate lat and lon
        parts = position_str.split('+')
        if len(parts) != 2:
            raise ValueError(f"Invalid position format: {position_str}")
        
        lat_part = parts[0]  # e.g., "-273826.000"
        lon_part = parts[1]  # e.g., "1524243.000"
        
        # Parse latitude
        lat_sign = -1 if lat_part.startswith('-') else 1
        lat_abs = lat_part.replace('-', '')
        
        # Convert DDMMSS.SSS format to decimal degrees
        lat_deg = float(lat_abs[:2])  # Degrees
        lat_min = float(lat_abs[2:4])  # Minutes
        lat_sec = float(lat_abs[4:])  # Seconds
        latitude = lat_sign * (lat_deg + lat_min/60 + lat_sec/3600)
        
        # Parse longitude
        lon_deg = float(lon_part[:3])  # Degrees (longitude can be 3 digits)
        lon_min = float(lon_part[3:5])  # Minutes
        lon_sec = float(lon_part[5:])  # Seconds
        longitude = lon_deg + lon_min/60 + lon_sec/3600
        
        return latitude, longitude
        
    except Exception as e:
        logger.error(f"Error parsing position '{position_str}': {e}")
        return None, None

def extract_airport_data(xml_file_path: str) -> List[Dict]:
    """
    Extract airport data from the Airspace.xml file.
    
    Args:
        xml_file_path: Path to the Airspace.xml file
        
    Returns:
        List of airport data dictionaries
    """
    airports_data = []
    
    try:
        # Parse the XML file
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Find all airport elements
        for airport_elem in root.findall('.//Airport'):
            icao_code = airport_elem.get('ICAO')
            full_name = airport_elem.get('FullName')
            position = airport_elem.get('Position')
            elevation = airport_elem.get('Elevation')
            
            if icao_code and position:
                latitude, longitude = parse_position(position)
                if latitude is not None and longitude is not None:
                    airport_data = {
                        'icao_code': icao_code,
                        'name': full_name or '',
                        'latitude': latitude,
                        'longitude': longitude,
                        'elevation': float(elevation) if elevation else 0
                    }
                    airports_data.append(airport_data)
        
        logger.info(f"Successfully extracted {len(airports_data)} airports from XML")
        return airports_data
        
    except Exception as e:
        logger.error(f"Error extracting airport data: {e}")
        return []

def populate_airports_table(airports_data: List[Dict]) -> bool:
    """
    Populate the airports table with extracted data.
    
    Args:
        airports_data: List of airport data dictionaries
        
    Returns:
        True if successful, False otherwise
    """
    db = SessionLocal()
    
    try:
        # Clear existing data (optional - comment out if you want to keep existing data)
        db.query(Airports).delete()
        logger.info("Cleared existing airports data")
        
        # Insert new airport data
        for airport_data in airports_data:
            airport = Airports(**airport_data)
            db.add(airport)
        
        db.commit()
        logger.info(f"Successfully inserted {len(airports_data)} airports")
        
        # Verify the insertion
        count = db.query(Airports).count()
        logger.info(f"Total airports in database: {count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

def main():
    """Main function to extract and populate airport data."""
    # Path to the Airspace.xml file (corrected for Docker environment)
    xml_file_path = "app/utils/Airspace.xml"
    
    if not os.path.exists(xml_file_path):
        logger.error(f"Airspace.xml file not found at: {xml_file_path}")
        return
    
    logger.info("Starting airport data extraction and population...")
    
    # Extract airport data from XML
    airports_data = extract_airport_data(xml_file_path)
    
    if not airports_data:
        logger.error("No airport data extracted from XML")
        return
    
    # Populate the database
    success = populate_airports_table(airports_data)
    
    if success:
        logger.info("✅ Airport population completed successfully!")
    else:
        logger.error("❌ Airport population failed!")

if __name__ == "__main__":
    main() 