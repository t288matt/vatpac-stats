#!/usr/bin/env python3
"""
Script to load airports from airport_coordinates.json into the airport_config table
for traffic movement detection and data integrity.
"""

import sys
import os
import json
sys.path.append('/app')

from app.database import SessionLocal
from app.models import AirportConfig
from datetime import datetime

def load_airports_from_json():
    """Load airports from airport_coordinates.json into the database"""
    
    try:
        # Load airport coordinates from JSON file
        with open('airport_coordinates.json', 'r') as f:
            airports_data = json.load(f)
        
        print(f"Loaded {len(airports_data)} airports from JSON file")
        
        db = SessionLocal()
        try:
            added_count = 0
            updated_count = 0
            
            for icao_code, airport_info in airports_data.items():
                # Check if airport already exists
                existing = db.query(AirportConfig).filter(
                    AirportConfig.icao_code == icao_code
                ).first()
                
                # Extract airport data
                latitude = airport_info.get('latitude', 0.0)
                longitude = airport_info.get('longitude', 0.0)
                name = airport_info.get('name', f'{icao_code} Airport')
                
                # Determine region based on ICAO code
                region = 'Unknown'
                if icao_code.startswith('Y'):  # Australia
                    region = 'Australia'
                elif icao_code.startswith('K'):  # United States
                    region = 'United States'
                elif icao_code.startswith('E'):  # Europe
                    region = 'Europe'
                elif icao_code.startswith('C'):  # Canada
                    region = 'Canada'
                elif icao_code.startswith('Z'):  # China
                    region = 'China'
                elif icao_code.startswith('V'):  # India
                    region = 'India'
                
                if not existing:
                    # Create new airport
                    airport = AirportConfig(
                        icao_code=icao_code,
                        name=name,
                        latitude=latitude,
                        longitude=longitude,
                        detection_radius_nm=15.0,  # Default detection radius
                        departure_altitude_threshold=1000,
                        arrival_altitude_threshold=3000,
                        departure_speed_threshold=50,
                        arrival_speed_threshold=150,
                        is_active=True,
                        region=region,
                        last_updated=datetime.utcnow()
                    )
                    db.add(airport)
                    added_count += 1
                    print(f"Added airport: {icao_code} - {name} ({region})")
                else:
                    # Update existing airport
                    existing.name = name
                    existing.latitude = latitude
                    existing.longitude = longitude
                    existing.region = region
                    existing.last_updated = datetime.utcnow()
                    updated_count += 1
                    print(f"Updated airport: {icao_code} - {name} ({region})")
            
            db.commit()
            print(f"\nSuccessfully processed airports:")
            print(f"- Added: {added_count}")
            print(f"- Updated: {updated_count}")
            print(f"- Total: {added_count + updated_count}")
            
        except Exception as e:
            db.rollback()
            print(f"Error processing airports: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error loading airport coordinates file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_airports_from_json() 