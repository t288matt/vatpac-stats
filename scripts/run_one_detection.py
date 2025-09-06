#!/usr/bin/env python3
import asyncio
import json

from sqlalchemy import text

from app.services.atc_detection_service import ATCDetectionService
from app.database import get_database_session


async def main():
    async with get_database_session() as session:
        res = await session.execute(text("SELECT id,callsign,departure,arrival,logon_time FROM flight_summaries WHERE enrichment_completed_at IS NOT NULL ORDER BY enrichment_completed_at DESC LIMIT 1"))
        row = res.fetchone()
        if not row:
            print("No enriched flight summary found")
            return
        fid, callsign, dep, arr, logon = row
        print("Sample flight:", fid, callsign, dep, arr, logon)

    svc = ATCDetectionService()
    try:
        atc = asyncio.run(svc.detect_flight_atc_interactions_with_timeout(callsign, dep, arr, logon, timeout_seconds=30.0))
    except Exception as e:
        print("Detection error:", e)
        return

    print("Detection result:")
    print(json.dumps(atc, default=str, indent=2))


if __name__ == '__main__':
    asyncio.run(main())




