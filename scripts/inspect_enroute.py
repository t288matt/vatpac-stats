#!/usr/bin/env python3
"""Inspect total enroute computation for flight_summaries with NULL enroute minutes.

Run inside container with PYTHONPATH=/app: python scripts/inspect_enroute.py
"""
import sys, os
from datetime import datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import asyncio
from sqlalchemy import text
from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService


async def main():
    async with get_database_session() as session:
        q = text("""
            SELECT id, callsign, departure, arrival, logon_time, completion_time
            FROM flight_summaries
            WHERE completion_time >= NOW() - INTERVAL '1 day'
              AND completion_time < NOW()
              AND (airborne_controller_time_percentage IS NULL OR total_enroute_time_minutes IS NULL)
            ORDER BY completion_time DESC
            LIMIT 10
        """)
        res = await session.execute(q)
        rows = res.fetchall()

    svc = ATCDetectionService()

    if not rows:
        print("No rows found")
        return

    for r in rows:
        print("---")
        print(f"id={r.id} callsign={r.callsign} departure={r.departure} arrival={r.arrival}")
        print(f"logon_time={r.logon_time} completion_time={r.completion_time}")
        try:
            minutes = await svc._get_airborne_time_from_flights(r.callsign, r.departure, r.arrival, r.logon_time, r.completion_time)
            print(f"_get_airborne_time_from_flights -> {minutes}")
        except Exception as e:
            print(f"Error computing airborne time: {e}")

        # Also show what detect returns
        try:
            atc = await svc.detect_flight_atc_interactions_with_timeout(r.callsign, r.departure, r.arrival, r.logon_time, timeout_seconds=20.0)
            print(f"detect_flight_atc_interactions -> controllers:{len(atc.get('controller_callsigns',{}))} actp={atc.get('airborne_controller_time_percentage')}")
        except Exception as e:
            print(f"Error running detect: {e}")


if __name__ == '__main__':
    asyncio.run(main())



