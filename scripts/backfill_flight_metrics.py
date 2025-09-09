#!/usr/bin/env python3
"""
Backfill flight_summaries metrics from flights table.

Populates NULL fields:
 - time_online_minutes
 - sector_breakdown
 - primary_enroute_sector
 - total_enroute_sectors
 - total_enroute_time_minutes
 - controller_callsigns
 - controller_time_percentage
 - airborne_controller_time_percentage

Usage (inside container):
  python scripts/backfill_flight_metrics.py --limit 100
"""

import asyncio
import argparse
import json
import logging
from datetime import timezone

from sqlalchemy import text

from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService
from app.services.data_service import DataService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_flight_metrics")


async def backfill_batch(limit: int = 100, use_archive: bool = False):
    ds = DataService()
    atc = ATCDetectionService()

    async with get_database_session() as session:
        # Find summaries missing any of the target fields and with a completion_time
        q = text("""
            SELECT id, callsign, departure, arrival, cid, logon_time, completion_time
            FROM flight_summaries
            WHERE completion_time IS NOT NULL
              AND (
                    time_online_minutes IS NULL
                    OR sector_breakdown IS NULL
                    OR primary_enroute_sector IS NULL
                    OR total_enroute_sectors IS NULL
                    OR total_enroute_time_minutes IS NULL
                    OR controller_callsigns IS NULL
                    OR controller_time_percentage IS NULL
                    OR airborne_controller_time_percentage IS NULL
                  )
            ORDER BY completion_time DESC
            LIMIT :limit
        """)

        res = await session.execute(q, {"limit": limit})
        rows = res.fetchall()
        if not rows:
            logger.info("No summaries to backfill")
            return 0

        updated = 0
        for r in rows:
            fs_id = r.id
            callsign = r.callsign
            departure = r.departure
            arrival = r.arrival
            cid = r.cid
            logon = r.logon_time
            completion = r.completion_time

            logger.info(f"Backfilling fs_id={fs_id} callsign={callsign} ({departure}->{arrival})")

            # Load flight records for this session from flights table
            fr_sql = text("""
                SELECT MIN(last_updated) AS first_updated, MAX(last_updated) AS last_updated
                FROM flights
                WHERE callsign = :callsign
                  AND cid = :cid
                  AND departure IS NOT DISTINCT FROM :departure
                  AND arrival IS NOT DISTINCT FROM :arrival
                  AND last_updated BETWEEN :logon AND :completion
            """)
            fr_res = await session.execute(fr_sql, {"callsign": callsign, "cid": cid, "departure": departure, "arrival": arrival, "logon": logon, "completion": completion})
            fr_row = fr_res.fetchone()

            # If no records in flights and archive fallback requested, check flights_archive
            if (not fr_row or not fr_row.first_updated or not fr_row.last_updated) and use_archive:
                ar_sql = text("""
                    SELECT MIN(last_updated) AS first_updated, MAX(last_updated) AS last_updated
                    FROM flights_archive
                    WHERE callsign = :callsign
                      AND cid = :cid
                      AND departure IS NOT DISTINCT FROM :departure
                      AND arrival IS NOT DISTINCT FROM :arrival
                      AND last_updated BETWEEN :logon AND :completion
                """)
                ar_res = await session.execute(ar_sql, {"callsign": callsign, "cid": cid, "departure": departure, "arrival": arrival, "logon": logon, "completion": completion})
                ar_row = ar_res.fetchone()
                if ar_row and ar_row.first_updated and ar_row.last_updated:
                    fr_row = ar_row

            time_online_minutes = None
            sector_breakdown = None
            primary_sector = None
            total_sectors = None
            total_enroute_time = None

            if fr_row and fr_row.first_updated and fr_row.last_updated:
                delta = fr_row.last_updated - fr_row.first_updated
                time_online_minutes = int(delta.total_seconds() / 60)

                # Use DataService helper to compute sector breakdown
                try:
                    sector_breakdown = await ds._calculate_sector_breakdown(callsign, session, logon_time=fr_row.first_updated, completion_time=fr_row.last_updated)
                    primary_sector = ds._get_primary_sector(sector_breakdown)
                    total_sectors = len(sector_breakdown)
                    total_enroute_time = sum(sector_breakdown.values())
                except Exception as e:
                    logger.warning(f"Sector breakdown failed for {callsign}: {e}")

            # Run ATC detection (short timeout) to fill controller fields and airborne percentage
            controller_callsigns = None
            controller_time_percentage = None
            airborne_controller_time_percentage = None
            try:
                atc_data = await atc.detect_flight_atc_interactions_with_timeout(callsign, departure, arrival, logon, timeout_seconds=30.0)
                controller_callsigns = json.dumps(atc_data.get("controller_callsigns") or {})
                controller_time_percentage = atc_data.get("controller_time_percentage")
                airborne_controller_time_percentage = atc_data.get("airborne_controller_time_percentage")
            except Exception as e:
                logger.warning(f"ATC detection failed for {callsign}: {e}")

            # Build update statement only setting fields that are not NULL currently
            upd_sql = text("""
                UPDATE flight_summaries
                SET
                    time_online_minutes = COALESCE(time_online_minutes, :time_online_minutes),
                    sector_breakdown = COALESCE(sector_breakdown, :sector_breakdown),
                    primary_enroute_sector = COALESCE(primary_enroute_sector, :primary_enroute_sector),
                    total_enroute_sectors = COALESCE(total_enroute_sectors, :total_enroute_sectors),
                    total_enroute_time_minutes = COALESCE(total_enroute_time_minutes, :total_enroute_time_minutes),
                    controller_callsigns = COALESCE(controller_callsigns, :controller_callsigns),
                    controller_time_percentage = COALESCE(controller_time_percentage, :controller_time_percentage),
                    airborne_controller_time_percentage = COALESCE(airborne_controller_time_percentage, :airborne_controller_time_percentage),
                    updated_at = NOW()
                WHERE id = :id
            """)

            params = {
                "id": fs_id,
                "time_online_minutes": time_online_minutes,
                "sector_breakdown": json.dumps(sector_breakdown) if sector_breakdown is not None else None,
                "primary_enroute_sector": primary_sector,
                "total_enroute_sectors": total_sectors,
                "total_enroute_time_minutes": total_enroute_time,
                "controller_callsigns": controller_callsigns,
                "controller_time_percentage": controller_time_percentage,
                "airborne_controller_time_percentage": airborne_controller_time_percentage,
            }

            await session.execute(upd_sql, params)
            updated += 1

        await session.commit()
        logger.info(f"Backfill complete. Updated rows: {updated}")
        return updated


def main():
    parser = argparse.ArgumentParser(description="Backfill flight_summaries metrics from flights table")
    parser.add_argument("--limit", type=int, default=100, help="Max number of summaries to process")
    parser.add_argument("--use-archive", action="store_true", help="Allow fallback to flights_archive when flights table has no records")
    args = parser.parse_args()

    asyncio.run(backfill_batch(args.limit, use_archive=args.use_archive))


if __name__ == '__main__':
    main()


