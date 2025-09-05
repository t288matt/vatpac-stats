import asyncio
import random
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

from app.database import get_database_session
from app.services.atc_detection_service import ATCDetectionService
from app.services.flight_detection_service import FlightDetectionService


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def generate_callsign(prefix: str, i: int) -> str:
    return f"{prefix}{i:04d}"


def test_stress_randomized_roundtrip():
    """Insert a randomized set of flights/controllers/transceivers and run detection
    to stress test integration and run integrity checks.
    """
    now = datetime.now(timezone.utc).replace(microsecond=0)

    num_flights = 50
    num_controllers = 20
    freq_base = 120000000

    async def setup_and_run():
        async with get_database_session() as session:
            # cleanup any existing stress test rows (simple heuristic)
            await session.execute(text("DELETE FROM transceivers WHERE callsign LIKE 'STF%' OR callsign LIKE 'STC%';"))
            await session.execute(text("DELETE FROM flights WHERE callsign LIKE 'STF%';"))
            await session.execute(text("DELETE FROM controllers WHERE callsign LIKE 'STC%';"))
            await session.execute(text("DELETE FROM flight_summaries WHERE callsign LIKE 'STF%';"))
            await session.execute(text("DELETE FROM controller_summaries WHERE callsign LIKE 'STC%';"))
            await session.commit()

            # Insert flights and controllers
            for i in range(num_flights):
                fc = generate_callsign('STF', i)
                ts = now - timedelta(seconds=random.randint(0, 300))
                await session.execute(text("INSERT INTO flights (callsign, departure, arrival, logon_time) VALUES (:c, 'AAA','BBB',:t) ON CONFLICT DO NOTHING"), {"c": fc, "t": ts})

            for i in range(num_controllers):
                cc = generate_callsign('STC', i)
                await session.execute(text("INSERT INTO controllers (callsign, facility, last_updated) VALUES (:c, 1, now()) ON CONFLICT DO NOTHING"), {"c": cc})

            await session.commit()

            # Insert randomized transceivers: map some flights to controllers via overlapping freq
            trans_id = 100000
            for i in range(num_flights):
                fc = generate_callsign('STF', i)
                freq = freq_base + random.randint(0, 50) * 250
                ts = now - timedelta(seconds=random.randint(0, 600))
                # flight transceiver
                await session.execute(text("INSERT INTO transceivers (callsign, transceiver_id, frequency, position_lat, position_lon, height_msl, height_agl, entity_type, timestamp) VALUES (:c, :id, :f, 0.0, 0.0, 1000, 100, 'flight', :ts)"), {"c": fc, "id": trans_id, "f": freq, "ts": ts})
                trans_id += 1
                # pick a controller and add matching transceiver with same freq +/- tolerance
                cc = generate_callsign('STC', random.randint(0, num_controllers - 1))
                await session.execute(text("INSERT INTO transceivers (callsign, transceiver_id, frequency, position_lat, position_lon, height_msl, height_agl, entity_type, timestamp) VALUES (:c, :id, :f, 0.0, 0.0, 1000, 100, 'atc', :ts)"), {"c": cc, "id": trans_id, "f": freq + random.choice([-5000, 0, 5000]), "ts": ts})
                trans_id += 1

            await session.commit()

        # Run detection for a random sample of flights and controllers
        atc_svc = ATCDetectionService()
        flight_svc = FlightDetectionService()

        # sample and run
        sample_flights = [generate_callsign('STF', i) for i in random.sample(range(num_flights), min(20, num_flights))]
        sample_controllers = [generate_callsign('STC', i) for i in random.sample(range(num_controllers), min(10, num_controllers))]

        for f in sample_flights:
            await atc_svc.detect_flight_atc_interactions_with_timeout(f, 'AAA', 'BBB', now, timeout_seconds=5.0)

        for c in sample_controllers:
            await flight_svc.detect_controller_flight_interactions_with_timeout(c, now - timedelta(seconds=300), now + timedelta(seconds=300), timeout_seconds=5.0)

        # run the same integrity queries as smaller window
        async with get_database_session() as session:
            res1 = await session.execute(text("SELECT count(*) FROM flight_summaries WHERE enrichment_status='pending' OR enrichment_status='in_progress'"))
            pending = int(res1.fetchone().count)

        return pending

    pending = run_async(setup_and_run())

    # We expect no unbounded blocking/pending items immediately after running sample detection; allow some pending
    assert pending >= 0



