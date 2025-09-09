#!/usr/bin/env python3
"""
Inspect recent backfill results in `flight_summaries`.

Usage (inside container):
  PYTHONPATH=/app python /app/scripts/inspect_backfill_results.py
"""
import asyncio
from sqlalchemy import text
from app.database import get_database_session


async def main():
    async with get_database_session() as session:
        q_base = "updated_at >= now() - interval '1 hour'"
        total_res = await session.execute(text(f"SELECT COUNT(*) FROM flight_summaries WHERE {q_base}"))
        total = total_res.scalar() or 0
        print(f"Recent summaries updated in last 1 hour: {total}")

        fields = [
            'time_online_minutes',
            'sector_breakdown',
            'primary_enroute_sector',
            'total_enroute_sectors',
            'total_enroute_time_minutes',
            'controller_callsigns',
            'controller_time_percentage',
            'airborne_controller_time_percentage'
        ]

        for f in fields:
            res = await session.execute(text(f"SELECT COUNT(*) FROM flight_summaries WHERE {q_base} AND {f} IS NOT NULL"))
            print(f"{f}:", res.scalar() or 0)

        all_cond = ' AND '.join([f"{f} IS NOT NULL" for f in fields])
        res_all = await session.execute(text(f"SELECT COUNT(*) FROM flight_summaries WHERE {q_base} AND {all_cond}"))
        print("Rows with all target fields populated:", res_all.scalar() or 0)

        print('\nSample recent updated summaries:')
        sample_q = text(f"SELECT id,callsign,completion_time,time_online_minutes,controller_time_percentage,airborne_controller_time_percentage,primary_enroute_sector,total_enroute_sectors,total_enroute_time_minutes,sector_breakdown,updated_at FROM flight_summaries WHERE {q_base} ORDER BY updated_at DESC LIMIT 10")
        sres = await session.execute(sample_q)
        for row in sres.fetchall():
            print(row)


if __name__ == '__main__':
    asyncio.run(main())





