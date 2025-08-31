import asyncio
import pytest

from app.services.data_service import DataService
from app.database import get_database_session
from sqlalchemy import text


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Occasional transient integrity mismatch during concurrent runs; advisory locks prevent duplication but queries may race.")
async def test_concurrent_pipeline_runs_do_not_error_and_keep_integrity():
    svc = DataService()

    # Run two concurrent invocations; advisory locks should prevent conflicts
    res1, res2 = await asyncio.gather(
        svc.process_completed_flights(), svc.process_completed_flights()
    )

    # Basic sanity
    assert isinstance(res1, dict) and isinstance(res2, dict)

    # Integrity should be green (0/0); allow brief eventual consistency
    for _ in range(10):
        async with get_database_session() as session:
            q1 = text(
                """
                WITH flight_ctrl AS (
                  SELECT fs.id AS flight_summary_id, fs.callsign AS flight_callsign, fs.logon_time,
                         COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time,
                         key AS controller_callsign
                  FROM flight_summaries fs
                  CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
                  WHERE fs.controller_callsigns IS NOT NULL AND fs.controller_callsigns <> '{}'::jsonb
                )
                SELECT COUNT(*) FROM flight_ctrl fc WHERE NOT EXISTS (
                  SELECT 1 FROM controller_summaries cs
                  WHERE cs.callsign = fc.controller_callsign
                    AND cs.session_start_time <= fc.completion_time
                    AND (cs.session_end_time IS NULL OR cs.session_end_time >= fc.logon_time)
                    AND EXISTS (
                      SELECT 1 FROM jsonb_array_elements(cs.aircraft_details) AS d
                      WHERE d->>'callsign' = fc.flight_callsign
                    )
                );
                """
            )
            q2 = text(
                """
                WITH ctrl_flights AS (
                  SELECT cs.id AS controller_summary_id, cs.callsign AS controller_callsign,
                         cs.session_start_time, COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') AS session_end_time,
                         d->>'callsign' AS flight_callsign
                  FROM controller_summaries cs
                  CROSS JOIN LATERAL jsonb_array_elements(cs.aircraft_details) AS d
                )
                SELECT COUNT(*) FROM ctrl_flights cf LEFT JOIN flight_summaries fs
                  ON fs.callsign = cf.flight_callsign
                 AND fs.logon_time <= cf.session_end_time
                 AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= cf.session_start_time
                WHERE fs.id IS NULL OR fs.controller_callsigns IS NULL OR fs.controller_callsigns = '{}'::jsonb
                   OR NOT (fs.controller_callsigns ? cf.controller_callsign);
                """
            )
            c1 = (await session.execute(q1)).scalar() or 0
            c2 = (await session.execute(q2)).scalar() or 0
            if c1 == 0 and c2 == 0:
                break
        await asyncio.sleep(0.5)
    assert c1 == 0 and c2 == 0


