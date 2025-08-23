#!/usr/bin/env python3
"""
Test script for airborne controller time percentage calculation

This script tests the new functionality to calculate the percentage of airborne time
spent in ATC contact using the enhanced logic that validates aircraft are in sectors.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.atc_detection_service import ATCDetectionService
from app.database import get_database_session

async def test_airborne_controller_time_calculation():
    """Test the new airborne controller time percentage calculation."""
    
    print("🧪 Testing Airborne Controller Time Percentage Calculation")
    print("=" * 60)
    
    # Initialize the service
    atc_service = ATCDetectionService()
    
    # Test parameters - use a real flight from your database
    test_callsign = "QFA123"  # Replace with actual callsign from your data
    test_departure = "YSSY"   # Replace with actual departure airport
    test_arrival = "YMML"     # Replace with actual arrival airport
    test_logon_time = datetime.now(timezone.utc) - timedelta(hours=2)  # 2 hours ago
    
    print(f"📊 Test Parameters:")
    print(f"   Callsign: {test_callsign}")
    print(f"   Departure: {test_departure}")
    print(f"   Arrival: {test_arrival}")
    print(f"   Logon Time: {test_logon_time}")
    print()
    
    try:
        # Test the new function
        print("🔄 Calculating airborne controller time percentage...")
        result = await atc_service.calculate_airborne_controller_time_percentage(
            test_callsign, test_departure, test_arrival, test_logon_time
        )
        
        print("✅ Calculation completed successfully!")
        print()
        print("📈 Results:")
        print(f"   Airborne Controller Time Percentage: {result['airborne_controller_time_percentage']}%")
        print(f"   Total Airborne ATC Time (minutes): {result['total_airborne_atc_time_minutes']}")
        print(f"   Total Airborne Time (minutes): {result['total_airborne_time_minutes']}")
        print(f"   Airborne ATC Contacts Detected: {result['airborne_atc_contacts_detected']}")
        print()
        
        # Test the existing function for comparison
        print("🔄 Calculating regular controller time percentage for comparison...")
        existing_result = await atc_service.detect_flight_atc_interactions(
            test_callsign, test_departure, test_arrival, test_logon_time
        )
        
        print("📊 Comparison Results:")
        print(f"   Regular Controller Time Percentage: {existing_result['controller_time_percentage']}%")
        print(f"   Airborne Controller Time Percentage: {result['airborne_controller_time_percentage']}%")
        print()
        
        if result['total_airborne_time_minutes'] > 0:
            print("✅ Test PASSED: Both calculations completed successfully")
            print(f"   Difference: {abs(result['airborne_controller_time_percentage'] - existing_result['controller_time_percentage']):.1f}%")
        else:
            print("⚠️  Test PARTIAL: No airborne time data found")
            print("   This might indicate the test flight has no sector occupancy data")
            
    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_database_connection():
    """Test database connection and verify the new field exists."""
    
    print("🔌 Testing Database Connection and Schema")
    print("=" * 50)
    
    try:
        async with get_database_session() as session:
            # Check if the new field exists in flight_summaries
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'flight_summaries' 
                AND column_name = 'airborne_controller_time_percentage'
            """))
            
            row = result.fetchone()
            if row:
                print(f"✅ New field found in flight_summaries:")
                print(f"   Column: {row.column_name}")
                print(f"   Type: {row.data_type}")
                print(f"   Nullable: {row.is_nullable}")
            else:
                print("❌ New field NOT found in flight_summaries")
                print("   You may need to run the migration script first")
                return False
            
            # Check if the new field exists in flights_archive
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'flights_archive' 
                AND column_name = 'airborne_controller_time_percentage'
            """))
            
            row = result.fetchone()
            if row:
                print(f"✅ New field found in flights_archive:")
                print(f"   Column: {row.column_name}")
                print(f"   Type: {row.data_type}")
                print(f"   Nullable: {row.is_nullable}")
            else:
                print("❌ New field NOT found in flights_archive")
                print("   You may need to run the migration script first")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

async def main():
    """Main test function."""
    
    print("🚀 Starting Airborne Controller Time Percentage Tests")
    print("=" * 60)
    print()
    
    # Test 1: Database connection and schema
    db_test_passed = await test_database_connection()
    print()
    
    if not db_test_passed:
        print("❌ Database test failed. Please run the migration script first:")
        print("   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/add_airborne_controller_time_percentage.sql")
        print()
        return
    
    # Test 2: Functionality
    func_test_passed = await test_airborne_controller_time_calculation()
    print()
    
    # Summary
    if db_test_passed and func_test_passed:
        print("🎉 All tests completed successfully!")
        print("   The new airborne_controller_time_percentage field is ready to use.")
    else:
        print("⚠️  Some tests failed. Please check the output above.")

if __name__ == "__main__":
    asyncio.run(main())



