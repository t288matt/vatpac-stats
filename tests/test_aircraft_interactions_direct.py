#!/usr/bin/env python3
"""
Direct Test of _get_aircraft_interactions Method

This script directly tests the _get_aircraft_interactions method to see:
1. If it's actually being called
2. What data it returns
3. Whether it's using the FlightDetectionService
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta

async def test_aircraft_interactions_direct():
    """Test the _get_aircraft_interactions method directly."""
    try:
        print("🧪 Testing _get_aircraft_interactions method directly")
        print("=" * 60)
        
        # Import the data service
        from app.services.data_service import get_data_service
        
        print("✅ Successfully imported get_data_service")
        
        # Get the data service instance
        data_service = await get_data_service()
        print("✅ Successfully got data service instance")
        
        # Check if FlightDetectionService exists
        if hasattr(data_service, 'flight_detection_service'):
            print(f"✅ FlightDetectionService exists: {type(data_service.flight_detection_service)}")
            print(f"   Proximity threshold: {data_service.flight_detection_service.proximity_threshold_nm}nm")
            print(f"   Time window: {data_service.flight_detection_service.time_window_seconds}s")
        else:
            print("❌ FlightDetectionService does NOT exist!")
            return
        
        # Test with AD_GND session data
        callsign = "AD_GND"
        session_start = datetime(2025, 8, 18, 11, 49, 16, tzinfo=timezone.utc)
        session_end = datetime(2025, 8, 18, 12, 34, 15, tzinfo=timezone.utc)
        
        print(f"\n📍 Testing with AD_GND session:")
        print(f"   Callsign: {callsign}")
        print(f"   Session start: {session_start}")
        print(f"   Session end: {session_end}")
        
        # Test the method directly on the main DataService
        print(f"\n🔍 Calling _get_aircraft_interactions directly...")
        aircraft_data = await data_service._get_aircraft_interactions(
            callsign, session_start, session_end, None
        )
        
        print(f"✅ Method returned: {type(aircraft_data)}")
        print(f"   Total aircraft: {aircraft_data.get('total_aircraft', 'N/A')}")
        print(f"   Peak count: {aircraft_data.get('peak_count', 'N/A')}")
        print(f"   Details count: {len(aircraft_data.get('details', []))}")
        
        # Check if VOZ905 and PAL416 are in the results
        details = aircraft_data.get('details', [])
        voz905_found = any(detail.get('callsign') == 'VOZ905' for detail in details)
        pal416_found = any(detail.get('callsign') == 'PAL416' for detail in details)
        
        print(f"\n🔍 Geographic Proximity Check Results:")
        print(f"   VOZ905 (Sydney, 628nm): {'❌ FOUND' if voz905_found else '✅ NOT FOUND'}")
        print(f"   PAL416 (Canberra, 523nm): {'❌ FOUND' if pal416_found else '✅ NOT FOUND'}")
        
        if voz905_found or pal416_found:
            print(f"\n🚨 PROBLEM: Geographically distant flights found despite 30nm threshold!")
            print(f"   This means the FlightDetectionService is NOT being used or its filtering is bypassed")
        else:
            print(f"\n✅ SUCCESS: Geographic filtering is working correctly!")
        
        # Show first few aircraft details
        print(f"\n📊 First 5 aircraft details:")
        for i, detail in enumerate(details[:5]):
            print(f"   {i+1}. {detail.get('callsign')} - {detail.get('frequency')}Hz")
        
        return aircraft_data
        
    except Exception as e:
        print(f"❌ Error testing _get_aircraft_interactions: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Starting direct test of _get_aircraft_interactions method...")
    result = asyncio.run(test_aircraft_interactions_direct())
    print(f"\n🏁 Test completed. Result: {type(result)}")
