#!/usr/bin/env python3
"""
Script to move older flights from flights_archive to flights table for summarization.
"""

import sys
import asyncio
from datetime import datetime, timezone

# Add app to path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

from app.database import get_database_session
from sqlalchemy import text

async def move_archive_flights_to_main():
    """Move older flights from archive to main table for summarization."""
    try:
        async with get_database_session() as session:
            print("Moving older flights from archive to main table...")
            
            # First, let's see what we have
            result = await session.execute(text("""
                SELECT COUNT(*) as archive_count 
                FROM flights_archive 
                WHERE last_updated < NOW() - INTERVAL '14 hours'
            """))
            archive_count = result.scalar()
            print(f"Found {archive_count} archived flights > 14 hours old")
            
            # Check current main table count
            result = await session.execute(text("SELECT COUNT(*) FROM flights"))
            main_count = result.scalar()
            print(f"Current main flights table: {main_count} records")
            
            # Move some older flights (let's start with 1000 to test)
            print("\nMoving 1000 older flights from archive to main table...")
            
            # Insert flights from archive to main table
            insert_result = await session.execute(text("""
                INSERT INTO flights (
                    callsign, aircraft_type, departure, arrival, deptime, logon_time,
                    route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
                    cid, name, server, pilot_rating, military_rating, latitude, longitude,
                    altitude, groundspeed, heading, last_updated, created_at, updated_at
                )
                SELECT 
                    callsign, aircraft_type, departure, arrival, deptime, logon_time,
                    route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
                    cid, name, server, pilot_rating, military_rating, latitude, longitude,
                    altitude, groundspeed, heading, last_updated, created_at, updated_at
                FROM flights_archive 
                WHERE last_updated < NOW() - INTERVAL '14 hours'
                AND callsign NOT IN (SELECT DISTINCT callsign FROM flights)
                LIMIT 1000
            """))
            
            await session.commit()
            
            # Check new count
            result = await session.execute(text("SELECT COUNT(*) FROM flights"))
            new_main_count = result.scalar()
            moved_count = new_main_count - main_count
            
            print(f"✅ Successfully moved {moved_count} flights from archive to main table")
            print(f"New main table count: {new_main_count}")
            
            # Check how many are now > 14 hours old
            result = await session.execute(text("""
                SELECT COUNT(*) as flights_over_14h 
                FROM flights 
                WHERE last_updated < NOW() - INTERVAL '14 hours'
            """))
            eligible_count = result.scalar()
            print(f"Flights > 14 hours old: {eligible_count}")
            
            return moved_count
            
    except Exception as e:
        print(f"Error moving flights: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    moved = asyncio.run(move_archive_flights_to_main())
    print(f"\nTotal flights moved: {moved}")
