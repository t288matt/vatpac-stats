import asyncio
from datetime import datetime, timezone, timedelta

import os
import pytest

from app.services.data_service import DataService


class DummyResult:
    def __init__(self):
        self.rowcount = 0

    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def scalar(self):
        return None


class DummySession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, *args, **kwargs):
        return DummyResult()

    async def commit(self):
        return None

    async def rollback(self):
        return None


@pytest.mark.asyncio
async def test_canonical_processing_respects_max_batch(monkeypatch):
    """Verify that _process_completed_flights_canonical truncates sessions to FLIGHT_SUMMARY_MAX_BATCH."""

    svc = DataService()

    # Create 25 fake canonical sessions
    sessions = []
    now = datetime.now(timezone.utc)
    for i in range(25):
        sessions.append({
            "callsign": f"CALL{i}",
            "cid": i,
            "departure": "AAA",
            "arrival": "BBB",
            "session_start": now - timedelta(hours=2),
            "session_end": now - timedelta(hours=1),
            "latest_deptime": None,
            "latest_route": None,
        })

    async def fake_select_canonical_sessions(*args, **kwargs):
        return sessions

    # Patch selector and DB session to avoid hitting real database
    monkeypatch.setattr("app.services.data_service.select_canonical_sessions", fake_select_canonical_sessions)
    monkeypatch.setattr("app.services.data_service.get_database_session", lambda: DummySession())

    # Patch ATC enrichment to return quickly
    async def fake_atc_enrich(*args, **kwargs):
        return {"controller_callsigns": {}, "controller_time_percentage": 0.0, "airborne_controller_time_percentage": 0.0}

    svc.atc_detection_service.detect_flight_atc_interactions_with_timeout = fake_atc_enrich

    # Set environment limit to 10
    monkeypatch.setenv("FLIGHT_SUMMARY_MAX_BATCH", "10")

    result = await svc._process_completed_flights_canonical()

    # The canonical processor should detect and limit to 10 sessions (env limit)
    assert isinstance(result, dict)
    assert result.get("sessions_detected") == 10, f"Expected 10 sessions detected, got {result}"
    # Summaries processed should be <= the configured limit (DB mocked so may be 0)
    assert result.get("summaries_processed", 0) <= 10


