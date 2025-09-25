import sys
import os
import pytest
from datetime import datetime, timezone, timedelta

# Ensure project root is on sys.path so `app` package is importable when running tests directly
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.atc_detection_service import ATCDetectionService
from types import SimpleNamespace


class DummySession:
    def __init__(self, rows=None, single=None):
        self._rows = rows or []
        self._single = single

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        # returns an object with fetchall() / fetchone()
        async def _execute():
            return SimpleNamespace(
                fetchall=lambda: self._rows,
                fetchone=lambda: self._single
            )
        return _execute()


class DummySessionFactory:
    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self._session


@pytest.mark.asyncio
async def test_get_airborne_time_helper_no_rows(monkeypatch):
    svc = ATCDetectionService()
    # Use a time window that will have no data
    t0 = datetime.now(timezone.utc) - timedelta(hours=1)
    t1 = datetime.now(timezone.utc)
    # monkeypatch get_database_session to return empty
    dummy = DummySession(rows=[])
    monkeypatch.setattr('app.services.atc_detection_service.get_database_session', lambda: dummy)
    minutes = await svc._get_airborne_time_from_flights('NONEXIST', 'AAA', 'BBB', t0, t1)
    assert isinstance(minutes, float)
    assert minutes == 0.0


@pytest.mark.asyncio
async def test_count_airborne_controller_contacts_empty():
    svc = ATCDetectionService()
    cnt = await svc._count_airborne_controller_contacts('NONEXIST', [], datetime.now(timezone.utc))
    assert isinstance(cnt, int)
    assert cnt == 0


@pytest.mark.asyncio
async def test_get_airborne_time_from_flights_segments(monkeypatch):
    svc = ATCDetectionService()
    base = datetime.now(timezone.utc)
    # create three timestamps within gap tolerance (poll 60s, multiplier 2.5 => tolerance 150s)
    ts = [base, base + timedelta(seconds=60), base + timedelta(seconds=120)]
    rows = [SimpleNamespace(ts=t) for t in ts]
    dummy = DummySession(rows=rows)
    monkeypatch.setattr('app.services.atc_detection_service.get_database_session', lambda: dummy)
    minutes = await svc._get_airborne_time_from_flights('TEST1', 'AAA', 'BBB', base - timedelta(minutes=1), base + timedelta(minutes=3))
    # span from first to last = 120s => 2 minutes
    assert minutes == 2.0 or minutes == 2


