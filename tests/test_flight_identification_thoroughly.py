#!/usr/bin/env python3
"""
Comprehensive Test Script for Flight Identification Logic
Tests the new flight identification logic and incomplete flight filtering
"""

import asyncio
import psycopg2
from datetime import datetime, timezone, timedelta
import json

# Database connection details
DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'vatsim_data',
    'user': 'vatsim_user',
    'password': 'vatsim_password'
}

def create_dummy_flights():
    """Create dummy flight records to test the new logic"""
    
    # Test scenarios
    test_flights = [
        # Complete flight plan - should be processed
        {
            'callsign': 'TEST001',
            'departure': 'YSSY',
            'arrival': 'YMML',
            'cid': 1001,
            'deptime': '0800',
            'aircraft_type': 'B738',
            'logon_time': datetime.now(timezone.utc) - timedelta(hours=2),
            'last_updated': datetime.now(timezone.utc) - timedelta(hours=1)
        },
        # Complete flight plan - different pilot, same route
        {
            'callsign': 'TEST001',
            'departure': 'YSSY',
            'arrival': 'YMML',
            'cid': 1002,
            'deptime': '0900',
            'aircraft_type': 'B738',
            'logon_time': datetime.now(timezone.utc) - timedelta(hours=2),
            'last_updated': datetime.now(timezone.utc) - timedelta(hours=1)
        },
        # Incomplete flight plan - missing departure
        {
            'callsign': 'TEST002',
            'departure': '',
            'arrival': 'YMML',
            'cid': 1003,
            'deptime': '1000',
            'aircraft_type': 'A320',
            'logon_time': datetime.now(timezone.utc) - timedelta(hours=2),
            'last_updated': datetime.now(timezone.utc) - timedelta(hours=1)
        },
        # Incomplete flight plan - missing arrival
        {
            'callsign': 'TEST003',
            'departure': 'YSSY',
            'arrival': '',
            'cid': 1004,
            'deptime': '1100',
            'aircraft_type': 'A320',
            'logon_time': datetime.now(timezone.utc) - timedelta(hours=2),
            'last_updated': datetime.now(timezone.utc) - timedelta(hours=1)
        },
        # Incomplete flight plan - both missing
        {
            'callsign': 'TEST004',
            'departure': None,
            'arrival': None,
            'cid': 1005,
            'deptime': '1200',
            'aircraft_type': 'C172',
            'logon_time': datetime.now(timezone.utc) - timedelta(hours=2),
            'last_updated': datetime.now(timezone.utc) - timedelta(hours=1)
        },
        # Same pilot, same route, different departure time
        {
            'callsign': 'TEST005',
            'departure': 'YSSY',
            'arrival': 'YMML',
            'cid': 1006,
            'deptime': '1300',
            'aircraft_type': 'B738',
            'logon_time': datetime.now(timezone.utc) - timedelta(hours=2),
            'last_updated': datetime.now(timezone.utc) - timedelta(hours=1)
        },
        {
            'callsign': 'TEST005',
            'departure': 'YSSY',
            'arrival': 'YMML',
            'cid': 1006,
            'deptime': '1400',
            'aircraft_type': 'B738',
            'logon_time': datetime.now(timezone.utc) - timedelta(hours=1),
            'last_updated': datetime.now(timezone.utc) - timedelta(minutes=30)
        }
    ]
    
    return test_flights

