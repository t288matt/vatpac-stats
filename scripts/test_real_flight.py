#!/usr/bin/env python3
"""
Test script for airborne controller time percentage calculation with real flight data.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.atc_detection_service import ATCDetectionService
from app.database import get_database_session
from sqlalchemy import text

async def test_real_flight():
    """Test with a real flight that has sector occupancy data."""
    
    # Flight data from the database
    callsign = "UAE413"
    departure = "YSSY"
    arrival = "OMDB"
    from datetime import datetime
    logon_time = datetime.fromisoformat("2025-08-23 13:17:38+00:00")
    
    print(f"🧪 Testing with real flight data:")
    print(f"   Callsign: {callsign}")
    print(f"   Route: {departure} → {arrival}")
    print(f"   Logon: {logon_time}")
    print()
    
    # Initialize the service
    atc_service = ATCDetectionService()
    
    try:
        # Test the calculation
        print("🔄 Calculating airborne controller time percentage...")
        result = await atc_service.calculate_airborne_controller_time_percentage(
            callsign, departure, arrival, logon_time
        )
        
        print("✅ Calculation completed!")
        print()
        print("📊 Results:")
        print(f"   Airborne Controller Time Percentage: {result['airborne_controller_time_percentage']:.2f}%")
        print(f"   Total Airborne ATC Time (minutes): {result['total_airborne_atc_time_minutes']}")
        print(f"   Total Airborne Time (minutes): {result['total_airborne_time_minutes']}")
        print(f"   Airborne ATC Contacts Detected: {result.get('airborne_atc_contacts_count', 'N/A')}")
        print()
        
        # Also test the regular controller time percentage for comparison
        print("🔄 Calculating regular controller time percentage for comparison...")
        regular_result = await atc_service.detect_flight_atc_interactions_with_timeout(
            callsign, departure, arrival, logon_time, timeout_seconds=30.0
        )
        
        print("📊 Comparison Results:")
        print(f"   Regular Controller Time Percentage: {regular_result['controller_time_percentage']:.2f}%")
        print(f"   Airborne Controller Time Percentage: {result['airborne_controller_time_percentage']:.2f}%")
        print()
        
        if result['total_airborne_time_minutes'] > 0:
            print("✅ SUCCESS: Found real airborne time data!")
        else:
            print("⚠️  No airborne time data found for this flight")
            
    except Exception as e:
        print(f"❌ Error during calculation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Testing Airborne Controller Time with Real Flight Data")
    print("=" * 60)
    print()
    
    asyncio.run(test_real_flight())
