#!/usr/bin/env python3
"""Run a small batch recalculation of airborne metrics and print before/after summaries.

Usage:
    python scripts/run_recalc_and_measure.py
"""
import asyncio
from datetime import datetime

from sqlalchemy import text

import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.atc_detection_service import ATCDetectionService
from app.database import get_database_session


async def run_query(sql, params=None):
    async with get_database_session() as session:
        res = await session.execute(text(sql), params or {})
        try:
            rows = res.fetchall()
            return rows
        except Exception:
            return res.fetchone()


async def snapshot_stats(window_days=7):
    # asyncpg does not support parameterizing INTERVAL expressions; interpolate safely
    q = f"""
    SELECT
      COUNT(*) as total_summaries,
      COUNT(CASE WHEN airborne_controller_time_percentage = 0.0 THEN 1 END) as zero_pct,
      AVG(airborne_controller_time_percentage) as avg_airborne_pct,
      AVG(total_enroute_time_minutes) as avg_enroute_minutes
    FROM flight_summaries
    WHERE completion_time >= NOW() - INTERVAL '{window_days} days'
    """
    rows = await run_query(q)
    return rows[0] if rows else None


async def main():
    svc = ATCDetectionService()

    # Allow overriding via environment variables for staging runs
    window_days = int(os.getenv("RECALC_DAYS", os.getenv("WINDOW_DAYS", "7")))
    batch_size = int(os.getenv("RECALC_BATCH", os.getenv("BATCH", "50")))

    print(f"Snapshot BEFORE recalculation (window_days={window_days}):")
    before = await snapshot_stats(window_days)
    print(before)

    print(f"Running recalculation ({window_days} days, batch {batch_size})...")
    processed = await svc.recalculate_airborne_for_summaries(days=window_days, batch_size=batch_size)
    print(f"Processed summaries: {processed}")

    print(f"Snapshot AFTER recalculation (window_days={window_days}):")
    after = await snapshot_stats(window_days)
    print(after)


if __name__ == '__main__':
    asyncio.run(main())


