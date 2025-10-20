#!/usr/bin/env python3
"""Analyze primary sector data vs actual sector occupancy."""
from app.database import get_sync_engine
from sqlalchemy import text

def main():
    engine = get_sync_engine()
    
    # Query 1: Compare primary sector with actual longest duration sector
    sql1 = """
    WITH sector_stats AS (
        SELECT 
            fs.callsign,
            fs.primary_enroute_sector,
            fso.sector_name,
            SUM(fso.duration_seconds) as total_duration,
            ROW_NUMBER() OVER (PARTITION BY fs.callsign ORDER BY SUM(fso.duration_seconds) DESC) as rank
        FROM flight_summaries fs
        JOIN flight_sector_occupancy fso ON 
            fs.callsign = fso.callsign 
            AND fso.entry_timestamp >= fs.logon_time 
            AND (fso.exit_timestamp <= fs.completion_time OR fs.completion_time IS NULL)
        WHERE fs.completion_time > NOW() - INTERVAL '24 hours'
        GROUP BY fs.callsign, fs.primary_enroute_sector, fso.sector_name
    )
    SELECT 
        callsign,
        primary_enroute_sector as recorded_primary,
        sector_name as actual_longest,
        total_duration as longest_duration
    FROM sector_stats 
    WHERE rank = 1
    LIMIT 20;
    """
    
    # Query 2: Get statistics on mismatches
    sql2 = """
    WITH sector_stats AS (
        SELECT 
            fs.callsign,
            fs.primary_enroute_sector,
            fso.sector_name,
            SUM(fso.duration_seconds) as total_duration,
            ROW_NUMBER() OVER (PARTITION BY fs.callsign ORDER BY SUM(fso.duration_seconds) DESC) as rank
        FROM flight_summaries fs
        JOIN flight_sector_occupancy fso ON 
            fs.callsign = fso.callsign 
            AND fso.entry_timestamp >= fs.logon_time 
            AND (fso.exit_timestamp <= fs.completion_time OR fs.completion_time IS NULL)
        WHERE fs.completion_time > NOW() - INTERVAL '24 hours'
        GROUP BY fs.callsign, fs.primary_enroute_sector, fso.sector_name
    )
    SELECT 
        COUNT(*) as total_flights,
        COUNT(CASE WHEN primary_enroute_sector = sector_name THEN 1 END) as matching,
        COUNT(CASE WHEN primary_enroute_sector != sector_name THEN 1 END) as mismatching,
        COUNT(CASE WHEN primary_enroute_sector IS NULL THEN 1 END) as null_primary
    FROM sector_stats 
    WHERE rank = 1;
    """
    
    with engine.connect() as conn:
        print("=== Sample of Recent Flights ===")
        result = conn.execute(text(sql1))
        rows = result.fetchall()
        for row in rows:
            print(f"Flight: {row.callsign}")
            print(f"  Recorded Primary: {row.recorded_primary}")
            print(f"  Actual Longest: {row.actual_longest} ({row.longest_duration}s)")
            print()
        
        print("\n=== Mismatch Statistics ===")
        result = conn.execute(text(sql2))
        row = result.fetchone()
        print(f"Total flights analyzed: {row.total_flights}")
        print(f"Matching primary sector: {row.matching}")
        print(f"Mismatching primary sector: {row.mismatching}")
        print(f"Null primary sector: {row.null_primary}")
        if row.total_flights > 0:
            match_pct = (row.matching / row.total_flights) * 100
            print(f"\nAccuracy: {match_pct:.1f}%")

if __name__ == '__main__':
    main()

