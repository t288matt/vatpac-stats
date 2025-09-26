#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append('/app')

from app.database import get_database_session
from sqlalchemy import text

async def get_next_50_sessions():
    async with get_database_session() as session:
        query = """
    WITH base AS (
        SELECT 
            callsign,
            cid,
            departure,
            arrival,
            COALESCE(logon_time, last_updated) AS logon_time,
            last_updated,
            deptime,
            route
        FROM flights
        WHERE NOW() >= last_updated + (8 * INTERVAL '1 hour')
        UNION ALL
        SELECT 
            callsign,
            cid,
            departure,
            arrival,
            COALESCE(logon_time, last_updated) AS logon_time,
            last_updated,
            deptime,
            route
        FROM flights_archive
        WHERE NOW() >= last_updated + (8 * INTERVAL '1 hour')
    ), ordered AS (
        SELECT 
            callsign,
            cid,
            departure,
            arrival,
            logon_time,
            last_updated,
            deptime,
            route,
            LAG(last_updated) OVER (
                PARTITION BY callsign, cid, departure, arrival
                ORDER BY GREATEST(logon_time, last_updated), last_updated
            ) AS prev_last_updated
        FROM base
    ), segmented AS (
        SELECT 
            callsign,
            cid,
            departure,
            arrival,
            logon_time,
            last_updated,
            deptime,
            route,
            CASE 
                WHEN prev_last_updated IS NULL THEN 1
                WHEN (EXTRACT(EPOCH FROM (logon_time - prev_last_updated)) / 60.0) > 120 THEN 1
                ELSE 0
            END AS is_new_seg
        FROM ordered
    ), labeled AS (
        SELECT 
            callsign,
            cid,
            departure,
            arrival,
            logon_time,
            last_updated,
            deptime,
            route,
            SUM(is_new_seg) OVER (
                PARTITION BY callsign, cid, departure, arrival
                ORDER BY GREATEST(logon_time, last_updated), last_updated
                ROWS UNBOUNDED PRECEDING
            ) AS segment_id
        FROM segmented
    ), sessions AS (
        SELECT 
            callsign,
            cid,
            departure,
            arrival,
            MIN(logon_time) AS session_start,
            MAX(last_updated) AS session_end,
            MAX(deptime) FILTER (WHERE deptime IS NOT NULL) AS latest_deptime,
            (ARRAY_REMOVE(ARRAY_AGG(route ORDER BY last_updated DESC), NULL))[1] AS latest_route
        FROM labeled
        GROUP BY callsign, cid, departure, arrival, segment_id
    )
    SELECT 
        callsign,
        cid,
        departure,
        arrival,
        session_start,
        session_end
    FROM sessions
    ORDER BY session_end DESC
    LIMIT 50
        """
        
        result = await session.execute(text(query))
        rows = result.fetchall()
        
        # Write to file
        with open('next_50_sessions.txt', 'w') as f:
            f.write("callsign,cid,departure,arrival,session_start,session_end\n")
            for row in rows:
                f.write(f"{row.callsign},{row.cid},{row.departure},{row.arrival},{row.session_start},{row.session_end}\n")
        
        print(f"Found {len(rows)} sessions")
        for i, row in enumerate(rows[:10]):  # Show first 10
            print(f"{i+1}. {row.callsign} {row.departure}->{row.arrival} (cid={row.cid}) - {row.session_end}")

if __name__ == "__main__":
    asyncio.run(get_next_50_sessions())
