#!/usr/bin/env python3
"""
Test script for Australian pilot new pilot alert query
"""

import asyncio
import os
from sqlalchemy import text
from app.database import get_database_session

async def test_australian_pilots_query():
    """Test the Australian pilot filtering query"""
    
    # Query to find new Australian pilots
    query = text("""
    -- Find new Australian pilots (currently online but no enroute experience)
    WITH current_australian_pilots AS (
      SELECT DISTINCT cid, name, callsign, server, pilot_rating, logon_time
      FROM flights 
      WHERE cid IS NOT NULL
        AND logon_time >= NOW() - INTERVAL '60 minutes'  -- Recently logged on
        AND LENGTH(name) >= 4  -- Ensure name is long enough
        AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'  -- 4th char from end is 'Y'
    ),
    pilot_experience AS (
      SELECT 
        cid,
        COUNT(*) as total_completed_flights,
        COUNT(CASE WHEN total_enroute_time_minutes > 0 THEN 1 END) as flights_with_enroute_time,
        MAX(completion_time) as last_flight_date,
        SUM(total_enroute_time_minutes) as total_enroute_minutes_ever
      FROM flight_summaries
      WHERE LENGTH(name) >= 4
        AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'  -- Also filter flight_summaries for Australian pilots
      GROUP BY cid
    )
    SELECT 
      cap.cid,
      cap.name,
      cap.callsign,
      cap.server,
      cap.pilot_rating,
      cap.logon_time,
      COALESCE(pe.total_completed_flights, 0) as total_completed_flights,
      COALESCE(pe.flights_with_enroute_time, 0) as flights_with_enroute_time,
      pe.last_flight_date,
      COALESCE(pe.total_enroute_minutes_ever, 0) as total_enroute_minutes_ever,
      (COALESCE(pe.flights_with_enroute_time, 0) = 0) as is_new_pilot
    FROM current_australian_pilots cap
    LEFT JOIN pilot_experience pe ON pe.cid = cap.cid
    WHERE COALESCE(pe.flights_with_enroute_time, 0) = 0  -- No enroute experience
    ORDER BY cap.logon_time DESC
    LIMIT 10;
    """)
    
    try:
        async with get_database_session() as session:
            result = await session.execute(query)
            rows = result.fetchall()
            
            print(f"Found {len(rows)} new Australian pilots:")
            print("=" * 80)
            
            for row in rows:
                print(f"CID: {row.cid}")
                print(f"Name: {row.name}")
                print(f"Callsign: {row.callsign}")
                print(f"Server: {row.server}")
                print(f"Pilot Rating: {row.pilot_rating}")
                print(f"Logon Time: {row.logon_time}")
                print(f"Total Completed Flights: {row.total_completed_flights}")
                print(f"Flights with Enroute Time: {row.flights_with_enroute_time}")
                print(f"Total Enroute Minutes Ever: {row.total_enroute_minutes_ever}")
                print(f"Is New Pilot: {row.is_new_pilot}")
                print("-" * 40)
                
    except Exception as e:
        print(f"Error running query: {e}")

async def test_australian_pilot_patterns():
    """Test different Australian pilot name patterns"""
    
    query = text("""
    SELECT DISTINCT name, cid, callsign
    FROM flights 
    WHERE cid IS NOT NULL
      AND name IS NOT NULL
      AND (
        LENGTH(name) >= 4 AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'
        OR name ~ '\\.Y$'
      )
    ORDER BY name
    LIMIT 20;
    """)
    
    try:
        async with get_database_session() as session:
            result = await session.execute(query)
            rows = result.fetchall()
            
            print(f"\nFound {len(rows)} Australian pilot name patterns:")
            print("=" * 60)
            
            for row in rows:
                print(f"Name: {row.name} | CID: {row.cid} | Callsign: {row.callsign}")
                
    except Exception as e:
        print(f"Error running pattern test: {e}")

if __name__ == "__main__":
    print("Testing Australian Pilot Query...")
    asyncio.run(test_australian_pilots_query())
    asyncio.run(test_australian_pilot_patterns())








