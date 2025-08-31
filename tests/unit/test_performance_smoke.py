import asyncio
import time

import pytest

from app.services.data_service import DataService


@pytest.mark.asyncio
async def test_performance_smoke_small_batch_finishes_quickly():
    svc = DataService()

    # Warm-up
    await svc.process_completed_flights()

    start = time.perf_counter()
    res = await svc.process_completed_flights()
    elapsed = time.perf_counter() - start

    assert isinstance(res, dict)
    # Generous SLA for CI/container variability
    assert elapsed < 15.0, f"Small batch exceeded SLA: {elapsed:.2f}s"


