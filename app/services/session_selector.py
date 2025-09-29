#!/usr/bin/env python3
"""
Session selector: builds canonical flight sessions by merging segments using an inactivity gap.

Signature/grouping: (callsign, cid, departure, arrival)
Outputs per session: session_start, session_end, latest_deptime, route snapshot
"""

from typing import List, Dict, Any

from sqlalchemy import text

from app.database import get_database_session


async def select_canonical_sessions(
    completion_hours: int,
    gap_minutes: int,
        max_span_hours: int = 24,  # Default to 24 hours, but not enforced (unused)
) -> List[Dict[str, Any]]:
    """Select canonical sessions from flights using an inactivity gap and span cap.

    Args:
        completion_hours: Horizon; only consider rows with last_updated <= now - completion_hours
        gap_minutes: Inactivity gap to split segments (minutes)
        max_span_hours: Maximum allowed session span; segments exceeding cap are split by gaps inherently

    Returns:
        List of session dicts with keys: callsign, cid, departure, arrival, session_start, session_end,
        latest_deptime, latest_route
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 DEBUG: Session selector called with completion_hours={completion_hours}, gap_minutes={gap_minutes}, max_span_hours={max_span_hours}")
    
    query = text(
        """
        WITH processed_flights AS (
            -- First get all the processed flights (any flight summary record exists)
            -- This reduces the number of queries against flight_summaries
            SELECT DISTINCT 
                callsign, 
                cid, 
                departure, 
                arrival
            FROM flight_summaries
            -- No enrichment status filter - canonical only cares if record exists
        ),
        base AS (
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
            FROM flights
            WHERE NOW() >= last_updated + ((:completion_hours)::int * INTERVAL '1 hour')
            -- More efficient anti-join using the processed_flights CTE
            AND NOT EXISTS (
                SELECT 1
                FROM processed_flights pf
                WHERE pf.callsign = flights.callsign
                AND pf.cid = flights.cid
                AND pf.departure = flights.departure
                AND pf.arrival = flights.arrival
            )
            UNION ALL
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
            WHERE NOW() >= last_updated + ((:completion_hours)::int * INTERVAL '1 hour')
            -- More efficient anti-join using the processed_flights CTE
            AND NOT EXISTS (
                SELECT 1
                FROM processed_flights pf
                WHERE pf.callsign = flights_archive.callsign
                AND pf.cid = flights_archive.cid
                AND pf.departure = flights_archive.departure
                AND pf.arrival = flights_archive.arrival
            )
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
                    WHEN (EXTRACT(EPOCH FROM (logon_time - prev_last_updated)) / 60.0) > :gap_minutes THEN 1
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
        -- Removed max_span_hours limit to allow long-haul flights
        ORDER BY session_end DESC
        """
    )

    async with get_database_session() as session:
        result = await session.execute(
            query,
            {
                "completion_hours": int(completion_hours),
                "gap_minutes": int(gap_minutes),
            },
        )
        rows = result.fetchall()
        sessions_out: List[Dict[str, Any]] = []
        for r in rows:
            sessions_out.append(
                {
                    "callsign": r.callsign,
                    "cid": r.cid,
                    "departure": r.departure,
                    "arrival": r.arrival,
                    "session_start": r.session_start,
                    "session_end": r.session_end,
                    "latest_deptime": r.latest_deptime,
                    "latest_route": r.latest_route,
                    "latest_aircraft_type": r.latest_aircraft_type,
                    "latest_aircraft_faa": r.latest_aircraft_faa,
                    "latest_aircraft_short": r.latest_aircraft_short,
                    "latest_flight_rules": r.latest_flight_rules,
                    "latest_planned_altitude": r.latest_planned_altitude,
                    "latest_name": r.latest_name,
                    "latest_server": r.latest_server,
                    "latest_pilot_rating": r.latest_pilot_rating,
                    "latest_military_rating": r.latest_military_rating,
                }
            )
        logger.info(f"🔍 DEBUG: Session selector returning {len(sessions_out)} sessions")
        if len(sessions_out) > 0:
            logger.info(f"🔍 DEBUG: First session example: {sessions_out[0]}")
        return sessions_out


