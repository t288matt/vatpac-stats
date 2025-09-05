#!/usr/bin/env python3
import asyncio
from datetime import datetime, timezone
from sqlalchemy import text

from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService
from app.services.detection_common import compute_prefilter_windows


async def main():
    async with get_database_session() as session:
        q = text("""
            SELECT id,callsign,departure,arrival,logon_time,completion_time
            FROM flight_summaries
            WHERE created_at >= now() - interval '1 day'
              AND callsign NOT LIKE 'DT-%'
              AND callsign NOT LIKE 'STF%'
            ORDER BY created_at DESC
            LIMIT 20
        """)
        res = await session.execute(q)
        rows = res.fetchall()

    if not rows:
        print('No recent real flight summaries found in the last 24h.')
        return

    atc = ATCDetectionService()

    print('Inspecting recent real flight summaries (max 20):')
    for r in rows:
        fid, callsign, dep, arr, logon, completion = r
        # normalize tz
        if logon is None:
            continue
        logon = logon if logon.tzinfo else logon.replace(tzinfo=timezone.utc)
        end = completion if completion is not None else datetime.now(timezone.utc)
        end = end if getattr(end, 'tzinfo', None) else end.replace(tzinfo=timezone.utc)

        async with get_database_session() as session:
            cnt_f = await session.execute(text("""
                SELECT count(*) AS c FROM transceivers
                WHERE entity_type='flight' AND callsign = :c AND "timestamp" BETWEEN :s AND :e
            """), {"c": callsign, "s": logon, "e": end})
            cnt_f = int(cnt_f.fetchone().c)

        pre = compute_prefilter_windows(logon, atc.time_window_seconds)
        async with get_database_session() as session:
            cnt_atc = await session.execute(text("""
                SELECT count(*) AS c FROM transceivers
                WHERE entity_type='atc' AND "timestamp" BETWEEN :s AND :e
            """), {"s": pre['atc_start_time'], "e": pre['atc_end_time']})
            cnt_atc = int(cnt_atc.fetchone().c)

        # run detection (with timeout)
        data = await atc.detect_flight_atc_interactions_with_timeout(callsign, dep or '', arr or '', logon, timeout_seconds=10.0)
        interactions = data.get('interactions_detected', 0)
        controllers = data.get('controller_callsigns') or {}

        print(f"id={fid} callsign={callsign} logon={logon} end={end} flight_tx={cnt_f} atc_window_tx={cnt_atc} interactions={interactions} controllers_found={len(controllers)}")


if __name__ == '__main__':
    asyncio.run(main())


