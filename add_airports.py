#!/usr/bin/env python3
"""
Script to add major Australian airports to the airport_config table
for traffic movement detection and data integrity.
"""

import sys
import os
sys.path.append('/app')

from app.database import SessionLocal
from app.models import AirportConfig
from datetime import datetime

def add_australian_airports():
    """Add major Australian airports to the configuration"""
    
    airports = [
        # Major Australian airports
        {
            'icao_code': 'YSSY',
            'name': 'Sydney Airport',
            'latitude': -33.9399,
            'longitude': 151.1753,
            'detection_radius_nm': 15.0,
            'departure_altitude_threshold': 1000,
            'arrival_altitude_threshold': 3000,
            'departure_speed_threshold': 50,
            'arrival_speed_threshold': 150,
            'region': 'Australia'
        },
        {
            'icao_code': 'YMML',
            'name': 'Melbourne Airport',
            'latitude': -37.8136,
            'longitude': 144.9631,
            'detection_radius_nm': 15.0,
            'departure_altitude_threshold': 1000,
            'arrival_altitude_threshold': 3000,
            'departure_speed_threshold': 50,
            'arrival_speed_threshold': 150,
            'region': 'Australia'
        },
        {
            'icao_code': 'YBBN',
            'name': 'Brisbane Airport',
            'latitude': -27.3842,
            'longitude': 153.1175,
            'detection_radius_nm': 15.0,
            'departure_altitude_threshold': 1000,
            'arrival_altitude_threshold': 3000,
            'departure_speed_threshold': 50,
            'arrival_speed_threshold': 150,
            'region': 'Australia'
        },
        {
            'icao_code': 'YPPH',
            'name': 'Perth Airport',
            'latitude': -31.9403,
            'longitude': 115.9670,
            'detection_radius_nm': 15.0,
            'departure_altitude_threshold': 1000,
            'arrival_altitude_threshold': 3000,
            'departure_speed_threshold': 50,
            'arrival_speed_threshold': 150,
            'region': 'Australia'
        },
        {
            'icao_code': 'YBCG',
            'name': 'Gold Coast Airport',
            'latitude': -28.1644,
            'longitude': 153.5047,
            'detection_radius_nm': 12.0,
            'departure_altitude_threshold': 1000,
            'arrival_altitude_threshold': 3000,
            'departure_speed_threshold': 50,
            'arrival_speed_threshold': 150,
            'region': 'Australia'
        },
        {
            'icao_code': 'YBCS',
            'name': 'Cairns Airport',
            'latitude': -16.8858,
            'longitude': 145.7553,
            'detection_radius_nm': 12.0,
            'departure_altitude_threshold': 1000,
            'arrival_altitude_threshold': 3000,
            'departure_speed_threshold': 50,
            'arrival_speed_threshold': 150,
            'region': 'Australia'
        },
        {
            'icao_code': 'YPDN',
            'name': 'Darwin Airport',
            'latitude': -12.4083,
            'longitude': 130.8726,
            'detection_radius_nm': 12.0,
            'departure_altitude_threshold': 1000,
            'arrival_altitude_threshold': 3000,
            'departure_speed_threshold': 50,
            'arrival_speed_threshold': 150,
            'region': 'Australia'
        },
        {
            'icao_code': 'YSCB',
            'name': 'Canberra Airport',
            'latitude': -35.3069,
            'longitude': 149.1950,
            'detection_radius_nm': 10.0,
            'departure_altitude_threshold': 1000,
            'arrival_altitude_threshold': 3000,
            'departure_speed_threshold': 50,
            'arrival_speed_threshold': 150,
            'region': 'Australia'
        },
        {
            'icao_code': 'YBAF',
            'name': 'Brisbane West Wellcamp Airport',
            'latitude': -27.5583,
            'longitude': 151.7933,
            'detection_radius_nm': 10.0,
            'departure_altitude_threshold': 1000,
            'arrival_altitude_threshold': 3000,
            'departure_speed_threshold': 50,
            'arrival_speed_threshold': 150,
            'region': 'Australia'
        }
    ]
    
    db = SessionLocal()
    try:
        for airport_data in airports:
            # Check if airport already exists
            existing = db.query(AirportConfig).filter(
                AirportConfig.icao_code == airport_data['icao_code']
            ).first()
            
            if not existing:
                airport = AirportConfig(
                    icao_code=airport_data['icao_code'],
                    name=airport_data['name'],
                    latitude=airport_data['latitude'],
                    longitude=airport_data['longitude'],
                    detection_radius_nm=airport_data['detection_radius_nm'],
                    departure_altitude_threshold=airport_data['departure_altitude_threshold'],
                    arrival_altitude_threshold=airport_data['arrival_altitude_threshold'],
                    departure_speed_threshold=airport_data['departure_speed_threshold'],
                    arrival_speed_threshold=airport_data['arrival_speed_threshold'],
                    is_active=True,
                    region=airport_data['region'],
                    last_updated=datetime.utcnow()
                )
                db.add(airport)
                print(f"Added airport: {airport_data['icao_code']} - {airport_data['name']}")
            else:
                print(f"Airport already exists: {airport_data['icao_code']}")
        
        db.commit()
        print(f"Successfully added {len(airports)} airports to configuration")
        
    except Exception as e:
        db.rollback()
        print(f"Error adding airports: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_australian_airports() 