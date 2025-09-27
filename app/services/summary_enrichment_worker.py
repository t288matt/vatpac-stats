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

import os
from sqlalchemy import text
from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService
from app.services.flight_detection_service import FlightDetectionService

# Get max retries from environment variable
MAX_ENRICHMENT_RETRIES = int(os.getenv('MAX_ENRICHMENT_RETRIES', '5'))


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

    async def _recover_stuck_flights(self):
        """Recover flights stuck in 'in_progress' status for too long."""
        try:
            async with get_database_session() as session:
                # Reset flights stuck in 'in_progress' for more than 5 minutes
                result = await session.execute(text("""
                    UPDATE flight_summaries
                    SET enrichment_status = 'pending',
                        enrichment_run_after = NOW() + INTERVAL '30 seconds',
                        enrichment_last_error = 'Recovered from stuck in_progress status',
                        updated_at = NOW()
                    WHERE enrichment_status = 'in_progress' 
                    AND updated_at < NOW() - INTERVAL '5 minutes'
                    RETURNING id, callsign
                """))
                
                recovered_flights = result.fetchall()
                if recovered_flights:
                    logger.warning(f"Recovered {len(recovered_flights)} flights stuck in 'in_progress' status")
                    for flight in recovered_flights:
                        logger.info(f"Recovered stuck flight: id={flight.id}, callsign={flight.callsign}")
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error recovering stuck flights: {e}")

    async def _stop_infinite_retry_loops(self):
        """Stop infinite retry loops by marking problematic flights as failed."""
        try:
            async with get_database_session() as session:
                # Mark flights with max+ attempts as failed to stop infinite loops
                error_msg = f'MAX_RETRIES_EXCEEDED: Infinite retry loop stopped ({MAX_ENRICHMENT_RETRIES}+ attempts) - DO NOT RESET'
                result = await session.execute(text("""
                    UPDATE flight_summaries
                    SET enrichment_status = 'failed',
                        enrichment_last_error = :error_msg,
                        updated_at = NOW()
                    WHERE enrichment_attempts >= :max_retries
                    AND enrichment_status = 'pending'
                    AND completion_time IS NOT NULL
                    RETURNING id, callsign, enrichment_attempts
                """), {"max_retries": MAX_ENRICHMENT_RETRIES, "error_msg": error_msg})
                
                failed_flights = result.fetchall()
                if failed_flights:
                    logger.warning(f"PERMANENTLY STOPPED {len(failed_flights)} infinite retry loops by marking as failed")
                    for flight in failed_flights:
                        logger.error(f"PERMANENT_RETRY_LOOP_STOPPED: flight id={flight.id}, callsign={flight.callsign}, attempts={flight.enrichment_attempts}")
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error stopping infinite retry loops: {e}")

    async def run_once(self):
        """Process one enrichment job with improved error handling."""
        # Periodically recover stuck flights and stop infinite retry loops
        import random
        if random.random() < 0.01:  # 1% chance per run
            await self._recover_stuck_flights()
            await self._stop_infinite_retry_loops()

        fs_id = None
        controller_job = None

        # FIX: Use a single transaction for claim and process
        try:
            async with get_database_session() as session:
                # Try flight summary first
                claim_flight_sql = text("""
                    SELECT id, callsign, departure, arrival, logon_time
                    FROM flight_summaries
                    WHERE enrichment_status = 'pending' 
                    AND enrichment_run_after <= now() 
                    AND completion_time IS NOT NULL
                    AND COALESCE(enrichment_attempts, 0) < :max_retries
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                """)
                res = await session.execute(claim_flight_sql, {"max_retries": MAX_ENRICHMENT_RETRIES})
                row = res.fetchone()
                
                if row:
                    fs_id = row.id
                    callsign = row.callsign
                    departure = row.departure
                    arrival = row.arrival
                    logon_time = row.logon_time

                    # Check for retry loop before processing
                    attempts_check = await session.execute(text("""
                        SELECT enrichment_attempts FROM flight_summaries WHERE id = :id
                    """), {"id": fs_id})
                    current_attempts = attempts_check.scalar()
                    
                    # Stop retry loops at configured max attempts
                    if current_attempts >= MAX_ENRICHMENT_RETRIES:
                        error_msg = f'MAX_RETRIES_EXCEEDED: Stopped after {MAX_ENRICHMENT_RETRIES} attempts - no more retries'
                        await session.execute(text("""
                            UPDATE flight_summaries
                            SET enrichment_status = 'failed',
                                enrichment_last_error = :error_msg,
                                updated_at = now()
                            WHERE id = :id
                        """), {"id": fs_id, "error_msg": error_msg})
                        await session.commit()
                        logger.warning(f"MAX_RETRIES_EXCEEDED: flight id={fs_id}, callsign={callsign}, attempts={current_attempts}, max={MAX_ENRICHMENT_RETRIES}")
                        return False

                    # Mark as in_progress but don't commit yet
                    await session.execute(text("""
                        UPDATE flight_summaries
                        SET enrichment_status = 'in_progress', 
                            enrichment_attempts = COALESCE(enrichment_attempts, 0) + 1, 
                            updated_at = now()
                        WHERE id = :id
                    """), {"id": fs_id})

                    logger.info(f"Enriching flight summary id={fs_id} callsign={callsign}")
                    
                    # Run enrichment within the same transaction
                    try:
                        atc_data = await self.atc_service.detect_flight_atc_interactions_with_timeout(
                            callsign, departure, arrival, logon_time, timeout_seconds=30.0
                        )
                        
                        # Apply controller validation filter
                        atc_data = self._filter_valid_controllers(atc_data)
                        
                        # Guard: ensure completion_time is still present
                        ct_res = await session.execute(text("""
                            SELECT completion_time FROM flight_summaries WHERE id = :id
                        """), {"id": fs_id})
                        ct_val = ct_res.scalar()
                        
                        if not ct_val:
                            # Requeue with backoff
                            await session.execute(text("""
                                UPDATE flight_summaries
                                SET enrichment_status = 'pending',
                                    enrichment_run_after = now() + interval '300 seconds',
                                    enrichment_last_error = 'deferred: missing completion_time',
                                    updated_at = now()
                                WHERE id = :id
                            """), {"id": fs_id})
                            await session.commit()
                            logger.info(f"Deferring flight enrichment id={fs_id} callsign={callsign}: completion_time missing")
                            return False

                        # Compute total enroute time
                        total_enroute_minutes = 0
                        try:
                            if ct_val:
                                total_enroute = await self.atc_service._get_airborne_time_from_flights(
                                    callsign, departure, arrival, logon_time, ct_val
                                )
                                total_enroute_minutes = int(total_enroute) if total_enroute is not None else 0
                        except Exception:
                            logger.exception("Failed to compute total_enroute from flights for enrichment")
                            total_enroute_minutes = 0

                        # Use custom default serializer
                        import json
                        controller_callsigns_json = json.dumps(
                            atc_data.get("controller_callsigns", {}), default=_json_default
                        )

                        # Complete the enrichment in the same transaction
                        await session.execute(text("""
                            UPDATE flight_summaries
                            SET controller_callsigns = :controller_callsigns,
                                controller_time_percentage = :ctp,
                                airborne_controller_time_percentage = :actp,
                                time_online_minutes = :time_online,
                                total_enroute_time_minutes = :enroute,
                                enrichment_status = 'completed',
                                enrichment_completed_at = now(),
                                enrichment_last_error = NULL,
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
                        
                        # Commit everything together - either all succeeds or all fails
                        await session.commit()
                        logger.info(f"Enrichment completed id={fs_id} callsign={callsign}")
                        return True
                        
                    except Exception as e:
                        # On any error, reset to pending with proper error logging
                        logger.exception(f"Enrichment failed for id={fs_id} callsign={callsign}: {e}")
                        # Use custom backoff schedule: 2, 10, 60, 300, 3600 seconds
                        backoff_schedule = [2, 10, 60, 300, 3600]  # 2s, 10s, 1m, 5m, 1h
                        backoff_seconds = backoff_schedule[min(current_attempts, len(backoff_schedule) - 1)]
                        await session.execute(text("""
                            UPDATE flight_summaries
                            SET enrichment_status = 'pending', 
                                enrichment_run_after = now() + interval ':backoff seconds', 
                                enrichment_last_error = :err, 
                                updated_at = now()
                            WHERE id = :id
                        """), {"err": str(e), "id": fs_id, "backoff": backoff_seconds})
                        await session.commit()
                        return False
                else:
                    # Try controller summary (using similar transaction pattern)
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

                    # Mark as in_progress
                    await session.execute(text("""
                        UPDATE controller_summaries
                        SET enrichment_status = 'in_progress', 
                            enrichment_attempts = COALESCE(enrichment_attempts, 0) + 1, 
                            updated_at = now()
                        WHERE id = :id
                    """), {"id": controller_job["id"]})

                    logger.info(f"Enriching controller summary id={controller_job['id']} callsign={controller_job['callsign']}")
                    
                    try:
                        flight_data = await self.flight_service.detect_controller_flight_interactions_with_timeout(
                            controller_job['callsign'], controller_job['session_start'], controller_job['session_end'], timeout_seconds=30.0
                        )

                        # Use custom default serializer
                        import json
                        aircraft_details_json = json.dumps(flight_data.get("details", []), default=_json_default)
                        hourly_json = json.dumps(flight_data.get("hourly_breakdown", {}), default=_json_default)
                        
                        await session.execute(text("""
                            UPDATE controller_summaries
                            SET aircraft_details = :aircraft_details, 
                                total_aircraft_handled = :total, 
                                peak_aircraft_count = :peak, 
                                hourly_aircraft_breakdown = :hourly, 
                                enrichment_status = 'completed', 
                                enrichment_completed_at = now(), 
                                enrichment_last_error = NULL,
                                updated_at = now()
                            WHERE id = :id
                        """), {
                            "aircraft_details": aircraft_details_json,
                            "total": flight_data.get("total_aircraft", 0),
                            "peak": flight_data.get("peak_count", 0),
                            "hourly": hourly_json,
                            "id": controller_job["id"]
                        })
                        
                        await session.commit()
                        logger.info(f"Controller enrichment completed id={controller_job['id']} callsign={controller_job['callsign']}")
                        return True
                        
                    except Exception as e:
                        logger.exception(f"Controller enrichment failed for id={controller_job['id']} callsign={controller_job['callsign']}: {e}")
                        # Get current attempt count for exponential backoff
                        attempt_result = await session.execute(text("""
                            SELECT COALESCE(enrichment_attempts, 0) as attempts FROM controller_summaries WHERE id = :id
                        """), {"id": controller_job["id"]})
                        current_attempts = attempt_result.fetchone().attempts
                        
                        # Use custom backoff schedule: 2, 10, 60, 300, 3600 seconds
                        backoff_schedule = [2, 10, 60, 300, 3600]  # 2s, 10s, 1m, 5m, 1h
                        backoff_seconds = backoff_schedule[min(current_attempts, len(backoff_schedule) - 1)]
                        await session.execute(text("""
                            UPDATE controller_summaries
                            SET enrichment_status = 'pending', 
                                enrichment_run_after = now() + interval ':backoff seconds', 
                                enrichment_last_error = :err, 
                                updated_at = now()
                            WHERE id = :id
                        """), {"err": str(e), "id": controller_job["id"], "backoff": backoff_seconds})
                        await session.commit()
                        return False

        except Exception as e:
            logger.exception(f"Critical error in enrichment worker: {e}")
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


