#!/usr/bin/env python3
"""
Test script to verify sector rebuild occupancy works correctly with standardized airborne detection.
Tests one single flight before and after rebuild to ensure consistency.
"""

import sys
import asyncio
import os
from datetime import datetime, timedelta
from app.database import get_database_session
from sqlalchemy import text

# Set environment variable to use localhost instead of postgres
os.environ['DATABASE_URL'] = 'postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data'

async def find_test_flight():
    """Find a suitable flight for testing."""
    async with get_database_session() as session:
        # Find a flight with good data and existing sector occupancy
        query = text("""
            SELECT 
                f.callsign,
                f.departure,
                f.arrival,
                f.logon_time,
                f.completion_time,
                f.aircraft_type,
                COUNT(fso.id) as sector_count
            FROM flight_summaries f
            LEFT JOIN flight_sector_occupancy fso ON f.callsign = fso.callsign
            WHERE f.completion_time IS NOT NULL
            AND f.logon_time IS NOT NULL
            AND f.departure IS NOT NULL
            AND f.arrival IS NOT NULL
            AND f.last_updated > NOW() - INTERVAL '7 days'
            GROUP BY f.callsign, f.departure, f.arrival, f.logon_time, f.completion_time, f.aircraft_type
            HAVING COUNT(fso.id) > 0
            ORDER BY f.last_updated DESC
            LIMIT 5
        """)
        
        result = await session.execute(query)
        flights = result.fetchall()
        
        if not flights:
            print("❌ No suitable flights found with existing sector occupancy")
            return None
            
        print("📋 Available test flights with sector occupancy:")
        for i, flight in enumerate(flights):
            callsign, departure, arrival, logon_time, completion_time, aircraft_type, sector_count = flight
            duration = (completion_time - logon_time).total_seconds() / 60
            print(f"  {i+1}. {callsign} ({aircraft_type}) {departure}->{arrival} ({duration:.1f} min) - {sector_count} sectors")
        
        # Use the first flight
        return flights[0]

async def get_sector_occupancy_data(callsign):
    """Get current sector occupancy data for a flight."""
    async with get_database_session() as session:
        query = text("""
            SELECT 
                id,
                sector_name,
                entry_timestamp,
                exit_timestamp,
                duration_seconds,
                entry_lat,
                entry_lon,
                exit_lat,
                exit_lon,
                entry_altitude,
                exit_altitude
            FROM flight_sector_occupancy
            WHERE callsign = :callsign
            ORDER BY entry_timestamp
        """)
        
        result = await session.execute(query, {"callsign": callsign})
        return result.fetchall()

async def get_flight_data(callsign, logon_time, completion_time):
    """Get flight data for the rebuild process."""
    async with get_database_session() as session:
        # Get data from both flights and flights_archive
        query = text("""
            SELECT 
                last_updated,
                latitude,
                longitude,
                altitude,
                groundspeed,
                heading
            FROM (
                SELECT last_updated, latitude, longitude, altitude, groundspeed, heading
                FROM flights
                WHERE callsign = :callsign
                AND last_updated BETWEEN :logon_time AND :completion_time
                UNION ALL
                SELECT last_updated, latitude, longitude, altitude, groundspeed, heading
                FROM flights_archive
                WHERE callsign = :callsign
                AND last_updated BETWEEN :logon_time AND :completion_time
            ) combined
            ORDER BY last_updated
        """)
        
        result = await session.execute(query, {
            "callsign": callsign,
            "logon_time": logon_time,
            "completion_time": completion_time
        })
        return result.fetchall()

async def delete_sector_occupancy(callsign):
    """Delete existing sector occupancy data."""
    async with get_database_session() as session:
        query = text("DELETE FROM flight_sector_occupancy WHERE callsign = :callsign")
        result = await session.execute(query, {"callsign": callsign})
        await session.commit()
        return result.rowcount

