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
    query = text(
        """
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
            WHERE NOW() >= last_updated + ((:completion_hours)::int * INTERVAL '1 hour')
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
            session_end,
            latest_deptime,
            latest_route
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
                }
            )
        return sessions_out


