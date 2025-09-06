#!/usr/bin/env python3
import asyncio
from datetime import datetime, timezone, timedelta
import json

from sqlalchemy import text
from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService
from app.services.flight_detection_service import FlightDetectionService


async def insert_transceivers():
    now = datetime.now(timezone.utc)
    t1 = now - timedelta(seconds=60)
    t2 = now - timedelta(seconds=30)
    flight_callsign = 'ITST1'
    controller_callsign = 'CTLR1'
    freq = 123450000  # 123.45 MHz

    async with get_database_session() as session:
        # Insert flight transceivers
        await session.execute(text("""
            INSERT INTO transceivers (callsign, transceiver_id, frequency, position_lat, position_lon, entity_type, entity_id, "timestamp") VALUES
            (:callsign, 1, :freq,  -33.86, 151.21, 'flight', NULL, :t1),
            (:callsign, 2, :freq,  -33.86, 151.21, 'flight', NULL, :t2)
        """), {"callsign": flight_callsign, "freq": freq, "t1": t1, "t2": t2})

        # Insert controller transceivers (same frequency/time window)
        await session.execute(text("""
            INSERT INTO transceivers (callsign, transceiver_id, frequency, position_lat, position_lon, entity_type, entity_id, "timestamp") VALUES
            (:ccallsign, 101, :freq, -33.87, 151.21, 'atc', NULL, :t1),
            (:ccallsign, 102, :freq, -33.87, 151.21, 'atc', NULL, :t2)
        """), {"ccallsign": controller_callsign, "freq": freq, "t1": t1, "t2": t2})

        await session.commit()
    return flight_callsign, controller_callsign, t1, t2


async def run_detection():
    flight_callsign, controller_callsign, t1, t2 = await insert_transceivers()

    atc_svc = ATCDetectionService()
    flight_result = await atc_svc.detect_flight_atc_interactions_with_timeout(flight_callsign, '', '', t1, timeout_seconds=30.0)

    flight_svc = FlightDetectionService()
    # Use a controller session window that covers t1..t2
    ctrl_result = await flight_svc.detect_controller_flight_interactions_with_timeout(controller_callsign, t1 - timedelta(seconds=5), t2 + timedelta(seconds=5), timeout_seconds=30.0)

    print('Flight detection result:')
    print(json.dumps(flight_result, default=str, indent=2))
    print('\nController detection result:')
    print(json.dumps(ctrl_result, default=str, indent=2))

    # Basic assertions
    flight_has_controller = bool(flight_result.get('controller_callsigns'))
    controller_has_flight = bool(ctrl_result.get('flights_detected', False))

    print('\nAssertions:')
    print('flight_has_controller ->', flight_has_controller)
    print('controller_has_flight ->', controller_has_flight)

    if not (flight_has_controller and controller_has_flight):
        raise SystemExit('Integration test FAILED: detection did not find symmetric matches')
    else:
        print('Integration test PASSED: symmetric detection found matches')


if __name__ == '__main__':
    asyncio.run(run_detection())




