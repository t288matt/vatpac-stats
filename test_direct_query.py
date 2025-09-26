#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_database_session
from sqlalchemy import text

async def test_direct_query():
    query = text("""
        WITH base AS (
            SELECT 
                callsign,
                cid,
                departure,
                arrival,
                COALESCE(logon_time, last_updated) AS logon_time,
                last_updated,
                deptime,
                route,
                aircraft_type,
                aircraft_faa,
                aircraft_short,
                flight_rules,
                planned_altitude,
                name,
                server,
                pilot_rating,
                military_rating
            FROM flights_archive
            WHERE callsign = 'JST458' AND logon_time >= '2025-09-08' AND logon_time < '2025-09-09'
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
                aircraft_type,
                aircraft_faa,
                aircraft_short,
                flight_rules,
                planned_altitude,
                name,
                server,
                pilot_rating,
                military_rating,
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
                aircraft_type,
                aircraft_faa,
                aircraft_short,
                flight_rules,
                planned_altitude,
                name,
                server,
                pilot_rating,
                military_rating,
                CASE 
                    WHEN prev_last_updated IS NULL THEN 1
                    WHEN (EXTRACT(EPOCH FROM (logon_time - prev_last_updated)) / 60.0) > 30 THEN 1
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
                aircraft_type,
                aircraft_faa,
                aircraft_short,
                flight_rules,
                planned_altitude,
                name,
                server,
                pilot_rating,
                military_rating,
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
                (ARRAY_REMOVE(ARRAY_AGG(route ORDER BY last_updated DESC), NULL))[1] AS latest_route,
                (ARRAY_REMOVE(ARRAY_AGG(aircraft_type ORDER BY last_updated DESC), NULL))[1] AS latest_aircraft_type,
                (ARRAY_REMOVE(ARRAY_AGG(aircraft_faa ORDER BY last_updated DESC), NULL))[1] AS latest_aircraft_faa,
                (ARRAY_REMOVE(ARRAY_AGG(aircraft_short ORDER BY last_updated DESC), NULL))[1] AS latest_aircraft_short,
                (ARRAY_REMOVE(ARRAY_AGG(flight_rules ORDER BY last_updated DESC), NULL))[1] AS latest_flight_rules,
                (ARRAY_REMOVE(ARRAY_AGG(planned_altitude ORDER BY last_updated DESC), NULL))[1] AS latest_planned_altitude,
                (ARRAY_REMOVE(ARRAY_AGG(name ORDER BY last_updated DESC), NULL))[1] AS latest_name,
                (ARRAY_REMOVE(ARRAY_AGG(server ORDER BY last_updated DESC), NULL))[1] AS latest_server,
                (ARRAY_REMOVE(ARRAY_AGG(pilot_rating ORDER BY last_updated DESC), NULL))[1] AS latest_pilot_rating,
                (ARRAY_REMOVE(ARRAY_AGG(military_rating ORDER BY last_updated DESC), NULL))[1] AS latest_military_rating
            FROM labeled
            GROUP BY callsign, cid, departure, arrival, segment_id
        )
        SELECT 
            callsign,
            cid,
            departure,
            arrival,
            session_start,
            session_end,
            latest_deptime,
            latest_route,
            latest_aircraft_type,
            latest_aircraft_faa,
            latest_aircraft_short,
            latest_flight_rules,
            latest_planned_altitude,
            latest_name,
            latest_server,
            latest_pilot_rating,
            latest_military_rating
        FROM sessions
        WHERE callsign = 'JST458'
        ORDER BY session_end DESC
    """)
    
    async with get_database_session() as session:
        result = await session.execute(query)
        rows = result.fetchall()
        
        print(f"Query returned {len(rows)} rows")
        for i, row in enumerate(rows):
            print(f"Row {i}: {dict(row._mapping)}")

if __name__ == "__main__":
    asyncio.run(test_direct_query())
