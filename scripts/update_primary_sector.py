#!/usr/bin/env python3
"""Populate `primary_enroute_sector` from existing `sector_breakdown` JSON.

This script updates rows where `sector_breakdown` is non-empty but
`primary_enroute_sector` is NULL. It prints the number of rows updated
and lists the affected rows (id, callsign, primary_enroute_sector).
"""
from app.database import get_sync_engine
from sqlalchemy import text


def main() -> int:
    engine = get_sync_engine()
    sql = """
WITH sub AS (
  SELECT id,
         (SELECT key
          FROM jsonb_each_text(sector_breakdown::jsonb)
          ORDER BY (value::integer) DESC
          LIMIT 1) AS primary_sector
  FROM flight_summaries
  WHERE sector_breakdown IS NOT NULL AND sector_breakdown <> '{}'::jsonb
)
UPDATE flight_summaries
SET primary_enroute_sector = sub.primary_sector
FROM sub
WHERE flight_summaries.id = sub.id
  AND flight_summaries.primary_enroute_sector IS NULL
RETURNING flight_summaries.id, flight_summaries.callsign, flight_summaries.primary_enroute_sector;
"""
    with engine.connect() as conn:
        res = conn.execute(text(sql))
        rows = res.fetchall()
        print("Updated rows:", len(rows))
        for r in rows:
            print(r)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())





