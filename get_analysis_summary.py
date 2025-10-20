#!/usr/bin/env python3
"""
Get just the summary from the flight analysis
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

async def get_summary():
    """Get summary of flight analysis"""
    
    db_url = "postgresql+asyncpg://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
    engine = create_async_engine(db_url)
    session_factory = sessionmaker(bind=engine, class_=AsyncSession)
    
    async with session_factory() as session:
        # Get total flights
        result = await session.execute(text("""
            SELECT COUNT(DISTINCT CONCAT(callsign, '_', cid, '_', completion_time)) as total_flights
            FROM flight_summaries
            WHERE completion_time > '2025-09-01'
        """))
        total_flights = result.fetchone().total_flights
        
        # Get flights with no sector records
        result = await session.execute(text("""
            SELECT COUNT(DISTINCT fs.callsign || '_' || fs.cid || '_' || fs.completion_time) as no_sectors
            FROM flight_summaries fs
            LEFT JOIN flight_sector_occupancy fso ON fs.callsign = fso.callsign
            WHERE fs.completion_time > '2025-09-01'
            AND fso.callsign IS NULL
        """))
        no_sectors = result.fetchone().no_sectors
        
        # Get flights with fragmented sectors (multiple entries to same sector)
        result = await session.execute(text("""
            SELECT COUNT(DISTINCT fso.callsign) as fragmented
            FROM flight_sector_occupancy fso
            WHERE fso.exit_timestamp IS NOT NULL
            AND EXISTS (
                SELECT 1 FROM flight_sector_occupancy fso2
                WHERE fso2.callsign = fso.callsign
                AND fso2.sector_name = fso.sector_name
                AND fso2.id != fso.id
                AND fso2.exit_timestamp IS NOT NULL
            )
        """))
        fragmented = result.fetchone().fragmented
        
        # Get flights with impossible timestamps
        result = await session.execute(text("""
            SELECT COUNT(DISTINCT callsign) as impossible_timestamps
            FROM flight_sector_occupancy
            WHERE exit_timestamp IS NOT NULL
            AND exit_timestamp < entry_timestamp
        """))
        impossible_timestamps = result.fetchone().impossible_timestamps
        
        # Get flights with negative durations
        result = await session.execute(text("""
            SELECT COUNT(DISTINCT callsign) as negative_durations
            FROM flight_sector_occupancy
            WHERE duration_seconds < 0
        """))
        negative_durations = result.fetchone().negative_durations
        
        # Get flights with overlapping entries
        result = await session.execute(text("""
            WITH overlapping_check AS (
                SELECT fso1.callsign
                FROM flight_sector_occupancy fso1
                JOIN flight_sector_occupancy fso2 ON fso1.callsign = fso2.callsign
                WHERE fso1.id < fso2.id
                AND fso1.sector_name = fso2.sector_name
                AND fso1.entry_timestamp < fso2.exit_timestamp
                AND fso1.exit_timestamp > fso2.entry_timestamp
                AND fso1.exit_timestamp IS NOT NULL
                AND fso2.exit_timestamp IS NOT NULL
            )
            SELECT COUNT(DISTINCT callsign) as overlapping FROM overlapping_check
        """))
        overlapping = result.fetchone().overlapping
    
    print("=" * 80)
    print("FLIGHT ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Total flights analyzed: {total_flights:,}")
    print(f"")
    print(f"ISSUES FOUND:")
    print(f"  - No sector records: {no_sectors:,}")
    print(f"  - Fragmented sectors: {fragmented:,}")
    print(f"  - Impossible timestamps: {impossible_timestamps:,}")
    print(f"  - Negative durations: {negative_durations:,}")
    print(f"  - Overlapping entries: {overlapping:,}")
    print(f"")
    
    # Calculate total flights needing rebuild
    total_issues = no_sectors + fragmented + impossible_timestamps + negative_durations + overlapping
    clean_flights = total_flights - total_issues
    
    print(f"SUMMARY:")
    print(f"  - Clean flights: {clean_flights:,} ({clean_flights/total_flights*100:.1f}%)")
    print(f"  - Flights needing rebuild: {total_issues:,} ({total_issues/total_flights*100:.1f}%)")
    
    # Priority recommendations
    print(f"")
    print(f"REBUILD PRIORITY:")
    if no_sectors > 0:
        print(f"  1. HIGH: {no_sectors:,} flights with missing sector records")
    if impossible_timestamps > 0 or negative_durations > 0:
        print(f"  2. HIGH: {impossible_timestamps + negative_durations:,} flights with data corruption")
    if overlapping > 0:
        print(f"  3. MEDIUM: {overlapping:,} flights with overlapping entries")
    if fragmented > 0:
        print(f"  4. LOW: {fragmented:,} flights with fragmented sectors (may be normal)")

if __name__ == "__main__":
    asyncio.run(get_summary())



