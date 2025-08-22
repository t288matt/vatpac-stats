#!/usr/bin/env python3
"""
Real Flight Processing Test
Creates real flight data 14+ hours old and triggers actual system processing
"""

import asyncio
import psycopg2
from datetime import datetime, timezone, timedelta
import json
import time
import sys
import os

# Add the app directory to Python path so we can import the actual system
sys.path.insert(0, '/app')

# Database connection details
DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'vatsim_data',
    'user': 'vatsim_user',
    'password': 'vatsim_password'
}

def create_old_flight_data():
    """Create flight data that's 14+ hours old to trigger processing"""
    
    # Calculate timestamps
    now = datetime.now(timezone.utc)
    old_timestamp = now - timedelta(hours=14, minutes=30)  # 14.5 hours old
    
    # Create realistic flight data
    test_flights = [
        {
            'callsign': 'REAL001',
            'departure': 'YSSY',
            'arrival': 'YMML',
            'cid': 999001,
            'deptime': '0800',
            'aircraft_type': 'B738',
            'logon_time': old_timestamp,
            'last_updated': old_timestamp,
            'aircraft_faa': 'B738',
            'route': 'YSSY YMML',
            'flight_rules': 'I',
            'planned_altitude': 'FL350',
            'name': 'Test Pilot 1',
            'server': 'TEST',
            'pilot_rating': 1,
            'military_rating': 0,
            'transponder': '1234',
            'altitude': 35000,
            'groundspeed': 450,
            'heading': 270,
            'latitude': -33.8688,
            'longitude': 151.2093
        },
        {
            'callsign': 'REAL002',
            'departure': 'YMML',
            'arrival': 'YSSY',
            'cid': 999002,
            'deptime': '0900',
            'aircraft_type': 'A320',
            'logon_time': old_timestamp,
            'last_updated': old_timestamp,
            'aircraft_faa': 'A320',
            'route': 'YMML YSSY',
            'flight_rules': 'I',
            'planned_altitude': 'FL300',
            'name': 'Test Pilot 2',
            'server': 'TEST',
            'pilot_rating': 2,
            'military_rating': 0,
            'transponder': '5678',
            'altitude': 30000,
            'groundspeed': 400,
            'heading': 90,
            'latitude': -37.8136,
            'longitude': 144.9631
        }
    ]
    
    return test_flights, old_timestamp