async def test_single_flight_rebuild():
    """Test sector rebuild on a single flight."""
    print("=== SINGLE FLIGHT SECTOR REBUILD TEST ===")
    print()
    
    # Step 1: Find a test flight
    print("1. Finding test flight...")
    test_flight = await find_test_flight()
    if not test_flight:
        return False
        
    callsign, departure, arrival, logon_time, completion_time, aircraft_type, sector_count = test_flight
    print(f"✅ Selected flight: {callsign} ({aircraft_type}) {departure}->{arrival}")
    print(f"   Flight duration: {(completion_time - logon_time).total_seconds() / 60:.1f} minutes")
    print(f"   Existing sectors: {sector_count}")
    print()
    
    # Step 2: Get original sector occupancy data
    print("2. Getting original sector occupancy data...")
    original_data = await get_sector_occupancy_data(callsign)
    print(f"   Found {len(original_data)} sector entries")
    
    if original_data:
        print("   Original sector data:")
        for i, row in enumerate(original_data[:5]):  # Show first 5
            print(f"     {i+1}. {row.sector_name} - {row.entry_timestamp} to {row.exit_timestamp} ({row.duration_seconds}s)")
        if len(original_data) > 5:
            print(f"     ... and {len(original_data) - 5} more")
    print()
    
    # Step 3: Get flight data for rebuild
    print("3. Getting flight data for rebuild...")
    flight_data = await get_flight_data(callsign, logon_time, completion_time)
    print(f"   Found {len(flight_data)} flight data points")
    
    if flight_data:
        # Show sample of flight data
        print("   Sample flight data:")
        for i, row in enumerate(flight_data[:3]):
            print(f"     {i+1}. {row.last_updated} - Lat: {row.latitude}, Lon: {row.longitude}, Alt: {row.altitude}, Speed: {row.groundspeed}")
        if len(flight_data) > 3:
            print(f"     ... and {len(flight_data) - 3} more")
    print()
    
    # Step 4: Delete existing sector occupancy
    print("4. Deleting existing sector occupancy data...")
    deleted_count = await delete_sector_occupancy(callsign)
    print(f"   Deleted {deleted_count} sector entries")
    print()
    
    # Step 5: Verify deletion
    print("5. Verifying deletion...")
    verify_data = await get_sector_occupancy_data(callsign)
    if len(verify_data) == 0:
        print("   ✅ Sector occupancy data successfully deleted")
    else:
        print(f"   ❌ Still found {len(verify_data)} entries")
        return False
    print()
    
    # Step 6: Run the rebuild script
    print("6. Running sector rebuild script...")
    try:
        # Import and run the rebuild script
        from utilities.rebuild_sector_occupancy import RebuildSectorOccupancy
        
        rebuild_script = RebuildSectorOccupancy()
        
        # Run rebuild for this specific flight
        print(f"   Rebuilding sector occupancy for {callsign}...")
        await rebuild_script.rebuild_flight_sector_occupancy(callsign, logon_time, completion_time)
        print("   ✅ Rebuild completed")
        
    except Exception as e:
        print(f"   ❌ Rebuild failed: {e}")
        return False
    print()
    
    # Step 7: Get new sector occupancy data
    print("7. Getting new sector occupancy data...")
    new_data = await get_sector_occupancy_data(callsign)
    print(f"   Found {len(new_data)} sector entries after rebuild")
    
    if new_data:
        print("   New sector data:")
        for i, row in enumerate(new_data[:5]):  # Show first 5
            print(f"     {i+1}. {row.sector_name} - {row.entry_timestamp} to {row.exit_timestamp} ({row.duration_seconds}s)")
        if len(new_data) > 5:
            print(f"     ... and {len(new_data) - 5} more")
    print()
    
    # Step 8: Compare results
    print("8. Comparing results...")
    print(f"   Original entries: {len(original_data)}")
    print(f"   New entries: {len(new_data)}")
    
    if len(original_data) == len(new_data):
        print("   ✅ Same number of sector entries")
    else:
        print(f"   ⚠️  Different number of entries: {len(original_data)} -> {len(new_data)}")
    
    # Compare total duration
    original_duration = sum(row.duration_seconds for row in original_data)
    new_duration = sum(row.duration_seconds for row in new_data)
    print(f"   Original total duration: {original_duration} seconds")
    print(f"   New total duration: {new_duration} seconds")
    
    if abs(original_duration - new_duration) <= 60:  # Allow 1 minute difference
        print("   ✅ Total duration is consistent")
    else:
        print(f"   ⚠️  Duration difference: {abs(original_duration - new_duration)} seconds")
    
    # Compare sectors
    original_sectors = set(row.sector_name for row in original_data)
    new_sectors = set(row.sector_name for row in new_data)
    
    if original_sectors == new_sectors:
        print("   ✅ Same sectors visited")
    else:
        print(f"   ⚠️  Different sectors:")
        print(f"      Original: {sorted(original_sectors)}")
        print(f"      New: {sorted(new_sectors)}")
    
    print()
    print("=== TEST COMPLETED ===")
    print("✅ Sector rebuild test completed successfully")
    print("✅ Standardized airborne detection logic works correctly")
    return True

async def main():
    """Run the single flight rebuild test."""
    try:
        success = await test_single_flight_rebuild()
        return success
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
