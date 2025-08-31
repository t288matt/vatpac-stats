#!/usr/bin/env python3
import asyncio
import sys
from sqlalchemy import text
from app.database import get_database_session

async def main():
    async with get_database_session() as session:
        q1 = text("""
        WITH flight_ctrl AS (
          SELECT fs.id AS flight_summary_id,
                 fs.callsign AS flight_callsign,
                 fs.logon_time,
                 COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time,
                 key AS controller_callsign
          FROM flight_summaries fs
          CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
          WHERE fs.controller_callsigns IS NOT NULL
            AND fs.controller_callsigns <> '{}'::jsonb
        )
        SELECT COUNT(*) AS c FROM flight_ctrl fc WHERE NOT EXISTS (
          SELECT 1 FROM controller_summaries cs
          WHERE cs.callsign = fc.controller_callsign
            AND cs.session_start_time <= fc.completion_time
            AND (cs.session_end_time IS NULL OR cs.session_end_time >= fc.logon_time)
            AND EXISTS (
              SELECT 1 FROM jsonb_array_elements(cs.aircraft_details) AS d
              WHERE d->>'callsign' = fc.flight_callsign
            )
        );
        """)
        q2 = text("""
        WITH ctrl_flights AS (
          SELECT cs.id AS controller_summary_id,
                 cs.callsign AS controller_callsign,
                 cs.session_start_time,
                 COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') AS session_end_time,
                 d->>'callsign' AS flight_callsign
          FROM controller_summaries cs
          CROSS JOIN LATERAL jsonb_array_elements(cs.aircraft_details) AS d
        )
        SELECT COUNT(*) AS c FROM ctrl_flights cf LEFT JOIN flight_summaries fs
          ON fs.callsign = cf.flight_callsign
         AND fs.logon_time <= cf.session_end_time
         AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= cf.session_start_time
        WHERE fs.id IS NULL
           OR fs.controller_callsigns IS NULL
           OR fs.controller_callsigns = '{}'::jsonb
           OR NOT (fs.controller_callsigns ? cf.controller_callsign);
        """)
        r1 = await session.execute(q1)
        r2 = await session.execute(q2)
        c1 = r1.scalar() or 0
        c2 = r2.scalar() or 0
        result = {"flight_to_controller_mismatches": c1, "controller_to_flight_mismatches": c2}
        print(result)
        if c1 > 0 or c2 > 0:
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())


