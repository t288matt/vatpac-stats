#!/usr/bin/env python3
"""
Script to move data from archive tables to main operational tables.
This handles the schema differences between archive and main tables.
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

async def move_archives_to_main():
    """Move data from archive tables to main operational tables."""
    
    # Get database URL from config
    config = get_config()
    database_url = config.database.url
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        print("Moving archive data to main tables...")
        
        # Move flights from flights_archive to flights
        print("\n1. Moving flights from flights_archive to flights...")
        
        # First check counts
        result = await conn.execute(text("SELECT COUNT(*) FROM flights_archive"))
        archive_count = result.scalar()
        result = await conn.execute(text("SELECT COUNT(*) FROM flights"))
        flights_count = result.scalar()
        
        print(f"  Flights archive: {archive_count} records")
        print(f"  Current flights: {flights_count} records")
        
        if archive_count > 0:
            # Insert flights from archive, handling schema differences
            insert_flights_query = """
            INSERT INTO flights (
                callsign, aircraft_type, departure, arrival, route, flight_rules,
                aircraft_faa, aircraft_short, planned_altitude, deptime,
                cid, name, server, pilot_rating, military_rating, logon_time,
                last_updated, created_at, updated_at
            )
            SELECT 
                fa.callsign,
                fa.aircraft_type,
                fa.departure,
                fa.arrival,
                fa.route,
                fa.flight_rules,
                fa.aircraft_faa,
                fa.aircraft_short,
                fa.planned_altitude,
                fa.deptime,
                fa.cid,
                fa.name,
                fa.server,
                fa.pilot_rating,
                fa.military_rating,
                fa.logon_time,
                COALESCE(fa.last_updated, NOW()) as last_updated,
                fa.created_at,
                fa.updated_at
            FROM flights_archive fa
            """
            
            await conn.execute(text(insert_flights_query))
            
            # Verify the move
            result = await conn.execute(text("SELECT COUNT(*) FROM flights"))
            new_flights_count = result.scalar()
            print(f"  Flights table now contains: {new_flights_count} records")
            print(f"  Added: {new_flights_count - flights_count} records")
        
        # Move controllers from controllers_archive to controllers
        print("\n2. Moving controllers from controllers_archive to controllers...")
        
        result = await conn.execute(text("SELECT COUNT(*) FROM controllers_archive"))
        archive_count = result.scalar()
        result = await conn.execute(text("SELECT COUNT(*) FROM controllers"))
        controllers_count = result.scalar()
        
        print(f"  Controllers archive: {archive_count} records")
        print(f"  Current controllers: {controllers_count} records")
        
        if archive_count > 0:
            # Insert controllers from archive
            insert_controllers_query = """
            INSERT INTO controllers (
                callsign, frequency, cid, name, rating, facility, 
                visual_range, text_atis, server, last_updated, 
                logon_time, created_at, updated_at
            )
            SELECT 
                ca.callsign,
                ca.frequency,
                ca.cid,
                ca.name,
                ca.rating,
                ca.facility,
                ca.visual_range,
                ca.text_atis,
                ca.server,
                COALESCE(ca.last_updated, NOW()) as last_updated,
                ca.logon_time,
                ca.created_at,
                ca.updated_at
            FROM controllers_archive ca
            """
            
            await conn.execute(text(insert_controllers_query))
            
            # Verify the move
            result = await conn.execute(text("SELECT COUNT(*) FROM controllers"))
            new_controllers_count = result.scalar()
            print(f"  Controllers table now contains: {new_controllers_count} records")
            print(f"  Added: {new_controllers_count - controllers_count} records")
        
        # Show final counts
        print("\n3. Final table counts:")
        result = await conn.execute(text("SELECT 'flights' as table_name, COUNT(*) as count FROM flights UNION ALL SELECT 'controllers' as table_name, COUNT(*) as count FROM controllers UNION ALL SELECT 'flights_archive' as table_name, COUNT(*) as count FROM flights_archive UNION ALL SELECT 'controllers_archive' as table_name, COUNT(*) as count FROM controllers_archive ORDER BY table_name"))
        
        for row in result:
            print(f"  {row.table_name}: {row.count} records")
    
    await engine.dispose()
    print("\nArchive data moved successfully!")

if __name__ == "__main__":
    asyncio.run(move_archives_to_main())
