#!/usr/bin/env python3
"""Check sector occupancy data for issues."""
from app.database import get_sync_engine
from sqlalchemy import text

def main():
    engine = get_sync_engine()
    with engine.connect() as conn:
        # Query 1: Check for sector flapping
        flap_sql = """
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
            COUNT(*) as total_changes,
            COUNT(*) FILTER (WHERE EXTRACT(EPOCH FROM (next_entry - exit_timestamp)) < 300) as quick_reentries,
            MIN(EXTRACT(EPOCH FROM (next_entry - exit_timestamp))) as min_gap_seconds,
            AVG(EXTRACT(EPOCH FROM (next_entry - exit_timestamp))) as avg_gap_seconds
        FROM sector_changes
        WHERE next_entry IS NOT NULL;
        """
        
        # Query 2: Check for speed-based issues
        speed_sql = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(*) FILTER (WHERE f.groundspeed IS NULL) as null_speed,
            COUNT(*) FILTER (WHERE f.groundspeed BETWEEN 30 AND 60) as boundary_speed,
            COUNT(*) FILTER (WHERE f.groundspeed < 30) as low_speed,
            COUNT(*) FILTER (WHERE f.groundspeed >= 60) as normal_speed
        FROM flight_sector_occupancy fso
        JOIN flights f ON 
            f.callsign = fso.callsign
            AND f.last_updated >= fso.entry_timestamp
            AND f.last_updated <= COALESCE(fso.exit_timestamp, NOW())
        WHERE fso.entry_timestamp > NOW() - INTERVAL '24 hours';
        """
        
        # Query 3: Check for duration issues
        duration_sql = """
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE duration_seconds IS NULL) as null_duration,
            COUNT(*) FILTER (WHERE duration_seconds = 0) as zero_duration,
            COUNT(*) FILTER (WHERE duration_seconds < 0) as negative_duration,
            COUNT(*) FILTER (WHERE duration_seconds BETWEEN 1 AND 60) as under_1min,
            COUNT(*) FILTER (WHERE duration_seconds BETWEEN 61 AND 300) as under_5min,
            COUNT(*) FILTER (WHERE duration_seconds > 300) as over_5min,
            AVG(duration_seconds) FILTER (WHERE duration_seconds > 0) as avg_duration
        FROM flight_sector_occupancy
        WHERE entry_timestamp > NOW() - INTERVAL '24 hours';
        """
        
        print("=== Sector Change Analysis ===")
        result = conn.execute(text(flap_sql))
        row = result.fetchone()
        print(f"Total sector changes: {row.total_changes}")
        print(f"Quick re-entries (<5min): {row.quick_reentries}")
        print(f"Minimum gap between exit/entry: {row.min_gap_seconds:.1f}s")
        print(f"Average gap between exit/entry: {row.avg_gap_seconds:.1f}s")
        
        print("\n=== Speed Analysis ===")
        result = conn.execute(text(speed_sql))
        row = result.fetchone()
        total = row.total_records
        if total > 0:
            print(f"Total records: {total}")
            print(f"Missing speed: {row.null_speed} ({row.null_speed/total*100:.1f}%)")
            print(f"Speed 30-60kts: {row.boundary_speed} ({row.boundary_speed/total*100:.1f}%)")
            print(f"Speed <30kts: {row.low_speed} ({row.low_speed/total*100:.1f}%)")
            print(f"Speed ≥60kts: {row.normal_speed} ({row.normal_speed/total*100:.1f}%)")
        
        print("\n=== Duration Analysis ===")
        result = conn.execute(text(duration_sql))
        row = result.fetchone()
        total = row.total
        if total > 0:
            print(f"Total records: {total}")
            print(f"NULL duration: {row.null_duration} ({row.null_duration/total*100:.1f}%)")
            print(f"Zero duration: {row.zero_duration} ({row.zero_duration/total*100:.1f}%)")
            print(f"Negative duration: {row.negative_duration} ({row.negative_duration/total*100:.1f}%)")
            print(f"Under 1 minute: {row.under_1min} ({row.under_1min/total*100:.1f}%)")
            print(f"1-5 minutes: {row.under_5min} ({row.under_5min/total*100:.1f}%)")
            print(f"Over 5 minutes: {row.over_5min} ({row.over_5min/total*100:.1f}%)")
            print(f"Average duration: {row.avg_duration:.1f}s")

if __name__ == '__main__':
    main()

