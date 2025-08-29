#!/usr/bin/env python3
"""
Regression tests for completed controller detection query.
Ensures NOT EXISTS with session_start_time and NULL-safe CID check are used.
"""

import pytest
from unittest.mock import AsyncMock, patch
import sys
import types

# Stub out vatsim_service to avoid importing external deps (e.g., httpx) during tests
stub_vs = types.ModuleType('app.services.vatsim_service')
class _StubVATSIMService:  # minimal surface for DataService.initialize
    async def initialize(self):
        return None
stub_vs.VATSIMService = _StubVATSIMService
sys.modules['app.services.vatsim_service'] = stub_vs

from app.services.data_service import DataService


@pytest.mark.asyncio
async def test_identify_query_uses_not_exists_and_session_start_time():
    service = DataService()

    mock_session = AsyncMock()
    class _Result:
        def fetchall(self):
            return []
    mock_session.execute.return_value = _Result()

    captured_sql = {"text": None}

    async def capture_execute(arg1, params=None):
        # arg1 is a SQLAlchemy TextClause; get raw SQL via .text
        try:
            captured_sql["text"] = getattr(arg1, "text", str(arg1))
        except Exception:
            captured_sql["text"] = str(arg1)
        return _Result()

    mock_session.execute.side_effect = capture_execute

    with patch('app.services.data_service.get_database_session') as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session
        await service._identify_completed_controllers(30)

    sql = captured_sql["text"] or ""
    assert "WHERE NOT EXISTS" in sql
    assert "controller_summaries cs" in sql
    assert "cs.session_start_time = c.logon_time" in sql
    assert "cs.cid IS NOT DISTINCT FROM c.cid" in sql
    assert " NOT IN (" not in sql  # guard against regression to tuple NOT IN


@pytest.mark.asyncio
async def test_identify_query_null_safe_cid_present():
    service = DataService()

    mock_session = AsyncMock()
    class _Result:
        def fetchall(self):
            return []
    mock_session.execute.return_value = _Result()

    captured_sql = {"text": None}

    async def capture_execute(arg1, params=None):
        captured_sql["text"] = getattr(arg1, "text", str(arg1))
        return _Result()

    mock_session.execute.side_effect = capture_execute

    with patch('app.services.data_service.get_database_session') as mock_get_session:
        mock_get_session.return_value.__aenter__.return_value = mock_session
        await service._identify_completed_controllers(30)

    sql = captured_sql["text"] or ""
    assert "cs.cid IS NOT DISTINCT FROM c.cid" in sql


