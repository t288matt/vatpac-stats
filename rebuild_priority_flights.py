#!/usr/bin/env python3
"""
Rebuild Priority Flights - Only rebuild flights that actually need it
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import our rebuild functionality
sys.path.append(os.path.dirname(__file__))
from rebuild_sector_occupancy import SectorOccupancyRebuilder

class PriorityFlightRebuilder:
    def __init__(self, db_url: str):
        self.db_url = db_url
        geojson_path = os.path.join(os.path.dirname(__file__), "config", "australian_airspace_sectors.geojson")
        self.rebuilder = SectorOccupancyRebuilder(db_url, geojson_path)
        
    async def get_priority_flights(self) -> List[Tuple[str, int, datetime]]:
        """Get flights that actually need rebuilding"""
        
        engine = create_async_engine(self.db_url)
        session_factory = sessionmaker(bind=engine, class_=AsyncSession)
        
        priority_flights = []
        
        async with session_factory() as session:
            # 1. Flights with no sector records (HIGH PRIORITY)
            print("[PRIORITY] Finding flights with no sector records...")
            result = await session.execute(text("""
                SELECT DISTINCT fs.callsign, fs.cid, fs.completion_time
                FROM flight_summaries fs
                LEFT JOIN flight_sector_occupancy fso ON fs.callsign = fso.callsign
                WHERE fs.completion_time > '2025-09-01'
                AND fso.callsign IS NULL
                ORDER BY fs.completion_time DESC
                LIMIT 100
            """))
            
            no_sector_flights = result.fetchall()
            print(f"[PRIORITY] Found {len(no_sector_flights)} flights with no sector records")
            
            for flight in no_sector_flights:
                priority_flights.append({
                    'callsign': flight.callsign,
                    'cid': flight.cid,
                    'completion_time': flight.completion_time,
                    'reason': 'no_sector_records',
                    'priority': 'HIGH'
                })
            
            # 2. Flights with impossible timestamps or negative durations (HIGH PRIORITY)
            print("[PRIORITY] Finding flights with data corruption...")
            result = await session.execute(text("""
                SELECT DISTINCT callsign, cid, completion_time
                FROM flight_summaries fs
                WHERE fs.callsign IN (
                    SELECT DISTINCT fso.callsign
                    FROM flight_sector_occupancy fso
                    WHERE (fso.exit_timestamp IS NOT NULL AND fso.exit_timestamp < fso.entry_timestamp)
                    OR fso.duration_seconds < 0
                )
                AND fs.completion_time > '2025-09-01'
                ORDER BY fs.completion_time DESC
                LIMIT 50
            """))
            
            corrupted_flights = result.fetchall()
            print(f"[PRIORITY] Found {len(corrupted_flights)} flights with data corruption")
            
            for flight in corrupted_flights:
                priority_flights.append({
                    'callsign': flight.callsign,
                    'cid': flight.cid,
                    'completion_time': flight.completion_time,
                    'reason': 'data_corruption',
                    'priority': 'HIGH'
                })
            
            # 3. Flights with overlapping entries (MEDIUM PRIORITY)
            print("[PRIORITY] Finding flights with overlapping entries...")
            result = await session.execute(text("""
                SELECT DISTINCT fs.callsign, fs.cid, fs.completion_time
                FROM flight_summaries fs
                WHERE fs.callsign IN (
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
                    SELECT callsign FROM overlapping_check
                )
                AND fs.completion_time > '2025-09-01'
                ORDER BY fs.completion_time DESC
                LIMIT 50
            """))
            
            overlapping_flights = result.fetchall()
            print(f"[PRIORITY] Found {len(overlapping_flights)} flights with overlapping entries")
            
            for flight in overlapping_flights:
                priority_flights.append({
                    'callsign': flight.callsign,
                    'cid': flight.cid,
                    'completion_time': flight.completion_time,
                    'reason': 'overlapping_entries',
                    'priority': 'MEDIUM'
                })
        
        return priority_flights
    
    async def _delete_existing_sector_records(self, callsign: str, cid: int, completion_time: datetime) -> None:
        """Delete existing sector records for a flight"""
        
        engine = create_async_engine(self.db_url)
        session_factory = sessionmaker(bind=engine, class_=AsyncSession)
        
        async with session_factory() as session:
            # Delete existing sector records for this flight
            result = await session.execute(text("""
                DELETE FROM flight_sector_occupancy
                WHERE callsign = :callsign
            """), {"callsign": callsign})
            
            deleted_count = result.rowcount
            await session.commit()
            
            if deleted_count > 0:
                print(f"[DELETE] Removed {deleted_count} existing sector records")
    
    async def rebuild_priority_flights(self, max_flights: int = 20) -> None:
        """Rebuild priority flights"""
        
        print("=" * 80)
        print("PRIORITY FLIGHT REBUILD")
        print("=" * 80)
        
        # Get priority flights
        priority_flights = await self.get_priority_flights()
        
        if not priority_flights:
            print("[SUCCESS] No flights need rebuilding!")
            return
        
        print(f"[TOTAL] Found {len(priority_flights)} flights needing rebuild")
        
        # Group by priority
        high_priority = [f for f in priority_flights if f['priority'] == 'HIGH']
        medium_priority = [f for f in priority_flights if f['priority'] == 'MEDIUM']
        
        print(f"[HIGH] {len(high_priority)} high priority flights")
        print(f"[MEDIUM] {len(medium_priority)} medium priority flights")
        
        # Rebuild high priority flights first
        flights_to_rebuild = high_priority[:max_flights]
        
        print(f"\n[REBUILD] Starting rebuild of {len(flights_to_rebuild)} high priority flights...")
        
        success_count = 0
        error_count = 0
        
        for i, flight in enumerate(flights_to_rebuild):
            try:
                print(f"\n[REBUILD {i+1}/{len(flights_to_rebuild)}] {flight['callsign']} (CID: {flight['cid']}) - {flight['reason']}")
                
                # Delete existing sector records for this flight first
                await self._delete_existing_sector_records(
                    flight['callsign'], flight['cid'], flight['completion_time']
                )
                
                # Rebuild from flight data
                result = await self.rebuilder.rebuild_flight_sectors(
                    flight['callsign'], flight['cid'], flight['completion_time']
                )
                
                if result:
                    print(f"[SUCCESS] Rebuilt {result['sectors_created']} sector records")
                    success_count += 1
                else:
                    print(f"[WARNING] No sector records created")
                    error_count += 1
                    
            except Exception as e:
                print(f"[ERROR] Failed to rebuild {flight['callsign']}: {e}")
                error_count += 1
        
        print(f"\n[SUMMARY] Rebuild completed:")
        print(f"  - Success: {success_count}")
        print(f"  - Errors: {error_count}")
        print(f"  - Total: {success_count + error_count}")

async def main():
    """Main function"""
    
    db_url = "postgresql+asyncpg://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
    
    rebuilder = PriorityFlightRebuilder(db_url)
    await rebuilder.rebuild_priority_flights(max_flights=10)

if __name__ == "__main__":
    asyncio.run(main())
