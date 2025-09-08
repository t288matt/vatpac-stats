#!/usr/bin/env python3
"""
Backfill missing descriptive fields on flight_summaries from flights / flights_archive.

Populates NULL fields such as name, aircraft_type, server, pilot/military ratings,
flight_rules, aircraft_faa, planned_altitude, aircraft_short using the most recent
flight record within the summary's session window.

Usage (inside container):
  python scripts/backfill_flight_summary_fields.py --limit 1000
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.database import get_database_session


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_flight_summary_fields")


CANDIDATE_SELECT = text(
    """
    SELECT id, callsign, cid, departure, arrival, logon_time, completion_time,
           name, aircraft_type, server, pilot_rating, military_rating,
           flight_rules, aircraft_faa, planned_altitude, aircraft_short
    FROM flight_summaries
    WHERE (
        name IS NULL
        OR aircraft_type IS NULL
        OR server IS NULL
        OR pilot_rating IS NULL
        OR military_rating IS NULL
        OR flight_rules IS NULL
        OR aircraft_faa IS NULL
        OR planned_altitude IS NULL
        OR aircraft_short IS NULL
    )
    ORDER BY id
    LIMIT :limit
    """
)


LATEST_FROM_FLIGHTS = text(
    """
    SELECT
        f.aircraft_type,
        f.flight_rules,
        f.aircraft_faa,
        f.planned_altitude,
        f.aircraft_short,
        f.cid,
        f.name,
        f.server,
        f.pilot_rating,
        f.military_rating
    FROM flights f
    WHERE f.callsign = :callsign
      AND (f.cid IS NOT DISTINCT FROM :cid)
      AND (f.departure IS NOT DISTINCT FROM :departure)
      AND (f.arrival IS NOT DISTINCT FROM :arrival)
      AND f.last_updated BETWEEN :start AND :end
    ORDER BY f.last_updated DESC
    LIMIT 1
    """
)


LATEST_FROM_ARCHIVE = text(
    """
    SELECT
        fa.aircraft_type,
        fa.flight_rules,
        fa.aircraft_faa,
        fa.planned_altitude,
        fa.aircraft_short,
        fa.cid,
        fa.name,
        fa.server,
        fa.pilot_rating,
        fa.military_rating
    FROM flights_archive fa
    WHERE fa.callsign = :callsign
      AND (fa.cid IS NOT DISTINCT FROM :cid)
      AND (fa.departure IS NOT DISTINCT FROM :departure)
      AND (fa.arrival IS NOT DISTINCT FROM :arrival)
      AND fa.last_updated BETWEEN :start AND :end
    ORDER BY fa.last_updated DESC
    LIMIT 1
    """
)


UPDATE_SUMMARY = text(
    """
    UPDATE flight_summaries
    SET
        name = COALESCE(name, :name),
        aircraft_type = COALESCE(aircraft_type, :aircraft_type),
        server = COALESCE(server, :server),
        pilot_rating = COALESCE(pilot_rating, :pilot_rating),
        military_rating = COALESCE(military_rating, :military_rating),
        flight_rules = COALESCE(flight_rules, :flight_rules),
        aircraft_faa = COALESCE(aircraft_faa, :aircraft_faa),
        planned_altitude = COALESCE(planned_altitude, :planned_altitude),
        aircraft_short = COALESCE(aircraft_short, :aircraft_short),
        updated_at = NOW()
    WHERE id = :id
    """
)


async def _fetch_latest_values(session, callsign: str, cid: Optional[int], departure: Optional[str], arrival: Optional[str], start: datetime, end: datetime) -> Optional[Dict[str, Any]]:
    params = {
        "callsign": callsign,
        "cid": cid,
        "departure": departure,
        "arrival": arrival,
        "start": start,
        "end": end,
    }
    res = await session.execute(LATEST_FROM_FLIGHTS, params)
    row = res.fetchone()
    if row:
        return dict(row._mapping)

    res = await session.execute(LATEST_FROM_ARCHIVE, params)
    row = res.fetchone()
    if row:
        return dict(row._mapping)

    return None


async def backfill_batch(limit: int) -> int:
    updated = 0
    async with get_database_session() as session:
        now = datetime.now(timezone.utc)
        res = await session.execute(CANDIDATE_SELECT, {"limit": limit})
        candidates = res.fetchall()
        if not candidates:
            logger.info("No candidates found with NULL fields")
            return 0

        for c in candidates:
            c_map = c._mapping
            fs_id = c_map["id"]
            callsign = c_map["callsign"]
            cid = c_map["cid"]
            departure = c_map["departure"]
            arrival = c_map["arrival"]
            start = c_map["logon_time"]
            end = c_map["completion_time"] or now

            latest = await _fetch_latest_values(session, callsign, cid, departure, arrival, start, end)
            if not latest:
                logger.debug(f"No latest values found for {callsign} {departure}->{arrival} (cid={cid}) @ {start}")
                continue

            params = {
                "id": fs_id,
                "name": latest.get("name"),
                "aircraft_type": latest.get("aircraft_type"),
                "server": latest.get("server"),
                "pilot_rating": latest.get("pilot_rating"),
                "military_rating": latest.get("military_rating"),
                "flight_rules": latest.get("flight_rules"),
                "aircraft_faa": latest.get("aircraft_faa"),
                "planned_altitude": latest.get("planned_altitude"),
                "aircraft_short": latest.get("aircraft_short"),
            }

            upd_res = await session.execute(UPDATE_SUMMARY, params)
            if upd_res.rowcount and upd_res.rowcount > 0:
                updated += upd_res.rowcount

        await session.commit()

    logger.info(f"Backfill complete. Updated rows: {updated}")
    return updated


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backfill flight_summaries descriptive fields from flights/flights_archive")
    parser.add_argument("--limit", type=int, default=1000, help="Max number of summaries to process per run")
    args = parser.parse_args()

    await backfill_batch(args.limit)


if __name__ == "__main__":
    asyncio.run(main())


