#!/usr/bin/env python3
"""Compare primary sector in flight summaries with actual longest duration sector."""
from app.database import _get_engine
from sqlalchemy import text

def main():
    engine = _get_engine()
    with engine.connect() as conn:
        # Get a sample of recent flight summaries and compare their primary sector
        # with the actual longest duration sector from flight_sector_occupancy
        sql = text("""
        WITH longest_sectors AS (
            SELECT 
                fso.callsign,
                fso.sector_name,
                SUM(fso.duration_seconds) as total_duration,
                ROW_NUMBER() OVER (PARTITION BY fso.callsign ORDER BY SUM(fso.duration_seconds) DESC) as rank
            FROM flight_sector_occupancy fso
            JOIN flight_summaries fs ON 
                fs.callsign = fso.callsign
                AND fso.entry_timestamp >= fs.logon_time
                AND fso.exit_timestamp <= fs.completion_time
            WHERE fs.completion_time > NOW() - INTERVAL '24 hours'
            GROUP BY fso.callsign, fso.sector_name
        )
        SELECT 
            fs.callsign,
            fs.primary_enroute_sector as recorded_primary,
            ls.sector_name as actual_longest,
            ls.total_duration as longest_duration
        FROM flight_summaries fs
        LEFT JOIN longest_sectors ls ON 
            ls.callsign = fs.callsign 
            AND ls.rank = 1
        WHERE fs.completion_time > NOW() - INTERVAL '24 hours'
        AND (fs.primary_enroute_sector IS NOT NULL OR ls.sector_name IS NOT NULL)
        LIMIT 20;
        """)
        
        print("=== Sample of Recent Flights ===")
        result = conn.execute(sql)
        rows = result.fetchall()
        for row in rows:
            print(f"\nFlight: {row.callsign}")
            print(f"Recorded Primary: {row.recorded_primary}")
            print(f"Actual Longest: {row.actual_longest} ({row.longest_duration}s)")

if __name__ == '__main__':
    main()