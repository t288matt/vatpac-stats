"""Simple single-process enrichment worker.

This worker claims pending summary rows (both flight_summaries and controller_summaries)
and runs enrichment logic using the detection services. It is intentionally minimal and
single-threaded to keep behaviour deterministic for initial rollout.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService

logger = logging.getLogger(__name__)


class SummaryEnrichmentWorker:
    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval
        self.atc_service = ATCDetectionService()

    async def run_once(self):
        # Claim one pending flight summary
        async with get_database_session() as session:
            claim_sql = text("""
                SELECT id, callsign, departure, arrival, logon_time
                FROM flight_summaries
                WHERE enrichment_status = 'pending' AND enrichment_run_after <= now()
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """)
            res = await session.execute(claim_sql)
            row = res.fetchone()
            if not row:
                return False

            fs_id = row.id
            callsign = row.callsign
            departure = row.departure
            arrival = row.arrival
            logon_time = row.logon_time

            # mark in_progress
            await session.execute(text("""
                UPDATE flight_summaries
                SET enrichment_status = 'in_progress', enrichment_attempts = COALESCE(enrichment_attempts, 0) + 1, updated_at = now()
                WHERE id = :id
            """), {"id": fs_id})
            await session.commit()

        # Run enrichment outside the claim transaction
        try:
            logger.info(f"Enriching flight summary id={fs_id} callsign={callsign}")
            atc_data = await self.atc_service.detect_flight_atc_interactions_with_timeout(callsign, departure, arrival, logon_time, timeout_seconds=30.0)

            # Write back results
            async with get_database_session() as session:
                await session.execute(text("""
                    UPDATE flight_summaries
                    SET controller_callsigns = :controller_callsigns, controller_time_percentage = :ctp, enrichment_status = 'completed', enrichment_completed_at = now(), updated_at = now()
                    WHERE id = :id
                """), {
                    "controller_callsigns": atc_data.get("controller_callsigns", {}),
                    "ctp": atc_data.get("controller_time_percentage", None),
                    "id": fs_id
                })
                await session.commit()

            logger.info(f"Enrichment completed id={fs_id} callsign={callsign}")
            return True

        except Exception as e:
            logger.exception(f"Enrichment failed for id={fs_id} callsign={callsign}: {e}")
            # mark pending again with backoff
            async with get_database_session() as session:
                await session.execute(text("""
                    UPDATE flight_summaries
                    SET enrichment_status = 'pending', enrichment_run_after = now() + interval '60 seconds', enrichment_last_error = :err, updated_at = now()
                    WHERE id = :id
                """), {"err": str(e), "id": fs_id})
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


