#!/usr/bin/env python3
"""
Accurate rebuild of flight_sector_occupancy that replicates live system logic.

This script replicates the EXACT same entry/exit logic as the live system:
- Entry: Aircraft must have groundspeed >= 60 knots AND be within sector boundary
- Exit: Aircraft must have groundspeed < 30 knots for 2 consecutive polls
- State tracking: Maintains current_sector and exit_counter for each flight
"""

import argparse
from datetime import datetime, timezone
from app.database import get_database_session
from app.utils.sector_loader import SectorLoader
from sqlalchemy import text

async def rebuild_sector_occupancy_accurate(since_date: str, dry_run: bool = True, limit: int = None):
    """
    Rebuild sector occupancy data using EXACT live system logic.

    This replicates the complete _track_sector_occupancy logic:
    - Entry: groundspeed >= 60 knots AND in sector boundary
    - Exit: groundspeed < 30 knots for 2 consecutive polls
    - State management: tracks current_sector and exit_counter per flight

    Args:
        since_date: Start date for rebuild (ISO format)
        dry_run: If True, only analyze without making changes
        limit: Limit number of flights to process (for testing)
    """
    print("  DEBUG: Starting rebuild function")
    since = datetime.fromisoformat(since_date).replace(tzinfo=timezone.utc)
    sector_loader = SectorLoader()
    sector_loader.load_sectors()

    # Load flights since the given date WITH groundspeed data from BOTH tables
    async with get_database_session() as session:
        query = """
        SELECT callsign, latitude, longitude, altitude, groundspeed, last_updated, logon_time
        FROM (
            SELECT callsign, latitude, longitude, altitude, groundspeed, last_updated, logon_time
            FROM flights
            WHERE last_updated >= :since
            UNION ALL
            SELECT callsign, latitude, longitude, altitude, groundspeed, last_updated, logon_time
            FROM flights_archive
            WHERE last_updated >= :since
        ) combined_flights
        ORDER BY callsign, last_updated ASC
        """
        if limit:
            query += " LIMIT :limit"

        params = {"since": since}
        if limit:
            params["limit"] = limit

        result = await session.execute(text(query), params)
        flights = result.fetchall()

    print(f"Found {len(flights)} flight records since {since_date}")

    # First, delete ALL existing sector occupancy records since the given date
    if not dry_run:
        async with get_database_session() as session:
            delete_query = """
            DELETE FROM flight_sector_occupancy
            WHERE entry_timestamp >= :since
            """
            await session.execute(text(delete_query), {"since": since})
            await session.commit()
            print(f"Deleted all existing sector occupancy records since {since_date}")

    if dry_run:
        print("DRY RUN - analyzing data only, no changes will be made")
        print(f"Would process {len(flights)} flight records")

        # Group by callsign for analysis
        callsigns = set(row.callsign for row in flights)
        print(f"Unique callsigns: {len(callsigns)}")

        # Check sample sector assignment
        sample_flight = flights[0] if flights else None
        if sample_flight:
            sector = sector_loader.get_sector_for_point(sample_flight.latitude, sample_flight.longitude)
            print(f"Sample sector check: {sample_flight.callsign} at ({sample_flight.latitude:.3f}, {sample_flight.longitude:.3f}) -> {sector}")
        return

    # Real processing - replicate EXACT live system logic
    processed_flights = 0
    total_entries = 0

    # Group flights by callsign
    flights_by_callsign = {}
    for flight in flights:
        if flight.callsign not in flights_by_callsign:
            flights_by_callsign[flight.callsign] = []
        flights_by_callsign[flight.callsign].append(flight)

    async with get_database_session() as session:
        for callsign, flight_records in flights_by_callsign.items():
            print(f"Processing {callsign} ({len(flight_records)} records)")
            print("  DEBUG: ABOUT TO START PROCESSING RECORDS")

            # Replicate EXACT live system _track_sector_occupancy logic
            # State tracking like live system
            flight_sector_states = {}  # Track current_sector and exit_counter per flight
            entries = []

            # Sort flight records by timestamp to process chronologically
            sorted_records = sorted(flight_records, key=lambda x: x.last_updated)

            print(f"  DEBUG: Processing {len(sorted_records)} records for {callsign}")
            print("  DEBUG: Starting to process records...")
            for record in sorted_records:
                print(f"  DEBUG: Processing record at {record.last_updated}, speed={record.groundspeed}")
                lat = record.latitude
                lon = record.longitude
                alt = record.altitude
                groundspeed = record.groundspeed
                ts = record.last_updated

                if lat is None or lon is None or ts is None:
                    continue

                # Get current geographic sector (same as live system)
                geographic_sector = sector_loader.get_sector_for_point(lat, lon)

                # Get previous state
                previous_state = flight_sector_states.get(callsign, {})
                previous_sector = previous_state.get("current_sector")
                exit_counter = previous_state.get("exit_counter", 0)

                # Determine current sector based on speed criteria (EXACT live system logic)
                current_sector = None

                # Entry logic: Must be above 60 knots to enter sector
                if groundspeed is not None and groundspeed >= 60:
                    current_sector = geographic_sector
                    print(f"  DEBUG: {callsign} at {ts} - Speed {groundspeed} >= 60, entering {geographic_sector}")
                elif groundspeed is None:
                    # Missing speed data - defer entry decision
                    current_sector = previous_sector  # Keep previous state
                    print(f"  DEBUG: {callsign} at {ts} - Speed None, keeping previous sector {previous_sector}")
                else:
                    # Speed below 60 knots - not in sector
                    current_sector = None
                    print(f"  DEBUG: {callsign} at {ts} - Speed {groundspeed} < 60, not in sector")

                # Exit logic: Track consecutive below-30kts polls
                if groundspeed is not None and groundspeed < 30:
                    exit_counter += 1
                else:
                    # Speed above 30 knots or missing - reset exit counter
                    exit_counter = 0

                # Check if we should exit due to 2 consecutive below-30kts polls
                should_exit = exit_counter >= 2

                # Handle sector transitions (EXACT live system logic)
                print(f"  DEBUG: {callsign} at {ts} - current_sector={current_sector}, previous_sector={previous_sector}, should_exit={should_exit}")
                if current_sector != previous_sector or should_exit:
                    print(f"  DEBUG: {callsign} at {ts} - TRANSITION: {previous_sector} -> {current_sector}")
                    # Close ALL open sectors for this flight before entering a new one
                    await session.execute(text("""
                        UPDATE flight_sector_occupancy
                        SET exit_timestamp = :exit_ts,
                            exit_lat = :exit_lat,
                            exit_lon = :exit_lon,
                            exit_altitude = :exit_alt,
                            duration_seconds = CASE
                                WHEN entry_timestamp IS NOT NULL
                                THEN EXTRACT(EPOCH FROM (:exit_ts - entry_timestamp))
                                ELSE 0
                            END
                        WHERE callsign = :callsign
                        AND exit_timestamp IS NULL
                    """), {
                        "callsign": callsign,
                        "exit_ts": ts,
                        "exit_lat": lat,
                        "exit_lon": lon,
                        "exit_alt": alt
                    })

                    # Enter new sector (only if different from previous)
                    if current_sector and current_sector != previous_sector:
                        await session.execute(text("""
                            INSERT INTO flight_sector_occupancy (
                                callsign, sector_name, entry_timestamp, exit_timestamp,
                                duration_seconds, entry_lat, entry_lon, exit_lat, exit_lon,
                                entry_altitude, exit_altitude
                            ) VALUES (
                                :callsign, :sector_name, :entry_ts, NULL, 0,
                                :entry_lat, :entry_lon, NULL, NULL, :entry_alt, NULL
                            )
                        """), {
                            "callsign": callsign,
                            "sector_name": current_sector,
                            "entry_ts": ts,
                            "entry_lat": lat,
                            "entry_lon": lon,
                            "entry_alt": alt
                        })

                # Update state
                flight_sector_states[callsign] = {
                    "current_sector": current_sector,
                    "exit_counter": exit_counter,
                    "last_speed": groundspeed
                }

            # Final cleanup: Close any remaining open sectors using last timestamp
            if flight_sector_states.get(callsign, {}).get("current_sector"):
                last_record = sorted_records[-1] if sorted_records else None
                if last_record:
                    await session.execute(text("""
                        UPDATE flight_sector_occupancy
                        SET exit_timestamp = :exit_ts,
                            exit_lat = :exit_lat,
                            exit_lon = :exit_lon,
                            exit_altitude = :exit_alt,
                            duration_seconds = CASE
                                WHEN entry_timestamp IS NOT NULL
                                THEN EXTRACT(EPOCH FROM (:exit_ts - entry_timestamp))
                                ELSE 0
                            END
                        WHERE callsign = :callsign
                        AND exit_timestamp IS NULL
                    """), {
                        "callsign": callsign,
                        "exit_ts": last_record.last_updated,
                        "exit_lat": last_record.latitude,
                        "exit_lon": last_record.longitude,
                        "exit_alt": last_record.altitude
                    })

            # Count entries created for this flight
            result = await session.execute(text("""
                SELECT COUNT(*) FROM flight_sector_occupancy
                WHERE callsign = :callsign
                AND entry_timestamp >= :since
            """), {"callsign": callsign, "since": since})
            entry_count = result.scalar()

            total_entries += entry_count
            processed_flights += 1

            print(f"  -> Inserted {entry_count} sector entries")

    print(f"\nCompleted: {processed_flights} flights processed, {total_entries} sector entries created")

if __name__ == '__main__':
    print("  DEBUG: Script started, parsing arguments")
    parser = argparse.ArgumentParser()
    parser.add_argument('--since', default='2025-09-20T00:00:00+00:00', help='Start date (ISO format)')
    parser.add_argument('--limit', type=int, default=None, help='Limit flights to process (for testing)')
    parser.add_argument('--dry-run', action='store_true', help='Analyze only, no changes')
    args = parser.parse_args()
    print(f"  DEBUG: Arguments parsed - since={args.since}, dry_run={args.dry_run}, limit={args.limit}")

    import asyncio
    asyncio.run(rebuild_sector_occupancy_accurate(args.since, args.dry_run, args.limit))
