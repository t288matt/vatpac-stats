#!/usr/bin/env python3
"""Simple analysis of missing sector data."""
from app.database import _get_engine
from sqlalchemy import text

def main():
    engine = _get_engine()
    
    # Simple count of summaries without sector data
    sql = """
    SELECT 
        COUNT(*) as total_without_sector,
        COUNT(CASE WHEN time_online_minutes IS NULL THEN 1 END) as null_time_online,
        COUNT(CASE WHEN time_online_minutes = 0 THEN 1 END) as zero_time_online,
        COUNT(CASE WHEN time_online_minutes > 0 AND time_online_minutes < 5 THEN 1 END) as very_short,
        COUNT(CASE WHEN time_online_minutes >= 5 AND time_online_minutes < 15 THEN 1 END) as short,
        COUNT(CASE WHEN time_online_minutes >= 15 THEN 1 END) as normal_length
    FROM flight_summaries
    WHERE DATE(updated_at) = CURRENT_DATE
        AND (sector_breakdown IS NULL OR sector_breakdown = '{}'::jsonb)
    """
    
    print("=== Analysis of 78 summaries without sector_breakdown data ===")
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        row = result.fetchone()
        print(f"Total without sector data: {row[0]}")
        print(f"  - NULL time_online_minutes: {row[1]}")
        print(f"  - 0 minutes online: {row[2]}")
        print(f"  - 1-4 minutes online: {row[3]}")
        print(f"  - 5-14 minutes online: {row[4]}")
        print(f"  - 15+ minutes online: {row[5]}")
    
    # Check if these have flight records
    sql2 = """
    SELECT 
        COUNT(DISTINCT fs.id) as summaries_without_sector,
        COUNT(DISTINCT CASE WHEN f.id IS NOT NULL THEN fs.id END) as with_flight_records,
        COUNT(DISTINCT CASE WHEN f.id IS NULL THEN fs.id END) as without_flight_records
    FROM flight_summaries fs
    LEFT JOIN flights f ON f.callsign = fs.callsign 
        AND f.cid = fs.cid 
        AND f.departure = fs.departure 
        AND f.arrival = fs.arrival
        AND f.logon_time = fs.logon_time
    WHERE DATE(fs.updated_at) = CURRENT_DATE
        AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
    """
    
    print("\n=== Flight record availability ===")
    with engine.connect() as conn:
        result = conn.execute(text(sql2))
        row = result.fetchone()
        print(f"Summaries without sector data: {row[0]}")
        print(f"  - Have flight records: {row[1]}")
        print(f"  - No flight records: {row[2]}")
    
    # Check a few examples of summaries with flight records but no sector data
    sql3 = """
    SELECT 
        fs.id, fs.callsign, fs.departure, fs.arrival, 
        fs.time_online_minutes, fs.sector_breakdown,
        COUNT(f.id) as flight_count,
        MIN(f.timestamp) as first_record,
        MAX(f.timestamp) as last_record
    FROM flight_summaries fs
    LEFT JOIN flights f ON f.callsign = fs.callsign 
        AND f.cid = fs.cid 
        AND f.departure = fs.departure 
        AND f.arrival = fs.arrival
        AND f.logon_time = fs.logon_time
    WHERE DATE(fs.updated_at) = CURRENT_DATE
        AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
        AND f.id IS NOT NULL
    GROUP BY fs.id, fs.callsign, fs.departure, fs.arrival, fs.time_online_minutes, fs.sector_breakdown
    ORDER BY flight_count DESC
    LIMIT 5
    """
    
    print("\n=== Examples with flight records but no sector data ===")
    with engine.connect() as conn:
        result = conn.execute(text(sql3))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row[0]}, {row[1]} {row[2]}-{row[3]}, "
                  f"Time: {row[4]}min, Records: {row[6]}, "
                  f"First: {row[7]}, Last: {row[8]}")

if __name__ == '__main__':
    main()


