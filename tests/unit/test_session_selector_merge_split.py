import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.database import get_database_session
from app.services.session_selector import select_canonical_sessions


@pytest.mark.asyncio
async def test_session_merge_split_gap_and_span():
    now = datetime.now(timezone.utc)
    callsign = "TEST123"
    cid = 424242
    dep = "YSSY"
    arr = "YMML"

    # Build three segments:
    # seg1: t0..t1, seg2: within 2h gap (should merge), seg3: >2h gap (should split)
    t0 = now - timedelta(hours=10)
    t1 = now - timedelta(hours=9, minutes=30)
    t2 = now - timedelta(hours=9, minutes=0)  # within 2h from t1
    t3 = now - timedelta(hours=8, minutes=30)
    t4 = now - timedelta(hours=5, minutes=0)  # >2h gap from t3
    t5 = now - timedelta(hours=4, minutes=30)

    async with get_database_session() as session:
        # Clean any prior test rows
        await session.execute(
            text(
                """
                DELETE FROM flights
                WHERE callsign = :callsign AND cid = :cid AND departure = :dep AND arrival = :arr
                """
            ),
            {"callsign": callsign, "cid": cid, "dep": dep, "arr": arr},
        )

        # Insert rows for seg1 (t0..t1)
        await session.execute(
            text(
                """
                INSERT INTO flights (callsign, aircraft_type, departure, arrival, logon_time,
                                      route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
                                      cid, name, server, pilot_rating, military_rating,
                                      latitude, longitude, altitude, groundspeed, heading,
                                      last_updated, deptime)
                VALUES (:callsign, 'B738', :dep, :arr, :logon, 'ROUTE', 'IFR', 'B738', 'FL350', 'B738',
                        :cid, 'Pilot', 'SERVER', 1, 0,
                        0, 0, 0, 0, 0,
                        :last_updated, '0900')
                """
            ),
            {
                "callsign": callsign,
                "dep": dep,
                "arr": arr,
                "logon": t0,
                "cid": cid,
                "last_updated": t1,
            },
        )

        # Insert rows for seg2 (t2..t3) within 2h gap => merge with seg1
        await session.execute(
            text(
                """
                INSERT INTO flights (callsign, aircraft_type, departure, arrival, logon_time,
                                      route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
                                      cid, name, server, pilot_rating, military_rating,
                                      latitude, longitude, altitude, groundspeed, heading,
                                      last_updated, deptime)
                VALUES (:callsign, 'B738', :dep, :arr, :logon, 'ROUTE', 'IFR', 'B738', 'FL350', 'B738',
                        :cid, 'Pilot', 'SERVER', 1, 0,
                        0, 0, 0, 0, 0,
                        :last_updated, '0930')
                """
            ),
            {
                "callsign": callsign,
                "dep": dep,
                "arr": arr,
                "logon": t2,
                "cid": cid,
                "last_updated": t3,
            },
        )

        # Insert rows for seg3 (t4..t5) beyond 2h gap => separate session
        await session.execute(
            text(
                """
                INSERT INTO flights (callsign, aircraft_type, departure, arrival, logon_time,
                                      route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
                                      cid, name, server, pilot_rating, military_rating,
                                      latitude, longitude, altitude, groundspeed, heading,
                                      last_updated, deptime)
                VALUES (:callsign, 'B738', :dep, :arr, :logon, 'ROUTE', 'IFR', 'B738', 'FL350', 'B738',
                        :cid, 'Pilot', 'SERVER', 1, 0,
                        0, 0, 0, 0, 0,
                        :last_updated, '1200')
                """
            ),
            {
                "callsign": callsign,
                "dep": dep,
                "arr": arr,
                "logon": t4,
                "cid": cid,
                "last_updated": t5,
            },
        )

        await session.commit()

    # Use completion_hours large enough so rows qualify
    sessions = await select_canonical_sessions(
        completion_hours=1, gap_minutes=120, max_span_hours=8
    )

    # Filter to our callsign
    own = [s for s in sessions if s["callsign"] == callsign and s["cid"] == cid and s["departure"] == dep and s["arrival"] == arr]

    # Expect two sessions: seg1+seg2 merged, seg3 separate
    assert len(own) == 2