def insert_dummy_flights(conn, flights):
    """Insert dummy flights into the database"""
    
    cursor = conn.cursor()
    
    # Clear existing test data
    cursor.execute("DELETE FROM flights WHERE callsign LIKE 'TEST%'")
    cursor.execute("DELETE FROM flight_summaries WHERE callsign LIKE 'TEST%'")
    cursor.execute("DELETE FROM flights_archive WHERE callsign LIKE 'TEST%'")
    
    # Insert new test data
    for flight in flights:
        cursor.execute("""
            INSERT INTO flights (
                callsign, departure, arrival, cid, deptime, aircraft_type,
                logon_time, last_updated, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            datetime.now(timezone.utc)
        ))
    
    conn.commit()
    cursor.close()
    print(f"✅ Inserted {len(flights)} dummy flight records")

def test_flight_identification_query(conn):
    """Test the new flight identification query"""
    
    cursor = conn.cursor()
    
    # Test the exact query from _identify_completed_flights
    query = """
        SELECT DISTINCT callsign, departure, arrival, cid, deptime
        FROM flights 
        WHERE last_updated < %s
        AND callsign NOT IN (
            SELECT DISTINCT callsign FROM flight_summaries
        )
        AND callsign LIKE 'TEST%%'
    """
    
    completion_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
    
    cursor.execute(query, (completion_threshold,))
    results = cursor.fetchall()
    
    print(f"\n🔍 Flight Identification Query Results (TEST flights only):")
    print(f"Query returned {len(results)} unique flight identifiers")
    
    for i, result in enumerate(results, 1):
        callsign, departure, arrival, cid, deptime = result
        print(f"  {i}. {callsign}: {departure} → {arrival} (CID: {cid}, Dept: {deptime})")
    
    cursor.close()
    return results

def test_incomplete_flight_filtering(conn):
    """Test that incomplete flights are not returned by the query"""
    
    cursor = conn.cursor()
    
    # Check which flights have incomplete data
    cursor.execute("""
        SELECT callsign, departure, arrival, cid, deptime
        FROM flights 
        WHERE callsign LIKE 'TEST%'
        ORDER BY callsign
    """)
    
    all_flights = cursor.fetchall()
    
    print(f"\n📊 All Test Flights in Database:")
    for flight in all_flights:
        callsign, departure, arrival, cid, deptime = flight
        status = "✅ Complete" if departure and arrival else "❌ Incomplete"
        print(f"  {callsign}: {departure} → {arrival} (CID: {cid}, Dept: {deptime}) - {status}")
    
    # Check incomplete flights specifically
    cursor.execute("""
        SELECT callsign, departure, arrival
        FROM flights 
        WHERE callsign LIKE 'TEST%'
        AND (departure IS NULL OR departure = '' OR arrival IS NULL OR arrival = '')
    """)
    
    incomplete_flights = cursor.fetchall()
    
    print(f"\n❌ Incomplete Flights (should be filtered out):")
    for flight in incomplete_flights:
        callsign, departure, arrival = flight
        print(f"  {callsign}: departure='{departure}', arrival='{arrival}'")
    
    cursor.close()
    return incomplete_flights

def test_flight_summary_creation_simulation(conn):
    """Simulate the flight summary creation process"""
    
    cursor = conn.cursor()
    
    # Get the unique flight identifiers that would be processed
    query = """
        SELECT DISTINCT callsign, departure, arrival, cid, deptime
        FROM flights 
        WHERE last_updated < %s
        AND callsign NOT IN (
            SELECT DISTINCT callsign FROM flight_summaries
        )
        AND departure IS NOT NULL AND departure != '' AND arrival IS NOT NULL AND arrival != ''
        AND callsign LIKE 'TEST%%'
    """
    
    completion_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
    
    cursor.execute(query, (completion_threshold,))
    flight_keys = cursor.fetchall()
    
    print(f"\n🎯 Flight Summary Creation Simulation (TEST flights only):")
    print(f"Would create {len(flight_keys)} flight summaries:")
    
    for i, flight_key in enumerate(flight_keys, 1):
        callsign, departure, arrival, cid, deptime = flight_key
        
        # Count how many records would be summarized for this flight
        cursor.execute("""
            SELECT COUNT(*) 
            FROM flights 
            WHERE callsign = %s 
            AND departure = %s 
            AND arrival = %s 
            AND cid = %s
            AND deptime = %s
        """, (callsign, departure, arrival, cid, deptime))
        
        record_count = cursor.fetchone()[0]
        
        print(f"  {i}. {callsign}: {departure} → {arrival} (CID: {cid}, Dept: {deptime})")
        print(f"     Records to summarize: {record_count}")
        
        # Show the actual records
        cursor.execute("""
            SELECT logon_time, last_updated, aircraft_type
            FROM flights 
            WHERE callsign = %s 
            AND departure = %s 
            AND arrival = %s 
            AND cid = %s
            AND deptime = %s
            ORDER BY last_updated
        """, (callsign, departure, arrival, cid, deptime))
        
        records = cursor.fetchall()
        for j, record in enumerate(records):
            logon_time, last_updated, aircraft_type = record
            print(f"       {j+1}. {aircraft_type} - Logon: {logon_time}, Last: {last_updated}")
    
    cursor.close()
    return flight_keys

def cleanup_test_data(conn):
    """Clean up all test data"""
    
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM flights WHERE callsign LIKE 'TEST%'")
    cursor.execute("DELETE FROM flight_summaries WHERE callsign LIKE 'TEST%'")
    cursor.execute("DELETE FROM flights_archive WHERE callsign LIKE 'TEST%'")
    
    conn.commit()
    cursor.close()
    
    print(f"\n🧹 Cleaned up all test data")

def main():
    """Main test execution"""
    
    print("🧪 Comprehensive Flight Identification Logic Test")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected to database")
        
        # Create and insert dummy flights
        test_flights = create_dummy_flights()
        insert_dummy_flights(conn, test_flights)
        
        # Test 1: Flight identification query
        identified_flights = test_flight_identification_query(conn)
        
        # Test 2: Incomplete flight filtering
        incomplete_flights = test_incomplete_flight_filtering(conn)
        
        # Test 3: Flight summary creation simulation
        summary_flights = test_flight_summary_creation_simulation(conn)
        
        # Test 4: Verify the logic works as expected
        print(f"\n🎯 Test Results Summary:")
        print(f"  Total test flights created: {len(test_flights)}")
        print(f"  Flights with complete plans: {len([f for f in test_flights if f['departure'] and f['arrival']])}")
        print(f"  Flights with incomplete plans: {len([f for f in test_flights if not f['departure'] or not f['arrival']])}")
        print(f"  Unique flight identifiers found: {len(identified_flights)}")
        print(f"  Incomplete flights filtered out: {len(incomplete_flights)}")
        print(f"  Flight summaries that would be created: {len(summary_flights)}")
        
        # Verify our logic is working
        expected_complete = len([f for f in test_flights if f['departure'] and f['arrival']])
        if len(identified_flights) == expected_complete:
            print(f"\n✅ SUCCESS: Flight identification logic working correctly!")
            print(f"   Expected {expected_complete} complete flights, found {len(identified_flights)}")
        else:
            print(f"\n❌ FAILURE: Flight identification logic not working as expected!")
            print(f"   Expected {expected_complete} complete flights, but found {len(identified_flights)}")
        
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
    main()
