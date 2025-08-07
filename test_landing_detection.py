#!/usr/bin/env python3
"""
Test script to manually test landing detection
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Add the app directory to the path
sys.path.append('app')

from app.database import SessionLocal
from app.models import Flight, Airports
from app.services.traffic_analysis_service import TrafficAnalysisService

def test_landing_detection():
    """Test landing detection for QFA804"""
    
    db = SessionLocal()
    try:
        # Get QFA804 flight
        flight = db.query(Flight).filter(Flight.callsign == 'QFA804').order_by(Flight.last_updated.desc()).first()
        
        if not flight:
            print("QFA804 flight not found")
            return
        
        print(f"Flight: {flight.callsign}")
        print(f"Status: {flight.status}")
        print(f"Arrival: {flight.arrival}")
        print(f"Position: {flight.position_lat}, {flight.position_lng}")
        print(f"Altitude: {flight.altitude}")
        print(f"Groundspeed: {flight.groundspeed}")
        print(f"Last Updated: {flight.last_updated}")
        
        # Get Sydney airport data
        airport = db.query(Airports).filter(Airports.icao_code == 'YSSY').first()
        if not airport:
            print("Sydney airport not found")
            return
        
        print(f"\nSydney Airport:")
        print(f"Position: {airport.latitude}, {airport.longitude}")
        print(f"Elevation: {airport.elevation}")
        
        # Test landing detection
        traffic_service = TrafficAnalysisService(db)
        landing_detections = traffic_service.detect_landings([flight])
        
        print(f"\nLanding detections: {len(landing_detections)}")
        for detection in landing_detections:
            print(f"Detection: {detection}")
        
        # Check if flight meets landing criteria manually
        distance_nm = traffic_service.calculate_distance(
            flight.position_lat, flight.position_lng,
            airport.latitude, airport.longitude
        )
        
        altitude_above_airport = (flight.altitude or 0) - (airport.elevation or 0)
        
        print(f"\nManual calculation:")
        print(f"Distance to airport: {distance_nm:.2f} nm")
        print(f"Altitude above airport: {altitude_above_airport} ft")
        print(f"Groundspeed: {flight.groundspeed} kts")
        
        # Check thresholds
        detection_radius_nm = float(os.getenv('LANDING_DETECTION_RADIUS_NM', '15.0'))
        altitude_threshold_ft = float(os.getenv('LANDING_ALTITUDE_THRESHOLD_FT_ABOVE_AIRPORT', '1000'))
        speed_threshold_kts = float(os.getenv('LANDING_SPEED_THRESHOLD_KTS', '20'))
        
        distance_ok = distance_nm <= detection_radius_nm
        altitude_ok = altitude_above_airport <= altitude_threshold_ft
        speed_ok = (flight.groundspeed or 0) <= speed_threshold_kts
        
        print(f"\nThresholds:")
        print(f"Distance OK: {distance_ok} ({distance_nm:.2f} <= {detection_radius_nm})")
        print(f"Altitude OK: {altitude_ok} ({altitude_above_airport} <= {altitude_threshold_ft})")
        print(f"Speed OK: {speed_ok} ({(flight.groundspeed or 0)} <= {speed_threshold_kts})")
        print(f"All OK: {distance_ok and altitude_ok and speed_ok}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_landing_detection()
