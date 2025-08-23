#!/usr/bin/env python3
"""
Test script to verify ATCDetectionService now returns array format.
"""

import sys
import os
import asyncio
import json
from datetime import datetime, timezone

# Add app to path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

from app.services.atc_detection_service import ATCDetectionService
from app.database import get_database_session
from sqlalchemy import text

async def test_atc_format():
    """Test that ATCDetectionService returns array format."""
    try:
        # Create service instance
        service = ATCDetectionService()
        
        # Get a real flight from the database to test with
        async with get_database_session() as session:
            # Find a flight that has transceiver data
            result = await session.execute(text("""
                SELECT DISTINCT f.callsign, f.departure, f.arrival, f.logon_time
                FROM flights f
                JOIN transceivers t ON f.callsign = t.callsign
                WHERE t.entity_type = 'flight'
                AND f.last_updated < NOW() - INTERVAL '14 hours'
                LIMIT 1
            """))
            
            flight_data = result.fetchone()
            if not flight_data:
                print("No suitable flight found for testing")
                return
            
            flight_callsign = flight_data.callsign
            departure = flight_data.departure
            arrival = flight_data.arrival
            logon_time = flight_data.logon_time
            
            print(f"Testing ATCDetectionService with real flight {flight_callsign}")
            print(f"Departure: {departure}, Arrival: {arrival}")
            print(f"Logon time: {logon_time}")
            print("-" * 50)
        
        # Call the service
        result = await service.detect_flight_atc_interactions_with_timeout(
            flight_callsign, departure, arrival, logon_time, timeout_seconds=30.0
        )
        
        print("Service returned:")
        print(f"Type of controller_callsigns: {type(result['controller_callsigns'])}")
        print(f"Is list: {isinstance(result['controller_callsigns'], list)}")
        print(f"Is dict: {isinstance(result['controller_callsigns'], dict)}")
        print(f"Length: {len(result['controller_callsigns'])}")
        print()
        
        if result['controller_callsigns']:
            print("First controller entry:")
            first_controller = result['controller_callsigns'][0] if isinstance(result['controller_callsigns'], list) else list(result['controller_callsigns'].values())[0]
            print(json.dumps(first_controller, indent=2, default=str))
        else:
            print("No controller interactions found")
        
        print()
        print("Full result structure:")
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"Error testing ATCDetectionService: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_atc_format())
