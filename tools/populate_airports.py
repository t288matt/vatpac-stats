#!/usr/bin/env python3
"""
Populate airport_config table from airport_coordinates.json

This script reads the airport_coordinates.json file and populates the airport_config
table with Australian airports, eliminating the need for hardcoded airport lists
in dashboards and queries.
"""

import json
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from config import get_config
from database import get_db


def load_airport_coordinates():
    """Load airport coordinates from JSON file."""
    try:
        project_root = Path(__file__).parent.parent
        airport_file = project_root / "airport_coordinates.json"
        
        with open(airport_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading airport coordinates: {e}")
        return {}


def get_australian_airports(airport_data):
    """Extract Australian airports from airport data."""
    australian_airports = {}
    for airport_code, airport_info in airport_data.items():
        if airport_code.startswith('Y'):
            australian_airports[airport_code] = airport_info
    return australian_airports


def populate_airport_config():
    """Populate the airport_config table with Australian airports."""
    config = get_config()
    
    # Create database engine (handle SQLite differently)
    if config.database.url.startswith('sqlite'):
        engine = create_engine(config.database.url)
    else:
        engine = create_engine(
            config.database.url,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            echo=config.database.echo
        )
    
    # Load airport data
    airport_data = load_airport_coordinates()
    if not airport_data:
        print("No airport data loaded. Exiting.")
        return
    
    australian_airports = get_australian_airports(airport_data)
    print(f"Found {len(australian_airports)} Australian airports")
    
    # Clear existing Australian airports
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM airport_config WHERE icao_code LIKE 'Y%'"))
        print("Cleared existing Australian airports from database")
    
    # Insert Australian airports
    with engine.begin() as conn:
        for airport_code, airport_info in australian_airports.items():
            # Extract coordinates
            lat = airport_info.get('latitude')
            lng = airport_info.get('longitude')
            
            if lat is not None and lng is not None:
                # Insert airport data
                insert_query = text("""
                    INSERT INTO airport_config 
                    (icao_code, name, latitude, longitude, region)
                    VALUES (:icao_code, :name, :latitude, :longitude, :region)
                """)
                
                conn.execute(insert_query, {
                    'icao_code': airport_code,
                    'name': f"{airport_code} Airport",  # Generic name since JSON doesn't have names
                    'latitude': lat,
                    'longitude': lng,
                    'region': 'Australia'  # Could be enhanced with state mapping
                })
        
        print(f"Successfully inserted {len(australian_airports)} Australian airports")
    
    # Verify the data
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT icao_code, name, latitude, longitude, region
            FROM airport_config 
            WHERE icao_code LIKE 'Y%'
            ORDER BY icao_code
        """))
        
        airports = result.fetchall()
        print(f"\nVerification - Found {len(airports)} airports in database:")
        for airport in airports:
            print(f"  {airport.icao_code}: {airport.name} ({airport.latitude}, {airport.longitude})")


def main():
    """Main function."""
    print("Populating airport_config table with Australian airports...")
    populate_airport_config()
    print("Done!")


if __name__ == "__main__":
    main() 