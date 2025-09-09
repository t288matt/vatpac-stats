#!/usr/bin/env python3
"""Investigate why some flight summaries lack sector_breakdown data."""
from app.database import _get_engine
from sqlalchemy import text

def main():
    engine = _get_engine()
    
    # Check summaries without sector data
    sql1 = """
    SELECT 
        fs.id, fs.callsign, fs.departure, fs.arrival, fs.completion_time,
        fs.time_online_minutes, fs.sector_breakdown,
        COUNT(f.id) as flight_records_count
    FROM flight_summaries fs
    LEFT JOIN flights f ON f.callsign = fs.callsign 
        AND f.cid = fs.cid 
        AND f.departure = fs.departure 
        AND f.arrival = fs.arrival
        AND f.logon_time = fs.logon_time
    WHERE DATE(fs.updated_at) = CURRENT_DATE
        AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
    GROUP BY fs.id, fs.callsign, fs.departure, fs.arrival, fs.completion_time, fs.time_online_minutes, fs.sector_breakdown
    ORDER BY flight_records_count DESC
    LIMIT 10
    """
    
    print("=== Top 10 summaries WITHOUT sector data ===")
    with engine.connect() as conn:
        result = conn.execute(text(sql1))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row[0]}, Callsign: {row[1]}, Route: {row[2]}-{row[3]}, "
                  f"Time online: {row[5]}, Flight records: {row[7]}, Sector breakdown: {row[6]}")
    
    # Check if these flights have any records in flights table
    sql2 = """
    SELECT 
        COUNT(DISTINCT fs.id) as summaries_without_sector_data,
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
    
    print("\n=== Analysis of summaries without sector data ===")
    with engine.connect() as conn:
        result = conn.execute(text(sql2))
        row = result.fetchone()
        print(f"Summaries without sector data: {row[0]}")
        print(f"  - Have flight records: {row[1]}")
        print(f"  - No flight records: {row[2]}")
    
    # Check if flights_archive has data for these
    sql3 = """
    SELECT 
        COUNT(DISTINCT fs.id) as summaries_without_sector_data,
        COUNT(DISTINCT CASE WHEN fa.id IS NOT NULL THEN fs.id END) as with_archive_records
    FROM flight_summaries fs
    LEFT JOIN flights f ON f.callsign = fs.callsign 
        AND f.cid = fs.cid 
        AND f.departure = fs.departure 
        AND f.arrival = fs.arrival
        AND f.logon_time = fs.logon_time
    LEFT JOIN flights_archive fa ON fa.callsign = fs.callsign 
        AND fa.cid = fs.cid 
        AND fa.departure = fs.departure 
        AND fa.arrival = fs.arrival
        AND fa.logon_time = fs.logon_time
    WHERE DATE(fs.updated_at) = CURRENT_DATE
        AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
    """
    
    print("\n=== Archive data availability ===")
    with engine.connect() as conn:
        result = conn.execute(text(sql3))
        row = result.fetchone()
        print(f"Summaries without sector data: {row[0]}")
        print(f"  - Have archive records: {row[1]}")
    
    # Check time_online_minutes distribution for summaries without sector data
    sql4 = """
    SELECT 
        CASE 
            WHEN time_online_minutes IS NULL THEN 'NULL'
            WHEN time_online_minutes = 0 THEN '0 minutes'
            WHEN time_online_minutes < 5 THEN '1-4 minutes'
            WHEN time_online_minutes < 15 THEN '5-14 minutes'
            WHEN time_online_minutes < 30 THEN '15-29 minutes'
            ELSE '30+ minutes'
        END as time_bucket,
        COUNT(*) as count
    FROM flight_summaries
    WHERE DATE(updated_at) = CURRENT_DATE
        AND (sector_breakdown IS NULL OR sector_breakdown = '{}'::jsonb)
    GROUP BY 
        CASE 
            WHEN time_online_minutes IS NULL THEN 'NULL'
            WHEN time_online_minutes = 0 THEN '0 minutes'
            WHEN time_online_minutes < 5 THEN '1-4 minutes'
            WHEN time_online_minutes < 15 THEN '5-14 minutes'
            WHEN time_online_minutes < 30 THEN '15-29 minutes'
            ELSE '30+ minutes'
        END
    ORDER BY 
        CASE 
            WHEN time_online_minutes IS NULL THEN 0
            WHEN time_online_minutes = 0 THEN 1
            WHEN time_online_minutes < 5 THEN 2
            WHEN time_online_minutes < 15 THEN 3
            WHEN time_online_minutes < 30 THEN 4
            ELSE 5
        END
    """
    
    print("\n=== Time online distribution for summaries without sector data ===")
    with engine.connect() as conn:
        result = conn.execute(text(sql4))
        rows = result.fetchall()
        for row in rows:
            print(f"{row[0]}: {row[1]} summaries")

if __name__ == '__main__':
    main()

