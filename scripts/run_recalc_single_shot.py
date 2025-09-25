#!/usr/bin/env python3
"""One-off per-summary recalculation for recently-reset flight_summaries.

Usage: run inside container with PYTHONPATH=/app
"""
import asyncio
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sqlalchemy import text
from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService


async def main():
    svc = ATCDetectionService()

    async with get_database_session() as session:
        q = text("""
            SELECT id, callsign, departure, arrival, logon_time, completion_time
            FROM flight_summaries
            WHERE completion_time >= NOW() - INTERVAL '1 day'
              AND completion_time < NOW()
              AND (airborne_controller_time_percentage IS NULL OR total_enroute_time_minutes IS NULL)
            ORDER BY completion_time DESC
        """)
        res = await session.execute(q)
        rows = res.fetchall()

    print(f"Found {len(rows)} summaries to recalc")
    processed = 0

    for r in rows:
        try:
            sid = r.id
            callsign = r.callsign
            departure = r.departure
            arrival = r.arrival
            logon_time = r.logon_time
            completion_time = r.completion_time

            # Re-run ATC detection (with reasonable timeout)
            atc_data = await svc.detect_flight_atc_interactions_with_timeout(
                callsign, departure, arrival, logon_time, timeout_seconds=30.0
            )

            total_enroute = await svc._get_airborne_time_from_flights(
                callsign, departure, arrival, logon_time, completion_time
            )

            async with get_database_session() as session:
                await session.execute(text("""
                    UPDATE flight_summaries
                    SET airborne_controller_time_percentage = :pct,
                        total_enroute_time_minutes = :enroute,
                        updated_at = NOW()
                    WHERE id = :id
                """), {"pct": float(atc_data.get("airborne_controller_time_percentage", 0.0)), "enroute": int(total_enroute), "id": sid})
                await session.commit()

            processed += 1
            print(f"Recalculated id={sid} callsign={callsign}")

        except Exception as e:
            print(f"Failed id={r.id if hasattr(r,'id') else 'unknown'}: {e}")
            continue

    print(f"Processed {processed} summaries")


if __name__ == '__main__':
    asyncio.run(main())