def insert_old_flights(conn, flights):
    """Insert old flight data into the database"""
    
    cursor = conn.cursor()
    
    # Clear existing test data
    cursor.execute("DELETE FROM flights WHERE callsign LIKE 'REAL%'")
    cursor.execute("DELETE FROM flight_summaries WHERE callsign LIKE 'REAL%'")
    cursor.execute("DELETE FROM flights_archive WHERE callsign LIKE 'REAL%'")
    
    # Insert new test data
    for flight in flights:
        cursor.execute("""
            INSERT INTO flights (
                callsign, departure, arrival, cid, deptime, aircraft_type,
                logon_time, last_updated, created_at, updated_at,
                aircraft_faa, route, flight_rules, planned_altitude,
                name, server, pilot_rating, military_rating, transponder,
                altitude, groundspeed, heading, latitude, longitude
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            flight['callsign'],
            flight['departure'],
            flight['arrival'],
            flight['cid'],
            flight['deptime'],
            flight['aircraft_type'],
            flight['logon_time'],
            flight['last_updated'],
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
            flight['aircraft_faa'],
            flight['route'],
            flight['flight_rules'],
            flight['planned_altitude'],
            flight['name'],
            flight['server'],
            flight['pilot_rating'],
            flight['military_rating'],
            flight['transponder'],
            flight['altitude'],
            flight['groundspeed'],
            flight['heading'],
            flight['latitude'],
            flight['longitude']
        ))
    
    conn.commit()
    cursor.close()
    print(f"✅ Inserted {len(flights)} old flight records (14+ hours old)")

def check_flight_data(conn):
    """Check the current state of our test flights"""
    
    cursor = conn.cursor()
    
    # Check flights table
    cursor.execute("""
        SELECT callsign, departure, arrival, cid, deptime, last_updated, 
               EXTRACT(EPOCH FROM (NOW() - last_updated))/3600 as hours_old
        FROM flights 
        WHERE callsign LIKE 'REAL%'
        ORDER BY callsign
    """)
    
    flights = cursor.fetchall()
    
    print(f"\n📊 Current Flight Data:")
    for flight in flights:
        callsign, departure, arrival, cid, deptime, last_updated, hours_old = flight
        print(f"  {callsign}: {departure} → {arrival} (CID: {cid}, Dept: {deptime})")
        print(f"     Last updated: {last_updated}")
        print(f"     Age: {hours_old:.2f} hours")
    
    # Check flight_summaries table
    cursor.execute("""
        SELECT callsign, departure, arrival, cid, created_at
        FROM flight_summaries 
        WHERE callsign LIKE 'REAL%'
        ORDER BY callsign
    """)
    
    summaries = cursor.fetchall()
    
    print(f"\n📋 Current Flight Summaries:")
    if summaries:
        for summary in summaries:
            callsign, departure, arrival, cid, created_at = summary
            print(f"  {callsign}: {departure} → {arrival} (CID: {cid})")
            print(f"     Created: {created_at}")
    else:
        print("  No flight summaries found yet")
    
    # Check flights_archive table
    cursor.execute("""
        SELECT callsign, departure, arrival, cid, created_at
        FROM flights_archive 
        WHERE callsign LIKE 'REAL%'
        ORDER BY callsign
    """)
    
    archived = cursor.fetchall()
    
    print(f"\n🗄️ Current Archived Flights:")
    if archived:
        for archive in archived:
            callsign, departure, arrival, cid, created_at = archive
            print(f"  {callsign}: {departure} → {arrival} (CID: {cid})")
            print(f"     Archived: {created_at}")
    else:
        print("  No archived flights found yet")
    
    cursor.close()
    return flights, summaries, archived

async def trigger_real_system_processing():
    """Trigger the actual system to process completed flights"""
    
    print(f"\n🚀 Triggering ACTUAL system processing...")
    
    try:
        # Import the actual data service
        from app.services.data_service import DataService
        
        # Initialize the service
        data_service = DataService()
        await data_service.initialize()
        
        print(f"✅ Data service initialized")
        
        # Call the actual method that processes completed flights
        result = await data_service.process_completed_flights()
        
        print(f"✅ System processing completed: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Failed to trigger system processing: {e}")
        import traceback
        traceback.print_exc()
        return None

def wait_and_monitor(conn, target_hours=14):
    """Wait and monitor the system as flights age"""
    
    print(f"\n⏰ Monitoring flights as they approach {target_hours} hours...")
    print(f"Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            # Check current state
            flights, summaries, archived = check_flight_data(conn)
            
            # Check if any flights are ready for processing
            cursor = conn.cursor()
            cursor.execute("""
                SELECT callsign, departure, arrival, cid, deptime, last_updated,
                       EXTRACT(EPOCH FROM (NOW() - last_updated))/3600 as hours_old
                FROM flights 
                WHERE callsign LIKE 'REAL%'
                AND EXTRACT(EPOCH FROM (NOW() - last_updated))/3600 >= 14
                ORDER BY callsign
            """)
            
            old_flights = cursor.fetchall()
            cursor.close()
            
            if old_flights:
                print(f"✅ Found {len(old_flights)} flights that are 14+ hours old:")
                for flight in old_flights:
                    callsign, departure, arrival, cid, deptime, last_updated, hours_old = flight
                    print(f"  {callsign}: {departure} → {arrival} (CID: {cid}, Dept: {deptime})")
                    print(f"     Age: {hours_old:.2f} hours - Ready for processing!")
            else:
                print(f"⏳ No flights are 14+ hours old yet")
            
            # Wait 1 minute
            print(f"\n⏳ Waiting 1 minute... (Press Ctrl+C to stop)")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Monitoring stopped by user")
        return flights, summaries, archived

def cleanup_test_data(conn):
    """Clean up all test data"""
    
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM flights WHERE callsign LIKE 'REAL%'")
    cursor.execute("DELETE FROM flight_summaries WHERE callsign LIKE 'REAL%'")
    cursor.execute("DELETE FROM flights_archive WHERE callsign LIKE 'REAL%'")
    
    conn.commit()
    cursor.close()
    
    print(f"\n🧹 Cleaned up all test data")

async def main():
    """Main test execution"""
    
    print("🧪 Real Flight Processing Test")
    print("=" * 60)
    print("This will create real flight data and trigger actual system processing")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected to database")
        
        # Create and insert old flight data
        test_flights, old_timestamp = create_old_flight_data()
        insert_old_flights(conn, test_flights)
        
        # Show initial state
        print(f"\n📅 Created flights at: {old_timestamp}")
        print(f"📅 Current time: {datetime.now(timezone.utc)}")
        
        # Check initial state
        check_flight_data(conn)
        
        # Wait for user to decide when to start monitoring
        print(f"\n⏰ Flights are currently {14.5:.2f} hours old")
        print(f"⏰ They should be eligible for processing immediately!")
        
        input("Press Enter when you want to trigger the ACTUAL system processing...")
        
        # Trigger the actual system processing
        result = await trigger_real_system_processing()
        
        if result:
            print(f"\n🎯 System Processing Result: {result}")
        
        # Check final state after processing
        print(f"\n🎯 Final System State After Processing:")
        check_flight_data(conn)
        
        # Summary
        print(f"\n📊 Test Summary:")
        print(f"  Flights created: {len(test_flights)}")
        print(f"  System processing result: {result}")
        
        if result and result.get('summaries_created', 0) > 0:
            print(f"\n✅ SUCCESS: System processed flights and created summaries!")
        else:
            print(f"\n❌ FAILURE: System did not create flight summaries")
        
        # Clean up
        cleanup_test_data(conn)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()
            print("✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())
