"""Simple single-process enrichment worker.

This worker claims pending summary rows (both flight_summaries and controller_summaries)
and runs enrichment logic using the detection services. It is intentionally minimal and
single-threaded to keep behaviour deterministic for initial rollout.
"""
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

def _json_default(obj):
    """JSON serializer helper for non-serializable types used in enrichment results.

    - Decimal -> float
    - datetime -> ISO string
    - fallback -> str(obj)
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

from sqlalchemy import text
from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService
from app.services.flight_detection_service import FlightDetectionService

logger = logging.getLogger(__name__)


class SummaryEnrichmentWorker:
    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval
        self.atc_service = ATCDetectionService()
        self.flight_service = FlightDetectionService()

    async def run_once(self):
        # Attempt to claim a pending flight summary; if none, claim a pending controller summary.
        fs_id = None
        controller_job = None

        async with get_database_session() as session:
            # Try flight summary
            claim_flight_sql = text("""
                SELECT id, callsign, departure, arrival, logon_time
                FROM flight_summaries
                WHERE enrichment_status = 'pending' AND enrichment_run_after <= now()
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """)
            res = await session.execute(claim_flight_sql)
            row = res.fetchone()
            if row:
                fs_id = row.id
                callsign = row.callsign
                departure = row.departure
                arrival = row.arrival
                logon_time = row.logon_time

                await session.execute(text("""
                    UPDATE flight_summaries
                    SET enrichment_status = 'in_progress', enrichment_attempts = COALESCE(enrichment_attempts, 0) + 1, updated_at = now()
                    WHERE id = :id
                """), {"id": fs_id})
                await session.commit()
            else:
                # Try controller summary
                claim_controller_sql = text("""
                    SELECT id, callsign, session_start_time, session_end_time
                    FROM controller_summaries
                    WHERE enrichment_status = 'pending' AND enrichment_run_after <= now()
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                """)
                cres = await session.execute(claim_controller_sql)
                crow = cres.fetchone()
                if not crow:
                    return False
                controller_job = {
                    "id": crow.id,
                    "callsign": crow.callsign,
                    "session_start": crow.session_start_time,
                    "session_end": crow.session_end_time,
                }

                await session.execute(text("""
                    UPDATE controller_summaries
                    SET enrichment_status = 'in_progress', enrichment_attempts = COALESCE(enrichment_attempts, 0) + 1, updated_at = now()
                    WHERE id = :id
                """), {"id": controller_job["id"]})
                await session.commit()

        # Run enrichment outside the claim transaction
        import json

        try:
            if fs_id:
                logger.info(f"Enriching flight summary id={fs_id} callsign={callsign}")
                atc_data = await self.atc_service.detect_flight_atc_interactions_with_timeout(callsign, departure, arrival, logon_time, timeout_seconds=30.0)
                # DEBUG: write ATC detection result to a debug file for traceability
                try:
                    import json
                    debug_path = f"/tmp/enrich_flight_{fs_id}_{callsign}.json"
                    with open(debug_path, 'w') as df:
                        json.dump({
                            'fs_id': fs_id,
                            'callsign': callsign,
                            'atc_data': atc_data
                        }, df, default=str, indent=2)
                    logger.debug(f"Wrote flight enrichment debug file: {debug_path}")
                except Exception:
                    logger.exception("Failed to write flight enrichment debug file")

                async with get_database_session() as session:
                    # Use custom default serializer to handle Decimal, datetime, etc.
                    controller_callsigns_json = json.dumps(atc_data.get("controller_callsigns", {}), default=_json_default)
                    await session.execute(text("""
                        UPDATE flight_summaries
                        SET controller_callsigns = :controller_callsigns, controller_time_percentage = :ctp, enrichment_status = 'completed', enrichment_completed_at = now(), updated_at = now()
                        WHERE id = :id
                    """), {
                        "controller_callsigns": controller_callsigns_json,
                        "ctp": atc_data.get("controller_time_percentage", None),
                        "id": fs_id
                    })
                    await session.commit()

                logger.info(f"Enrichment completed id={fs_id} callsign={callsign}")
                return True

            if controller_job:
                cid = controller_job["id"]
                callsign = controller_job["callsign"]
                start = controller_job["session_start"]
                end = controller_job["session_end"]

                logger.info(f"Enriching controller summary id={cid} callsign={callsign}")
                flight_data = await self.flight_service.detect_controller_flight_interactions_with_timeout(callsign, start, end, timeout_seconds=30.0)

                # Log concise detection summary immediately before writing to DB
                try:
                    sample_callsigns = [d.get('callsign') for d in (flight_data.get('details') or [])[:10]]
                    logger.debug(
                        f"Controller enrichment write summary id={cid} callsign={callsign}: flights_detected={flight_data.get('flights_detected')}, total_aircraft={flight_data.get('total_aircraft')}, details_len={len(flight_data.get('details') or [])}, sample_callsigns={sample_callsigns}"
                    )
                except Exception:
                    logger.exception("Failed to log controller enrichment write summary")

                async with get_database_session() as session:
                    # Use custom default serializer to handle Decimal, datetime, etc.
                    aircraft_details_json = json.dumps(flight_data.get("details", []), default=_json_default)
                    hourly_json = json.dumps(flight_data.get("hourly_breakdown", {}), default=_json_default)
                    await session.execute(text("""
                        UPDATE controller_summaries
                        SET aircraft_details = :aircraft_details, total_aircraft_handled = :total, peak_aircraft_count = :peak, hourly_aircraft_breakdown = :hourly, enrichment_status = 'completed', enrichment_completed_at = now(), updated_at = now()
                        WHERE id = :id
                    """), {
                        "aircraft_details": aircraft_details_json,
                        "total": flight_data.get("total_aircraft", 0),
                        "peak": flight_data.get("peak_count", 0),
                        "hourly": hourly_json,
                        "id": cid
                    })
                    await session.commit()

                logger.info(f"Controller enrichment completed id={cid} callsign={callsign}")
                return True

            return False

        except Exception as e:
            logger.exception(f"Enrichment failed: {e}")
            async with get_database_session() as session:
                if fs_id:
                    await session.execute(text("""
                        UPDATE flight_summaries
                        SET enrichment_status = 'pending', enrichment_run_after = now() + interval '60 seconds', enrichment_last_error = :err, updated_at = now()
                        WHERE id = :id
                    """), {"err": str(e), "id": fs_id})
                if controller_job:
                    await session.execute(text("""
                        UPDATE controller_summaries
                        SET enrichment_status = 'pending', enrichment_run_after = now() + interval '60 seconds', enrichment_last_error = :err, updated_at = now()
                        WHERE id = :id
                    """), {"err": str(e), "id": controller_job["id"]})
                await session.commit()
            return False

    async def run_loop(self):
        while True:
            try:
                did = await self.run_once()
                if not did:
                    await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Worker loop unexpected error")
                await asyncio.sleep(self.poll_interval)


async def main():
    w = SummaryEnrichmentWorker()
    await w.run_loop()


if __name__ == '__main__':
    asyncio.run(main())


