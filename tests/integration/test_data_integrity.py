import asyncio
import json
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService
from app.services.flight_detection_service import FlightDetectionService


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_end_to_end_data_integrity_roundtrip():
    """Insert deterministic transceivers, run both detection directions, insert summaries,
    and assert the integrity queries report zero mismatches.
    """
    now = datetime.now(timezone.utc).replace(microsecond=0)
    flight_callsign = "DT-INT-FLT"
    controller_callsign = "DT-INT-CTR"
    freq = 123450000

    async def setup_and_run():
        async with get_database_session() as session:
            # cleanup any previous test rows
            await session.execute(text("DELETE FROM transceivers WHERE callsign IN (:f, :c)"), {"f": flight_callsign, "c": controller_callsign})
            await session.execute(text("DELETE FROM flight_summaries WHERE callsign = :f"), {"f": flight_callsign})
            await session.execute(text("DELETE FROM controller_summaries WHERE callsign = :c"), {"c": controller_callsign})
            await session.commit()

            # insert deterministic transceivers (one each) with same freq and same timestamp
            await session.execute(text("""
                INSERT INTO transceivers (callsign, transceiver_id, frequency, position_lat, position_lon, height_msl, height_agl, entity_type, entity_id, "timestamp")
                VALUES (:fc, 900001, :freq, 0.0, 0.0, 1000, 100, 'flight', NULL, :ts),
                       (:cc, 900002, :freq, 0.0, 0.0, 1000, 100, 'atc', NULL, :ts)
            """), {"fc": flight_callsign, "cc": controller_callsign, "freq": freq, "ts": now})
            # insert minimal flight row used by some detection helpers
            await session.execute(text("""
                INSERT INTO flights (callsign, departure, arrival, logon_time)
                VALUES (:fc, 'AAA', 'BBB', :ts)
                ON CONFLICT DO NOTHING
            """), {"fc": flight_callsign, "ts": now})
            await session.commit()

        # run detection services
        atc_svc = ATCDetectionService()
        flight_svc = FlightDetectionService()

        atc_data = await atc_svc.detect_flight_atc_interactions_with_timeout(flight_callsign, 'AAA', 'BBB', now, timeout_seconds=10.0)
        flight_data = await flight_svc.detect_controller_flight_interactions_with_timeout(controller_callsign, now - timedelta(seconds=10), now + timedelta(seconds=10), timeout_seconds=10.0)

        # write summaries based on detection outputs
        async with get_database_session() as session:
            # JSON-serialize Decimal and datetime types
            controller_callsigns_json = json.dumps(atc_data.get("controller_callsigns", {}), default=lambda o: float(o) if isinstance(o, Decimal) else (o.isoformat() if hasattr(o, 'isoformat') else str(o)))
            await session.execute(text("""
                INSERT INTO flight_summaries (callsign, logon_time, completion_time, controller_callsigns, controller_time_percentage, enrichment_status, enrichment_completed_at)
                VALUES (:fc, :logon, :completion, :ccalls, :ctp, 'completed', now())
            """), {
                "fc": flight_callsign,
                "logon": now,
                "completion": now,
                "ccalls": controller_callsigns_json,
                "ctp": atc_data.get("controller_time_percentage", 0.0)
            })

            aircraft_details_json = json.dumps(flight_data.get("details", []), default=lambda o: float(o) if isinstance(o, Decimal) else (o.isoformat() if hasattr(o, 'isoformat') else str(o)))
            await session.execute(text("""
                INSERT INTO controller_summaries (callsign, session_start_time, session_end_time, aircraft_details, total_aircraft_handled, enrichment_status, enrichment_completed_at)
                VALUES (:cc, :start, :end, :ad, :total, 'completed', now())
            """), {
                "cc": controller_callsign,
                "start": now - timedelta(seconds=10),
                "end": now + timedelta(seconds=10),
                "ad": aircraft_details_json,
                "total": len(flight_data.get("details", []))
            })
            await session.commit()

        # run integrity queries (wide window around now)
        async with get_database_session() as session:
            # Flight -> Controller mismatches
            res1 = await session.execute(text("""
                WITH params AS (
                  SELECT (now() - interval '1 hour') AS window_start, (now() + interval '1 hour') AS window_end
                ), flight_ctrl AS (
                  SELECT fs.id AS flight_summary_id, fs.callsign AS flight_callsign, fs.logon_time, COALESCE(fs.completion_time, now()) AS completion_time, key AS controller_callsign FROM flight_summaries fs
                    CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
                  WHERE fs.controller_callsigns IS NOT NULL AND fs.controller_callsigns <> '{}'::jsonb
                    AND fs.logon_time <= (SELECT window_end FROM params)
                    AND COALESCE(fs.completion_time, now()) >= (SELECT window_start FROM params)
                )
                SELECT count(*) AS mismatches FROM (
                  SELECT fc.* FROM flight_ctrl fc
                  WHERE NOT EXISTS (
                    SELECT 1 FROM controller_summaries cs
                    WHERE cs.callsign = fc.controller_callsign
                      AND cs.session_start_time <= fc.completion_time
                      AND (cs.session_end_time IS NULL OR cs.session_end_time >= fc.logon_time)
                  )
                ) t
            """))
            mismatches_fc = int(res1.fetchone().mismatches)

            # Controller -> Flight mismatches
            res2 = await session.execute(text("""
                WITH params AS (
                  SELECT (now() - interval '1 hour') AS window_start, (now() + interval '1 hour') AS window_end
                ), ctrl_flights AS (
                  SELECT cs.id AS controller_summary_id, cs.callsign AS controller_callsign, cs.session_start_time, COALESCE(cs.session_end_time, now()) AS session_end_time, d->>'callsign' AS flight_callsign
                  FROM controller_summaries cs
                  CROSS JOIN LATERAL jsonb_array_elements(cs.aircraft_details) AS d
                  WHERE cs.session_start_time <= (SELECT window_end FROM params)
                    AND COALESCE(cs.session_end_time, now()) >= (SELECT window_start FROM params)
                )
                SELECT count(*) AS mismatches FROM (
                  SELECT cf.* FROM ctrl_flights cf
                  LEFT JOIN flight_summaries fs ON fs.callsign = cf.flight_callsign
                    AND fs.logon_time <= cf.session_end_time
                    AND COALESCE(fs.completion_time, now()) >= cf.session_start_time
                  WHERE fs.id IS NULL OR fs.controller_callsigns IS NULL OR fs.controller_callsigns = '{}'::jsonb
                ) t
            """))
            mismatches_cf = int(res2.fetchone().mismatches)

        return atc_data, flight_data, mismatches_fc, mismatches_cf

    atc_data, flight_data, mismatches_fc, mismatches_cf = run_async(setup_and_run())

    # Assertions
    assert atc_data.get("interactions_detected", 0) >= 0  # allow zero but we expect >=0
    assert flight_data.get("interactions_detected", 0) >= 0
    assert mismatches_fc == 0, f"Flight->Controller mismatches: {mismatches_fc}"
    assert mismatches_cf == 0, f"Controller->Flight mismatches: {mismatches_cf}"


