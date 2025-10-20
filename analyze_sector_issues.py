#!/usr/bin/env python3
"""Analyze sector occupancy issues by looking at actual data."""
from app.database import get_sync_engine
from sqlalchemy import text

def main():
    engine = get_sync_engine()
    with engine.connect() as conn:
        # Query 1: Look for sector flapping (multiple entries/exits in short time)
        flapping_sql = """
        WITH sector_changes AS (
            SELECT 
                callsign,
                sector_name,
                entry_timestamp,
                exit_timestamp,
                LEAD(entry_timestamp) OVER (
                    PARTITION BY callsign, sector_name 
                    ORDER BY entry_timestamp
                ) as next_entry,
                duration_seconds
            FROM flight_sector_occupancy
            WHERE exit_timestamp IS NOT NULL
            AND entry_timestamp > NOW() - INTERVAL '24 hours'
        )
        SELECT 
            callsign,
            sector_name,
            entry_timestamp,
            exit_timestamp,
            next_entry,
            duration_seconds,
            EXTRACT(EPOCH FROM (next_entry - exit_timestamp)) as gap_seconds
        FROM sector_changes
        WHERE next_entry IS NOT NULL
        AND EXTRACT(EPOCH FROM (next_entry - exit_timestamp)) < 300  -- Less than 5 minutes gap
        ORDER BY gap_seconds ASC
        LIMIT 10;
        """
        
        # Query 2: Look for missing speed data impact
        speed_sql = """
        SELECT 
            f.callsign,
            f.groundspeed,
            f.last_updated,
            fso.sector_name,
            fso.entry_timestamp,
            fso.exit_timestamp,
            fso.duration_seconds
        FROM flights f
        JOIN flight_sector_occupancy fso ON 
            f.callsign = fso.callsign
            AND f.last_updated >= fso.entry_timestamp
            AND f.last_updated <= COALESCE(fso.exit_timestamp, NOW())
        WHERE f.groundspeed IS NULL
        AND f.last_updated > NOW() - INTERVAL '24 hours'
        ORDER BY f.last_updated DESC
        LIMIT 10;
        """
        
        # Query 3: Look for boundary cases (30-60 knots)
        boundary_sql = """
        SELECT 
            f.callsign,
            f.groundspeed,
            f.last_updated,
            fso.sector_name,
            fso.entry_timestamp,
            fso.exit_timestamp,
            fso.duration_seconds
        FROM flights f
        JOIN flight_sector_occupancy fso ON 
            f.callsign = fso.callsign
            AND f.last_updated >= fso.entry_timestamp
            AND f.last_updated <= COALESCE(fso.exit_timestamp, NOW())
        WHERE f.groundspeed BETWEEN 30 AND 60
        AND f.last_updated > NOW() - INTERVAL '24 hours'
        ORDER BY f.last_updated DESC
        LIMIT 10;
        """
        
        print("=== Sector Flapping Analysis ===")
        result = conn.execute(text(flapping_sql))
        rows = result.fetchall()
        for row in rows:
            print(f"\nFlight: {row.callsign}")
            print(f"Sector: {row.sector_name}")
            print(f"First Entry: {row.entry_timestamp}")
            print(f"Exit: {row.exit_timestamp}")
            print(f"Next Entry: {row.next_entry}")
            print(f"Duration: {row.duration_seconds}s")
            print(f"Gap between exit/entry: {row.gap_seconds}s")
        
        print("\n=== Missing Speed Data Analysis ===")
        result = conn.execute(text(speed_sql))
        rows = result.fetchall()
        for row in rows:
            print(f"\nFlight: {row.callsign}")
            print(f"Time: {row.last_updated}")
            print(f"Sector: {row.sector_name}")
            print(f"Entry: {row.entry_timestamp}")
            print(f"Exit: {row.exit_timestamp}")
            print(f"Duration: {row.duration_seconds}s")
        
        print("\n=== Speed Boundary Cases (30-60 knots) ===")
        result = conn.execute(text(boundary_sql))
        rows = result.fetchall()
        for row in rows:
            print(f"\nFlight: {row.callsign}")
            print(f"Speed: {row.groundspeed}")
            print(f"Time: {row.last_updated}")
            print(f"Sector: {row.sector_name}")
            print(f"Entry: {row.entry_timestamp}")
            print(f"Exit: {row.exit_timestamp}")
            print(f"Duration: {row.duration_seconds}s")

if __name__ == '__main__':
    main()

