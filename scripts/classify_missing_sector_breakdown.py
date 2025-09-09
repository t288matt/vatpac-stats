#!/usr/bin/env python3
"""Classify missing sector_breakdown reasons for today's flight summaries."""
from app.database import get_sync_engine
from sqlalchemy import text


def main():
    eng = get_sync_engine()
    sql_total = """
    SELECT COUNT(*) FROM flight_summaries fs
    WHERE DATE(fs.updated_at) = CURRENT_DATE
      AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
    """

    sql_no_flights = """
    SELECT COUNT(DISTINCT fs.id)
    FROM flight_summaries fs
    LEFT JOIN flights f ON f.callsign = fs.callsign
      AND f.cid = fs.cid
      AND f.departure IS NOT DISTINCT FROM fs.departure
      AND f.arrival IS NOT DISTINCT FROM fs.arrival
      AND f.logon_time = fs.logon_time
    WHERE DATE(fs.updated_at) = CURRENT_DATE
      AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
      AND f.id IS NULL
    """

    sql_open_entries = """
    SELECT COUNT(DISTINCT fs.id)
    FROM flight_summaries fs
    JOIN flight_sector_occupancy fso ON fso.callsign = fs.callsign
    WHERE DATE(fs.updated_at) = CURRENT_DATE
      AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
      AND fso.exit_timestamp IS NULL
    """

    sql_overlapping = """
    SELECT COUNT(DISTINCT fs.id)
    FROM flight_summaries fs
    JOIN flight_sector_occupancy fso ON fso.callsign = fs.callsign
      AND fso.exit_timestamp IS NOT NULL
    WHERE DATE(fs.updated_at) = CURRENT_DATE
      AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
      AND NOT (fso.exit_timestamp < fs.logon_time OR fso.entry_timestamp > fs.completion_time)
    """

    sql_short = """
    SELECT COUNT(DISTINCT fs.id)
    FROM flight_summaries fs
    JOIN flight_sector_occupancy fso ON fso.callsign = fs.callsign
      AND fso.exit_timestamp IS NOT NULL
    WHERE DATE(fs.updated_at) = CURRENT_DATE
      AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
      AND fso.duration_seconds < 60
    """

    with eng.connect() as conn:
        total = conn.execute(text(sql_total)).scalar() or 0
        no_flights = conn.execute(text(sql_no_flights)).scalar() or 0
        open_entries = conn.execute(text(sql_open_entries)).scalar() or 0
        overlapping = conn.execute(text(sql_overlapping)).scalar() or 0
        short = conn.execute(text(sql_short)).scalar() or 0

        print(f"total_missing_sector_breakdown_today: {total}")
        print(f"no_flight_records: {no_flights}")
        print(f"has_open_sector_entries: {open_entries}")
        print(f"has_overlapping_occupancy_records: {overlapping}")
        print(f"has_short_occupancy_records(<60s): {short}")


if __name__ == '__main__':
    main()

