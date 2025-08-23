#!/usr/bin/env python3
"""
Test script to validate SQL syntax and ATC detection logic
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.atc_detection_service import ATCDetectionService
from app.database import get_database_session
from datetime import datetime, timezone, timedelta

async def test_sql_syntax():
    """Test the ATC detection with actual data that exists in this environment"""
    
    # Test data that actually exists in this dev environment
    test_flight = "JST522"  # This has overlapping transceivers with ML-GUN_CTR ATC
    test_departure = "YMML"  # Melbourne
    test_arrival = "YSSY"    # Sydney
    test_logon_time = datetime(2025, 8, 22, 8, 51, 11, tzinfo=timezone.utc)  # Exact logon time from database
    
    print(f"🧪 Testing ATC Detection for flight {test_flight}")
    print(f"   Departure: {test_departure}")
    print(f"   Arrival: {test_arrival}")
    print(f"   Logon time: {test_logon_time}")
    print()
    
    try:
        # Initialize the service
        atc_service = ATCDetectionService()
        
        # Test the ATC detection
        print("🔍 Testing ATC interaction detection...")
        result = await atc_service.detect_flight_atc_interactions(
            test_flight, test_departure, test_arrival, test_logon_time
        )
        
        print(f"✅ ATC detection completed successfully!")
        print(f"   Controllers detected: {len(result.get('controller_callsigns', {}))}")
        print(f"   Controller time percentage: {result.get('controller_time_percentage', 0)}%")
        
        if result.get('controller_callsigns'):
            print("   Controllers found:")
            for controller, data in result['controller_callsigns'].items():
                print(f"     - {controller}: {data.get('type', 'Unknown')} type")
        else:
            print("   ❌ No controllers detected - this indicates the SQL issue is still present")
            
    except Exception as e:
        print(f"❌ ATC detection failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False
    
    return True

async def test_with_existing_controllers():
    """Test with controllers that actually exist in this environment"""
    
    print("\n🔍 Testing with existing controllers from this environment...")
    
    try:
        async with get_database_session() as session:
            # Check what controllers exist for JST522's time period
            query = """
            SELECT DISTINCT t.callsign, t.entity_type, t.timestamp
            FROM transceivers t
            WHERE t.callsign IN ('JST522', 'ML-GUN_CTR', 'ML_TWR')
            AND t.timestamp > '2025-08-22 10:00:00+00'
            ORDER BY t.timestamp DESC
            LIMIT 20
            """
            
            result = await session.execute(query)
            records = result.fetchall()
            
            print(f"   Found {len(records)} transceiver records:")
            for record in records:
                print(f"     - {record.callsign} ({record.entity_type}) at {record.timestamp}")
            
            return len(records) > 0
            
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False

async def test_frequency_matching():
    """Test if frequency matching works with existing data"""
    
    print("\n🔍 Testing frequency matching logic...")
    
    try:
        async with get_database_session() as session:
            # Test the actual frequency matching logic with JST522 and ML-GUN_CTR
            query = """
            WITH flight_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'flight' 
                AND t.callsign = 'JST522'
                AND t.timestamp > '2025-08-22 10:00:00+00'
                LIMIT 10
            ),
            atc_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'atc' 
                AND t.callsign = 'ML-GUN_CTR'
                AND t.timestamp > '2025-08-22 10:00:00+00'
                LIMIT 10
            )
            SELECT 
                ft.callsign as flight_callsign,
                at.callsign as atc_callsign,
                ft.frequency_mhz,
                ft.timestamp as flight_time,
                at.timestamp as atc_time,
                ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) as time_diff_seconds
            FROM flight_transceivers ft 
            JOIN atc_transceivers at ON ft.frequency_mhz = at.frequency_mhz 
            AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= 180
            ORDER BY ft.timestamp, at.timestamp
            LIMIT 20
            """
            
            result = await session.execute(query)
            matches = result.fetchall()
            
            print(f"   Found {len(matches)} frequency matches:")
            for match in matches:
                print(f"     - {match.flight_callsign} ↔ {match.atc_callsign} on {match.frequency_mhz:.3f}MHz (diff: {match.time_diff_seconds}s)")
            
            return len(matches) > 0
            
    except Exception as e:
        print(f"❌ Frequency matching test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting ATC Detection Tests with Actual Dev Environment Data")
    print("=" * 60)
    
    # Test 1: Check what data exists
    data_test_passed = await test_with_existing_controllers()
    
    # Test 2: Test frequency matching logic
    frequency_test_passed = await test_frequency_matching()
    
    # Test 3: Full ATC detection service
    atc_test_passed = await test_sql_syntax()
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   Data Availability Test: {'✅ PASSED' if data_test_passed else '❌ FAILED'}")
    print(f"   Frequency Matching Test: {'✅ PASSED' if frequency_test_passed else '❌ FAILED'}")
    print(f"   ATC Detection Service Test: {'✅ PASSED' if atc_test_passed else '❌ FAILED'}")
    
    if not atc_test_passed:
        print("\n🔧 The ATC detection is still failing - need to investigate further")
    
    return data_test_passed and frequency_test_passed and atc_test_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
