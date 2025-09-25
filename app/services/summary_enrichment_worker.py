"""Simple single-process enrichment worker.

This worker claims pending summary rows (both flight_summaries and controller_summaries)
and runs enrichment logic using the detection services. It is intentionally minimal and
single-threaded to keep behaviour deterministic for initial rollout.
"""
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict

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
        
        # Load valid controller callsigns for filtering
        self.valid_controllers = self._load_controller_callsigns()
        logger.info(f"SummaryEnrichmentWorker: Loaded {len(self.valid_controllers)} valid controller callsigns for validation")
    
    def _load_controller_callsigns(self) -> set:
        """Load valid controller callsigns from config file (format: CALLSIGN, FREQUENCY)."""
        try:
            controllers = set()
            with open('airspace_sector_data/controller_callsigns_list.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:  # Skip empty lines
                        # Parse format: CALLSIGN, FREQUENCY
                        if ',' in line:
                            callsign = line.split(',')[0].strip()
                            if callsign:  # Only add if callsign is not empty
                                controllers.add(callsign)
                        else:
                            # Fallback for old format (just callsign)
                            controllers.add(line)
            logger.info(f"Successfully loaded {len(controllers)} valid controller callsigns from config file")
            return controllers
        except Exception as e:
            logger.error(f"Failed to load controller callsigns from config file: {e}")
            return set()
    
    def _filter_valid_controllers(self, atc_data: Dict) -> Dict:
        """Filter out invalid controllers from ATC data before storing in JSONB."""
        if not atc_data.get('controller_callsigns') or not self.valid_controllers:
            return atc_data
        
        original_controllers = atc_data['controller_callsigns']
        filtered_controllers = {}
        filtered_count = 0
        
        for callsign, data in original_controllers.items():
            if callsign in self.valid_controllers:
                filtered_controllers[callsign] = data
            else:
                logger.debug(f"Filtering out invalid controller from JSONB: {callsign}")
                filtered_count += 1
        
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} invalid controller callsigns from JSONB data")
        
        # Update the ATC data with filtered controllers
        atc_data['controller_callsigns'] = filtered_controllers
        return atc_data

    async def run_once(self):
        # Attempt to claim a pending flight summary; if none, claim a pending controller summary.
        fs_id = None
        controller_job = None

        async with get_database_session() as session:
            # Try flight summary
            claim_flight_sql = text("""
                SELECT id, callsign, departure, arrival, logon_time
                FROM flight_summaries
                WHERE enrichment_status = 'pending' AND enrichment_run_after <= now() AND completion_time IS NOT NULL
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
                
                # Apply controller validation filter before storing to JSONB
                atc_data = self._filter_valid_controllers(atc_data)
                
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
                    # Guard: ensure completion_time is still present before writing completion
                    try:
                        ct_res = await session.execute(text("""
                            SELECT completion_time FROM flight_summaries WHERE id = :id
                        """), {"id": fs_id})
                        ct_val = ct_res.scalar()
                    except Exception:
                        ct_val = None
                    if not ct_val:
                        # Requeue with backoff instead of writing an empty/incorrect enrichment
                        await session.execute(text("""
                            UPDATE flight_summaries
                            SET enrichment_status = 'pending',
                                enrichment_run_after = now() + interval '300 seconds',
                                enrichment_last_error = COALESCE(enrichment_last_error, '') || ' | deferred: missing completion_time',
                                updated_at = now()
                            WHERE id = :id
                        """), {"id": fs_id})
                        await session.commit()
                        logger.info(f"Deferring flight enrichment id={fs_id} callsign={callsign}: completion_time missing")
                        return False
                    # Use custom default serializer to handle Decimal, datetime, etc.
                    controller_callsigns_json = json.dumps(atc_data.get("controller_callsigns", {}), default=_json_default)

                    # Compute total enroute time (minutes) using flights/flights_archive/transceivers
                    total_enroute_minutes = None
                    try:
                        # Re-read completion_time (ct_val) which we checked exists above
                        ct_res = await session.execute(text("SELECT completion_time FROM flight_summaries WHERE id = :id"), {"id": fs_id})
                        ct_val = ct_res.scalar()
                        if ct_val:
                            total_enroute = await self.atc_service._get_airborne_time_from_flights(callsign, departure, arrival, logon_time, ct_val)
                            try:
                                total_enroute_minutes = int(total_enroute) if total_enroute is not None else 0
                            except Exception:
                                logger.exception("Failed to convert total_enroute to int")
                                total_enroute_minutes = 0
                        else:
                            total_enroute_minutes = 0
                    except Exception:
                        logger.exception("Failed to compute total_enroute from flights for enrichment")
                        total_enroute_minutes = 0

                    if total_enroute_minutes == 0:
                        logger.debug(f"Computed total_enroute_minutes=0 for fs_id={fs_id} callsign={callsign}; may indicate missing archive/transceiver records or short duration")

                    await session.execute(text("""
                        UPDATE flight_summaries
                        SET controller_callsigns = :controller_callsigns,
                            controller_time_percentage = :ctp,
                            airborne_controller_time_percentage = :actp,
                            time_online_minutes = :time_online,
                            total_enroute_time_minutes = :enroute,
                            enrichment_status = 'completed',
                            enrichment_completed_at = now(),
                            updated_at = now()
                        WHERE id = :id
                    """), {
                        "controller_callsigns": controller_callsigns_json,
                        "ctp": atc_data.get("controller_time_percentage", None),
                        "actp": atc_data.get("airborne_controller_time_percentage", None),
                        "time_online": atc_data.get("total_controller_time_minutes", None),
                        "enroute": total_enroute_minutes,
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


