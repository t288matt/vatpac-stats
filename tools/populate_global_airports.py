#!/usr/bin/env python3
"""
Populate Global Airports Table
==============================

This script populates the airports table with all global airports from
airport_coordinates.json, making it the single source of truth for all
airport data in the system.

Usage:
    python tools/populate_global_airports.py
"""

import json
import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.models import Airports
from app.config import get_config


def load_airport_data():
    """Load airport data from airport_coordinates.json"""
    try:
        project_root = Path(__file__).parent.parent
        airport_file = project_root / "airport_coordinates.json"
        
        with open(airport_file, 'r') as f:
            airport_data = json.load(f)
        
        print(f"Loaded {len(airport_data)} airports from {airport_file}")
        return airport_data
    except Exception as e:
        print(f"Error loading airport data: {e}")
        return None


def determine_country_from_icao(icao_code):
    """Determine country from ICAO code prefix"""
    if not icao_code or len(icao_code) < 2:
        return None
    
    # Common ICAO prefixes by country/region
    country_mapping = {
        'K': 'United States',
        'Y': 'Australia',
        'C': 'Canada',
        'E': 'Europe',
        'L': 'Europe',
        'G': 'United Kingdom',
        'F': 'France',
        'D': 'Germany',
        'E': 'Spain',
        'L': 'Italy',
        'P': 'Poland',
        'U': 'Russia',
        'Z': 'China',
        'R': 'Japan',
        'V': 'India',
        'W': 'Indonesia',
        'S': 'Brazil',
        'M': 'Mexico',
        'N': 'New Zealand',
        'A': 'Argentina',
        'H': 'Kenya',
        'O': 'Saudi Arabia',
        'T': 'Thailand',
        'V': 'Vietnam',
        'X': 'Mexico',
        'B': 'Iceland',
        'J': 'Japan',
        'Q': 'Chile',
        'R': 'South Korea',
        'S': 'Sweden',
        'T': 'Turkey',
        'U': 'Ukraine',
        'V': 'Venezuela',
        'W': 'Malaysia',
        'X': 'Mexico',
        'Y': 'Australia',
        'Z': 'South Africa'
    }
    
    prefix = icao_code[:1]
    return country_mapping.get(prefix, 'Unknown')


def determine_region_from_icao(icao_code):
    """Determine region/state from ICAO code for known countries"""
    if not icao_code or len(icao_code) < 3:
        return None
    
    # Australian regions (Y*)
    if icao_code.startswith('Y'):
        australian_regions = {
            'YB': 'Queensland',
            'YS': 'New South Wales', 
            'YM': 'Victoria',
            'YP': 'Western Australia',
            'YSC': 'South Australia',
            'YPD': 'Northern Territory',
            'YBR': 'Tasmania'
        }
        prefix = icao_code[:3]
        return australian_regions.get(prefix, 'Australia')
    
    # US regions (K*)
    elif icao_code.startswith('K'):
        # This is simplified - US has more complex regional codes
        return 'United States'
    
    return None


def populate_airports_table(airport_data):
    """Populate the airports table with global airport data"""
    try:
        # Get database configuration
        config = get_config()
        engine = create_engine(config.database.url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Clear existing airports
        session.execute(text("DELETE FROM airports"))
        session.commit()
        print("Cleared existing airports from database")
        
        # Insert all airports
        airports_to_insert = []
        
        for icao_code, airport_info in airport_data.items():
            # Skip invalid ICAO codes
            if not icao_code or len(icao_code) != 4:
                continue
            
            # Extract coordinates
            latitude = airport_info.get('latitude')
            longitude = airport_info.get('longitude')
            
            if latitude is None or longitude is None:
                continue
            
            # Determine country and region
            country = determine_country_from_icao(icao_code)
            region = determine_region_from_icao(icao_code)
            
            # Create airport record
            airport = Airports(
                icao_code=icao_code,
                name=airport_info.get('name'),  # Will be None for most entries
                latitude=latitude,
                longitude=longitude,
                country=country,
                region=region,
                facility_type='airport',  # Default assumption
                is_active=True
            )
            
            airports_to_insert.append(airport)
        
        # Bulk insert for efficiency
        session.bulk_save_objects(airports_to_insert)
        session.commit()
        
        print(f"Successfully inserted {len(airports_to_insert)} airports")
        
        # Verify the data
        total_airports = session.query(Airports).count()
        australian_airports = session.query(Airports).filter(Airports.icao_code.like('Y%')).count()
        us_airports = session.query(Airports).filter(Airports.icao_code.like('K%')).count()
        
        print(f"Database now contains:")
        print(f"  - Total airports: {total_airports}")
        print(f"  - Australian airports: {australian_airports}")
        print(f"  - US airports: {us_airports}")
        
        session.close()
        
    except Exception as e:
        print(f"Error populating airports table: {e}")
        session.rollback()
        session.close()
        raise


def main():
    """Main function to populate global airports table"""
    print("Populating global airports table...")
    
    # Load airport data
    airport_data = load_airport_data()
    if not airport_data:
        print("Failed to load airport data")
        return
    
    # Populate the table
    populate_airports_table(airport_data)
    
    print("Global airports table population completed successfully!")


if __name__ == "__main__":
    main() 