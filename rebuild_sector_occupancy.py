#!/usr/bin/env python3
"""
Rebuild Sector Occupancy from Flight Data
Uses the same logic as the existing sector tracking code
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path to import the sector loader
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.utils.sector_loader import SectorLoader

class SectorOccupancyRebuilder:
    def __init__(self, db_url: str, geojson_path: str):
        self.engine = create_async_engine(db_url)
        self.session_factory = sessionmaker(bind=self.engine, class_=AsyncSession)
        
        # Use the same sector loader as the original code
        self.sector_loader = SectorLoader(geojson_path)
        if not self.sector_loader.load_sectors():
            raise RuntimeError("Failed to load sector boundaries")
        
        # Flight sector states (same as original code)
        self.flight_sector_states = {}
        
    async def _delete_existing_sector_records(self, callsign: str, cid: int, completion_time: datetime):
        """Delete existing sector occupancy records for a specific flight session"""
        async with self.session_factory() as session:
            # First, check if there are any NULL CID records to delete
            result = await session.execute(text("""
                SELECT COUNT(*) FROM flight_sector_occupancy
                WHERE callsign = :callsign AND cid IS NULL
                AND entry_timestamp <= :completion_time
                AND (exit_timestamp IS NULL OR exit_timestamp <= :completion_time)
            """), {
                "callsign": callsign,
                "completion_time": completion_time
            })
            null_cid_count = result.scalar()
            
            if null_cid_count > 0:
                print(f"Warning: Deleting {null_cid_count} NULL CID records for {callsign}")
                
            # Delete both matching CID and NULL CID records
            await session.execute(text("""
                DELETE FROM flight_sector_occupancy 
                WHERE callsign = :callsign 
                AND (cid = :cid OR cid IS NULL)
                AND entry_timestamp <= :completion_time
                AND (exit_timestamp IS NULL OR exit_timestamp <= :completion_time)
            """), {
                "callsign": callsign,
                "cid": cid,
                "completion_time": completion_time
            })
            await session.commit()

    async def rebuild_flight_sectors(self, callsign: str, cid: int, completion_time: datetime) -> List[Dict]:
        """Rebuild sector occupancy for a single flight using EXACT production logic"""
        
        # Delete existing records for this flight session first
        await self._delete_existing_sector_records(callsign, cid, completion_time)
        
        # Get flight data from both current and archive tables, ordered by timestamp
        # Use completion_time to identify a SINGLE flight session
        async with self.session_factory() as session:
            # Get flight records for the specific flight session ending at completion_time
            # First, check if there's a previous completion time for this callsign/CID
            prev_result = await session.execute(text("""
                SELECT COALESCE(MAX(fs2.completion_time), '1970-01-01'::timestamp) as prev_time
                FROM flight_summaries fs2 
                WHERE fs2.callsign = :callsign AND fs2.cid = :cid AND fs2.completion_time < :completion_time
            """), {
                "callsign": callsign,
                "cid": cid,
                "completion_time": completion_time
            })
            prev_completion_time = prev_result.scalar()
            
            # Build the query based on whether there's a previous completion time
            if prev_completion_time == datetime(1970, 1, 1, tzinfo=timezone.utc):
                # No previous completion time - get all records up to completion time
                result = await session.execute(text("""
                    SELECT f.callsign, f.last_updated, f.latitude, f.longitude, f.altitude, f.groundspeed, 'current' as source
                    FROM flights f
                    JOIN flight_summaries fs ON f.callsign = fs.callsign AND f.cid = fs.cid
                    WHERE f.callsign = :callsign AND f.cid = :cid AND fs.completion_time = :completion_time
                    AND f.last_updated <= :completion_time
                    
                    UNION ALL
                    
                    SELECT fa.callsign, fa.last_updated, fa.latitude, fa.longitude, fa.altitude, fa.groundspeed, 'archive' as source
                    FROM flights_archive fa
                    JOIN flight_summaries fs ON fa.callsign = fs.callsign AND fa.cid = fs.cid
                    WHERE fa.callsign = :callsign AND fa.cid = :cid AND fs.completion_time = :completion_time
                    AND fa.last_updated <= :completion_time
                    
                    ORDER BY last_updated
                """), {
                    "callsign": callsign,
                    "cid": cid,
                    "completion_time": completion_time
                })
            else:
                # There's a previous completion time - use it as lower bound
                result = await session.execute(text("""
                    SELECT f.callsign, f.last_updated, f.latitude, f.longitude, f.altitude, f.groundspeed, 'current' as source
                    FROM flights f
                    JOIN flight_summaries fs ON f.callsign = fs.callsign AND f.cid = fs.cid
                    WHERE f.callsign = :callsign AND f.cid = :cid AND fs.completion_time = :completion_time
                    AND f.last_updated <= :completion_time
                    AND f.last_updated > :prev_completion_time
                    
                    UNION ALL
                    
                    SELECT fa.callsign, fa.last_updated, fa.latitude, fa.longitude, fa.altitude, fa.groundspeed, 'archive' as source
                    FROM flights_archive fa
                    JOIN flight_summaries fs ON fa.callsign = fs.callsign AND fa.cid = fs.cid
                    WHERE fa.callsign = :callsign AND fa.cid = :cid AND fs.completion_time = :completion_time
                    AND fa.last_updated <= :completion_time
                    AND fa.last_updated > :prev_completion_time
                    
                    ORDER BY last_updated
                """), {
                    "callsign": callsign,
                    "cid": cid,
                    "completion_time": completion_time,
                    "prev_completion_time": prev_completion_time
                })
            
            flight_records = result.fetchall()
        
        if not flight_records:
            return []
        
        # Initialize state tracking (EXACT production flight_sector_states)
        flight_sector_states = {}
        rebuilt_records = []
        
        # Process each flight record chronologically, exactly like production
        previous_timestamp = None
        for record in flight_records:
            lat = record.latitude
            lon = record.longitude
            altitude = record.altitude
            groundspeed = record.groundspeed
            timestamp = record.last_updated
            
            if lat is None or lon is None:
                continue
            
            # Detect data gaps (like production would reset state)
            if previous_timestamp:
                gap_seconds = (timestamp - previous_timestamp).total_seconds()
                if gap_seconds > 300:  # 5 minutes gap - reset flight state
                    # Data gap detected - close open sectors and reset state
                    
                    # Close any open sector entries before resetting state
                    for record in rebuilt_records:
                        if (record['callsign'] == callsign and 
                            record['exit_timestamp'] is None):
                            record['exit_timestamp'] = previous_timestamp
                            record['exit_lat'] = lat
                            record['exit_lon'] = lon
                            record['exit_altitude'] = altitude
                            record['duration_seconds'] = int((previous_timestamp - record['entry_timestamp']).total_seconds())
                    
                    flight_sector_states.clear()  # Reset state like production would
            
            # Create flight_dict exactly like production
            flight_dict = {
                "callsign": callsign,
                "latitude": lat,
                "longitude": lon,
                "altitude": altitude,
                "groundspeed": groundspeed,
                "cid": cid
            }
            
            # Call the EXACT production logic
            await self._track_sector_occupancy_production(
                flight_dict, flight_sector_states, rebuilt_records, timestamp
            )
            
            previous_timestamp = timestamp
        
        # After processing all records, close any remaining open sectors using last flight record
        # This mimics production's _close_open_sector_entries behavior
        if rebuilt_records and flight_records:
            last_record = flight_records[-1]  # Get the last flight record
            last_timestamp = last_record.last_updated
            last_lat = last_record.latitude
            last_lon = last_record.longitude
            last_altitude = last_record.altitude
            
            # Ensure no NULL values in the last record data
            if last_lat is None:
                last_lat = 0.0
            if last_lon is None:
                last_lon = 0.0
            if last_altitude is None:
                last_altitude = 0
            
            # Close any open sector entries using the last flight record data
            for record in rebuilt_records:
                if record['exit_timestamp'] is None:
                    # Use last flight record timestamp as exit time (like production cleanup)
                    record['exit_timestamp'] = last_timestamp
                    record['exit_lat'] = last_lat
                    record['exit_lon'] = last_lon
                    record['exit_altitude'] = last_altitude
                    record['duration_seconds'] = int((last_timestamp - record['entry_timestamp']).total_seconds())
        
        # Return the rebuilt records (don't insert here - calling methods will handle insertion)
        return rebuilt_records
    
    async def _track_sector_occupancy_production(
        self, flight_dict: Dict[str, Any], flight_sector_states: Dict, 
        rebuilt_records: List[Dict], timestamp: datetime
    ) -> None:
        """EXACT copy of production _track_sector_occupancy logic"""
        
        callsign = flight_dict.get("callsign")
        if not callsign:
            return
        
        # Get current position and speed
        lat = flight_dict.get("latitude")
        lon = flight_dict.get("longitude")
        altitude = flight_dict.get("altitude")
        groundspeed = flight_dict.get("groundspeed")
        
        if lat is None or lon is None:
            return
        
        # Get current geographic sector
        geographic_sector = self.sector_loader.get_sector_for_point(lat, lon)
        
        # DEBUG: Log sector detection for PTI737
        if callsign == "PTI737":
            print(f"DEBUG {callsign}: {timestamp} - Lat:{lat:.3f}, Lon:{lon:.3f}, Alt:{altitude}, Speed:{groundspeed}, GeoSector:{geographic_sector}")
        
        # Get previous state (combined structure: sector + exit counter)
        previous_state = flight_sector_states.get(callsign, {})
        previous_sector = previous_state.get("current_sector") if isinstance(previous_state, dict) else previous_state
        exit_counter = previous_state.get("exit_counter", 0) if isinstance(previous_state, dict) else 0
        
        # Determine current sector based on speed criteria
        current_sector = None
        
        # Entry logic: Must be above 60 knots to enter sector
        if groundspeed is not None and groundspeed >= 60:
            current_sector = geographic_sector
        elif groundspeed is None:
            # Missing speed data - defer entry decision
            current_sector = previous_sector  # Keep previous state
        else:
            # Speed below 60 knots - not in sector
            current_sector = None
        
        # Exit logic: Track consecutive below-30kts polls
        if groundspeed is not None and groundspeed < 30:
            exit_counter += 1
        else:
            # Speed above 30 knots or missing - reset exit counter
            exit_counter = 0
        
        # Check if we should exit due to 2 consecutive below-30kts polls
        should_exit = exit_counter >= 2
        
        # Handle sector transitions (EXACT production logic)
        if current_sector != previous_sector or should_exit:
            await self._handle_sector_transition_production(
                callsign, previous_sector, current_sector, 
                lat, lon, altitude, should_exit, timestamp, flight_dict, rebuilt_records
            )
            
            # Update state with combined structure
            flight_sector_states[callsign] = {
                "current_sector": current_sector,
                "exit_counter": exit_counter,
                "last_speed": groundspeed
            }
        else:
            # Update state even when no transition occurs
            flight_sector_states[callsign] = {
                "current_sector": current_sector,
                "exit_counter": exit_counter,
                "last_speed": groundspeed
            }
    
    async def _handle_sector_transition_production(
        self, callsign: str, previous_sector: Optional[str], 
        current_sector: Optional[str], lat: float, lon: float, 
        altitude: int, should_exit: bool, timestamp: datetime, 
        flight_dict: Dict[str, Any], rebuilt_records: List[Dict]
    ) -> None:
        """EXACT copy of production _handle_sector_transition logic"""
        
        # CRITICAL FIX: Always close any open entry for this flight-sector combination
        if current_sector:
            await self._close_open_sector_for_flight_and_sector_production(
                callsign, current_sector, timestamp, lat, lon, altitude, rebuilt_records
            )

        # Also close all open sectors if transitioning to different sector or exiting
        if current_sector != previous_sector or should_exit:
            await self._close_all_open_sectors_for_flight_production(
                callsign, timestamp, lat, lon, altitude, rebuilt_records
            )
        
        # Enter new sector (only if different from previous)
        if current_sector and current_sector != previous_sector:
            await self._record_sector_entry_production(
                callsign, current_sector, lat, lon, altitude, timestamp, 
                flight_dict, rebuilt_records
            )
    
    async def _close_open_sector_for_flight_and_sector_production(
        self, callsign: str, sector_name: str, timestamp: datetime,
        lat: float, lon: float, altitude: int, rebuilt_records: List[Dict]
    ) -> None:
        """Production _close_open_sector_for_flight_and_sector logic with NULL prevention"""
        
        # Find and close any open entry for this flight-sector combination
        for record in rebuilt_records:
            if (record['callsign'] == callsign and 
                record['sector_name'] == sector_name and
                record['exit_timestamp'] is None):
                
                # Ensure no NULL values when closing sectors
                record['exit_timestamp'] = timestamp
                record['exit_lat'] = lat if lat is not None else 0.0
                record['exit_lon'] = lon if lon is not None else 0.0
                record['exit_altitude'] = altitude if altitude is not None else 0
                record['duration_seconds'] = int((timestamp - record['entry_timestamp']).total_seconds())
                break  # Only close one entry per sector
    
    async def _close_all_open_sectors_for_flight_production(
        self, callsign: str, timestamp: datetime,
        lat: float, lon: float, altitude: int, rebuilt_records: List[Dict]
    ) -> None:
        """Production _close_all_open_sectors_for_flight logic with NULL prevention"""
        
        # Close all open sectors for this flight
        for record in rebuilt_records:
            if (record['callsign'] == callsign and 
                record['exit_timestamp'] is None):
                
                # Ensure no NULL values when closing sectors
                record['exit_timestamp'] = timestamp
                record['exit_lat'] = lat if lat is not None else 0.0
                record['exit_lon'] = lon if lon is not None else 0.0
                record['exit_altitude'] = altitude if altitude is not None else 0
                record['duration_seconds'] = int((timestamp - record['entry_timestamp']).total_seconds())
    
    async def _record_sector_entry_production(
        self, callsign: str, sector_name: str, lat: float, lon: float, 
        altitude: int, timestamp: datetime, flight_dict: Dict[str, Any], 
        rebuilt_records: List[Dict]
    ) -> None:
        """Production _record_sector_entry logic with NULL field prevention"""
        
        # Extract additional flight data for sector tracking
        cid = flight_dict.get("cid")
        # Ensure CID is never NULL - use a placeholder if needed
        if cid is None:
            print(f"Warning: NULL CID for {callsign} at {timestamp}. Using placeholder.")
            cid = 0  # Use 0 as a placeholder for missing CIDs
            
        departure = flight_dict.get("departure", "")
        arrival = flight_dict.get("arrival", "")
        
        # Ensure no NULL values in any fields
        if departure is None:
            departure = ""
        if arrival is None:
            arrival = ""
        
        # Create new sector entry record
        rebuilt_records.append({
            'callsign': callsign,
            'sector_name': sector_name,
            'entry_timestamp': timestamp,
            'exit_timestamp': None,  # Will be filled later when exiting sector
            'entry_lat': lat,
            'entry_lon': lon,
            'entry_altitude': altitude,
            'exit_lat': None,  # Will be filled later when exiting sector
            'exit_lon': None,  # Will be filled later when exiting sector
            'exit_altitude': None,  # Will be filled later when exiting sector
            'duration_seconds': 0,  # Will be calculated when exiting sector
            'cid': cid,
            'departure': departure,
            'arrival': arrival
        })
    
    async def _insert_rebuilt_records(self, records: List[Dict]) -> None:
        """Insert rebuilt sector records into database with NULL prevention"""
        
        async with self.session_factory() as session:
            for record in records:
                # Ensure no NULL values in any field before inserting
                sanitized_record = {}
                for key, value in record.items():
                    if value is None:
                        if key in ['exit_lat', 'exit_lon', 'entry_lat', 'entry_lon']:
                            sanitized_record[key] = 0.0
                        elif key in ['exit_altitude', 'entry_altitude', 'duration_seconds', 'cid']:
                            sanitized_record[key] = 0
                        elif key in ['departure', 'arrival']:
                            sanitized_record[key] = ""
                        else:
                            # For any other fields, use a reasonable default
                            sanitized_record[key] = value
                    else:
                        sanitized_record[key] = value
                
                await session.execute(text("""
                    INSERT INTO flight_sector_occupancy (
                        callsign, sector_name, entry_timestamp, exit_timestamp,
                        entry_lat, entry_lon, entry_altitude,
                        exit_lat, exit_lon, exit_altitude, duration_seconds, cid
                    ) VALUES (
                        :callsign, :sector_name, :entry_timestamp, :exit_timestamp,
                        :entry_lat, :entry_lon, :entry_altitude,
                        :exit_lat, :exit_lon, :exit_altitude, :duration_seconds, :cid
                    )
                """), sanitized_record)
            
            await session.commit()
    
    async def rebuild_all_flights(self, limit: Optional[int] = None) -> None:
        """Rebuild sector occupancy for all flights"""
        
        # FIXED: Get flights with proper identifiers from flight_summaries
        async with self.session_factory() as session:
            query = """
                SELECT DISTINCT fs.callsign, fs.cid, fs.completion_time
                FROM flight_summaries fs
                WHERE fs.completion_time > '2025-08-01'
                ORDER BY fs.completion_time DESC
            """
            if limit:
                query += f" LIMIT {limit}"
                
            result = await session.execute(text(query))
            flights = result.fetchall()
        
        print(f"Rebuilding sector occupancy for {len(flights)} flights...")
        
        total_records = 0
        success_count = 0
        error_count = 0
        
        for i, flight in enumerate(flights):
            if i % 100 == 0:
                print(f"Processing flight {i+1}/{len(flights)}: {flight.callsign}")
            
            try:
                # FIXED: Call with all required parameters
                rebuilt_records = await self.rebuild_flight_sectors(
                    flight.callsign, flight.cid, flight.completion_time
                )
                
                # FIXED: Insert records into database
                if rebuilt_records:
                    await self._insert_rebuilt_records(rebuilt_records)
                    total_records += len(rebuilt_records)
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                print(f"Error rebuilding {flight.callsign}: {e}")
                error_count += 1
        
        print(f"Rebuild complete. Generated {total_records} sector occupancy records.")
        print(f"Success: {success_count}, Errors: {error_count}")
    
    async def rebuild_priority_flights(self) -> None:
        """Rebuild only flights missing sector data (the 486 priority flights)"""
        
        async with self.session_factory() as session:
            # Get flights with no sector records
            result = await session.execute(text("""
                SELECT DISTINCT fs.callsign, fs.cid, fs.completion_time
                FROM flight_summaries fs
                LEFT JOIN flight_sector_occupancy fso ON fs.callsign = fso.callsign
                WHERE fs.completion_time > '2025-08-01'
                AND fso.callsign IS NULL
                ORDER BY fs.completion_time DESC
            """))
            
            priority_flights = result.fetchall()
        
        print(f"Found {len(priority_flights)} flights missing sector data")
        
        total_records = 0
        success_count = 0
        error_count = 0
        
        for i, flight in enumerate(priority_flights):
            print(f"Processing {i+1}/{len(priority_flights)}: {flight.callsign}")
            
            try:
                rebuilt_records = await self.rebuild_flight_sectors(
                    flight.callsign, flight.cid, flight.completion_time
                )
                
                if rebuilt_records:
                    await self._insert_rebuilt_records(rebuilt_records)
                    total_records += len(rebuilt_records)
                    success_count += 1
                    print(f"  ✅ Generated {len(rebuilt_records)} sector records")
                else:
                    error_count += 1
                    print(f"  ⚠️ No sector records generated")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                error_count += 1
        
        print(f"\nPriority rebuild complete:")
        print(f"  Generated: {total_records} sector records")
        print(f"  Success: {success_count}")
        print(f"  Errors: {error_count}")
    
    async def analyze_data_coverage(self, callsign: str, cid: int, completion_time: datetime) -> Dict:
        """Analyze data coverage for a flight across current and archive tables"""
        async with self.session_factory() as session:
            result = await session.execute(text("""
                SELECT 
                    'current' as source,
                    COUNT(*) as record_count,
                    MIN(f.last_updated) as earliest,
                    MAX(f.last_updated) as latest
                FROM flights f
                JOIN flight_summaries fs ON f.callsign = fs.callsign AND f.cid = fs.cid
                WHERE f.callsign = :callsign AND f.cid = :cid AND fs.completion_time = :completion_time
                
                UNION ALL
                
                SELECT 
                    'archive' as source,
                    COUNT(*) as record_count,
                    MIN(fa.last_updated) as earliest,
                    MAX(fa.last_updated) as latest
                FROM flights_archive fa
                JOIN flight_summaries fs ON fa.callsign = fs.callsign AND fa.cid = fs.cid
                WHERE fa.callsign = :callsign AND fa.cid = :cid AND fs.completion_time = :completion_time
            """), {
                "callsign": callsign,
                "cid": cid,
                "completion_time": completion_time
            })
            
            coverage = {}
            for row in result.fetchall():
                coverage[row.source] = {
                    'record_count': row.record_count,
                    'earliest': row.earliest,
                    'latest': row.latest
                }
            
            return coverage

async def main():
    """Main function to run the rebuild"""
    db_url = "postgresql+asyncpg://vatsim_user:vatsim_password@postgres:5432/vatsim_data"
    geojson_path = "/app/airspace_sector_data/australian_airspace_sectors.geojson"
    
    rebuilder = SectorOccupancyRebuilder(db_url, geojson_path)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "priority":
            print("Rebuilding priority flights (missing sector data)...")
            await rebuilder.rebuild_priority_flights()
        elif sys.argv[1] == "all":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
            print(f"Rebuilding all flights (limit: {limit})...")
            await rebuilder.rebuild_all_flights(limit)
        else:
            print("Usage:")
            print("  python3 rebuild_sector_occupancy.py priority  # Rebuild flights missing sector data")
            print("  python3 rebuild_sector_occupancy.py all [limit]  # Rebuild all flights")
            sys.exit(1)
    else:
        # Interactive mode
        print("Sector Occupancy Rebuild Tool")
        print("=" * 40)
        print("1. Rebuild priority flights (missing sector data)")
        print("2. Rebuild all flights")
        print("3. Test single flight")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            await rebuilder.rebuild_priority_flights()
        elif choice == "2":
            limit = input("Enter limit (or press Enter for all): ").strip()
            limit = int(limit) if limit else None
            await rebuilder.rebuild_all_flights(limit)
        elif choice == "3":
            callsign = input("Enter callsign: ").strip()
            cid = int(input("Enter CID: ").strip())
            completion_time_str = input("Enter completion time (YYYY-MM-DD HH:MM:SS): ").strip()
            completion_time = datetime.fromisoformat(completion_time_str.replace(' ', 'T'))
            
            print(f"\nTesting flight: {callsign} (CID: {cid})")
            
            # Analyze data coverage
            coverage = await rebuilder.analyze_data_coverage(callsign, cid, completion_time)
            print(f"Data coverage:")
            for source, data in coverage.items():
                print(f"  {source}: {data['record_count']} records from {data['earliest']} to {data['latest']}")
            
            # Rebuild sector occupancy
            test_records = await rebuilder.rebuild_flight_sectors(callsign, cid, completion_time)
            print(f"Generated {len(test_records)} sector occupancy records")
            
            if test_records:
                await rebuilder._insert_rebuilt_records(test_records)
                print("✅ Records inserted into database")
                print("Sample record:")
                print(f"  Entry: {test_records[0]['entry_timestamp']} in {test_records[0]['sector_name']}")
                if test_records[0]['exit_timestamp']:
                    print(f"  Exit: {test_records[0]['exit_timestamp']} (duration: {test_records[0]['duration_seconds']}s)")
        elif choice == "4":
            print("Exiting...")
        else:
            print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())
