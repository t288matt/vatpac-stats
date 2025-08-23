#!/usr/bin/env python3
"""
Script to move flight summaries data to the flights table.
This handles the mapping between flight_summaries and flights schemas.
"""

import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path for imports
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

from app.config import get_config

async def move_flight_summaries_to_flights():
    """Move all flight summaries to the flights table."""
    
    # Get database URL from config
    config = get_config()
    database_url = config.database.url
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        # First, let's see how many flight summaries we have
        result = await conn.execute(text("SELECT COUNT(*) FROM flight_summaries"))
        count = result.scalar()
        print(f"Found {count} flight summaries to move")
        
        if count == 0:
            print("No flight summaries to move")
            return
        
        # Check if there are existing flights to avoid duplicates
        result = await conn.execute(text("SELECT COUNT(*) FROM flights"))
        existing_count = result.scalar()
        print(f"Existing flights count: {existing_count}")
        
        # Insert flight summaries into flights table
        # Map the fields appropriately between the two schemas
        # Since there's no unique constraint on callsign, we'll insert all records
        insert_query = """
        INSERT INTO flights (
            callsign, aircraft_type, departure, arrival, route, flight_rules,
            aircraft_faa, aircraft_short, planned_altitude, deptime,
            cid, name, server, pilot_rating, military_rating, logon_time,
            last_updated, created_at, updated_at
        )
        SELECT 
            fs.callsign,
            fs.aircraft_type,
            fs.departure,
            fs.arrival,
            fs.route,
            fs.flight_rules,
            fs.aircraft_faa,
            fs.aircraft_short,
            fs.planned_altitude,
            fs.deptime,
            fs.cid,
            fs.name,
            fs.server,
            fs.pilot_rating,
            fs.military_rating,
            fs.logon_time,
            COALESCE(fs.completion_time, NOW()) as last_updated,
            fs.created_at,
            fs.updated_at
        FROM flight_summaries fs
        """
        
        print("Moving flight summaries to flights table...")
        await conn.execute(text(insert_query))
        
        # Verify the move
        result = await conn.execute(text("SELECT COUNT(*) FROM flights"))
        flights_count = result.scalar()
        print(f"Flights table now contains {flights_count} records")
        print(f"Added {flights_count - existing_count} new flight records")
        
        # Show some sample data
        result = await conn.execute(text("""
            SELECT callsign, departure, arrival, aircraft_type, logon_time
            FROM flights 
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        print("\nSample flights data:")
        for row in result:
            print(f"  {row.callsign}: {row.departure} -> {row.arrival} ({row.aircraft_type}) - Logon: {row.logon_time}")
    
    await engine.dispose()
    print("\nFlight summaries moved successfully!")

if __name__ == "__main__":
    asyncio.run(move_flight_summaries_to_flights())
