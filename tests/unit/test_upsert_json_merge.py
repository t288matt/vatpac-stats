import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.database import get_database_session


@pytest.mark.asyncio
async def test_update_first_upsert_updates_completion_and_deptime_and_route():
    callsign = "UPSRT1"
    cid = 101010
    dep = "YSSY"
    arr = "YMML"
    logon_time = datetime.now(timezone.utc) - timedelta(hours=12)
    t1 = logon_time + timedelta(hours=1)
    t2 = logon_time + timedelta(hours=2)

    async with get_database_session() as session:
        # Clean any leftovers
        await session.execute(
            text(
                """
                DELETE FROM flight_summaries
                WHERE callsign=:c AND cid=:cid AND departure=:d AND arrival=:a AND logon_time=:l
                """
            ),
            {"c": callsign, "cid": cid, "d": dep, "a": arr, "l": logon_time},
        )

        # Insert initial row
        await session.execute(
            text(
                """
                INSERT INTO flight_summaries (
                  callsign, departure, arrival, deptime, logon_time, route, cid, completion_time, controller_callsigns
                ) VALUES (
                  :c, :d, :a, '0900', :l, 'ROUTE0', :cid, :ct1, '{"ML-HYD_CTR": {}}'::jsonb
                )
                """
            ),
            {"c": callsign, "d": dep, "a": arr, "l": logon_time, "cid": cid, "ct1": t1},
        )

        # Read back stored logon_time (avoid precision/rounding mismatch)
        stored = (
            await session.execute(
                text(
                    """
                    SELECT logon_time
                    FROM flight_summaries
                    WHERE callsign=:c AND cid=:cid AND departure=:d AND arrival=:a
                    ORDER BY logon_time DESC
                    LIMIT 1
                    """
                ),
                {"c": callsign, "cid": cid, "d": dep, "a": arr},
            )
        ).first()
        assert stored is not None
        stored_logon = stored.logon_time

        # Update-first upsert logic (as in code):
        await session.execute(
            text(
                """
                UPDATE flight_summaries
                SET
                  completion_time = GREATEST(completion_time, :new_completion_time),
                  deptime = :new_deptime,
                  route = COALESCE(:new_route, route),
                  updated_at = NOW()
                WHERE callsign = :callsign
                  AND cid = :cid
                  AND departure = :dep
                  AND arrival = :arr
                  AND logon_time = :logon
                """
            ),
            {
                "new_completion_time": t2,
                "new_deptime": "0930",
                "new_route": "ROUTE1",
                "callsign": callsign,
                "cid": cid,
                "dep": dep,
                "arr": arr,
                "logon": stored_logon,
            },
        )

        # Verify
        row = (
            await session.execute(
                text(
                    """
                    SELECT completion_time, deptime, route, controller_callsigns
                    FROM flight_summaries
                    WHERE callsign=:c AND cid=:cid AND departure=:d AND arrival=:a
                    ORDER BY logon_time DESC
                    LIMIT 1
                    """
                ),
                {"c": callsign, "cid": cid, "d": dep, "a": arr},
            )
        ).first()

        assert row is not None
        # Allow DB second-level rounding
        assert abs((row.completion_time - t2).total_seconds()) <= 1.0
        assert row.deptime == "0930"
        assert row.route == "ROUTE1"
        # controller_callsigns unchanged by update-first step
        assert "ML-HYD_CTR" in row.controller_callsigns


