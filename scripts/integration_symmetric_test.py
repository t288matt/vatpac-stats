#!/usr/bin/env python3
import asyncio
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService
from app.services.flight_detection_service import FlightDetectionService


async def main():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    flight_callsign = "INTGFL"
    controller_callsign = "INTGCT"
    freq = 123450000

    async with get_database_session() as session:
        # Insert deterministic transceivers
        await session.execute(text("""
            INSERT INTO transceivers (callsign, transceiver_id, frequency, position_lat, position_lon, height_msl, height_agl, entity_type, entity_id, "timestamp")
            VALUES (:fc, 999901, :freq, 0.0, 0.0, 1000, 100, 'flight', NULL, :ts),
                   (:cc, 999902, :freq, 0.0, 0.0, 1000, 100, 'atc', NULL, :ts)
        """), {"fc": flight_callsign, "cc": controller_callsign, "freq": freq, "ts": now})
        await session.commit()

        print("Inserted transceivers:")
        rows = await session.execute(text("SELECT id, callsign, transceiver_id, frequency, entity_type, \"timestamp\" FROM transceivers WHERE transceiver_id IN (999901,999902) ORDER BY transceiver_id"))
        for r in rows.fetchall():
            print(r)

    # Run ATC detection for flight
    atc = ATCDetectionService()
    atc_res = await atc.detect_flight_atc_interactions_with_timeout(flight_callsign, '', '', now, timeout_seconds=10.0)

    # Run Flight detection for controller
    fds = FlightDetectionService()
    ctrl_res = await fds.detect_controller_flight_interactions_with_timeout(controller_callsign, now - timedelta(seconds=10), now + timedelta(seconds=10), timeout_seconds=10.0)

    print('\nATC detection result:')
    print(json.dumps(atc_res, default=str, indent=2))

    print('\nController detection result:')
    print(json.dumps(ctrl_res, default=str, indent=2))

    # Cleanup
    async with get_database_session() as session:
        await session.execute(text("DELETE FROM transceivers WHERE transceiver_id IN (999901,999902)"))
        await session.commit()
        print('\nCleaned up transceivers')


if __name__ == '__main__':
    asyncio.run(main())



