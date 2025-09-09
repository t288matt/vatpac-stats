#!/usr/bin/env python3
"""Inspect flight_sector_occupancy for summaries missing sector_breakdown."""
from app.database import _get_engine
from sqlalchemy import text


def main():
    engine = _get_engine()

    # Find callsigns with missing sector_breakdown but with flights
    sql_calls = text('''
    SELECT fs.callsign, fs.cid, fs.logon_time, COUNT(f.id) AS flight_count
    FROM flight_summaries fs
    JOIN flights f ON f.callsign = fs.callsign
        AND f.cid = fs.cid
        AND f.departure = fs.departure
        AND f.arrival = fs.arrival
        AND f.logon_time = fs.logon_time
    WHERE DATE(fs.updated_at) = CURRENT_DATE
        AND (fs.sector_breakdown IS NULL OR fs.sector_breakdown = '{}'::jsonb)
    GROUP BY fs.callsign, fs.cid, fs.logon_time
    ORDER BY flight_count DESC
    LIMIT 10
    ''')

    with engine.connect() as conn:
        calls = conn.execute(sql_calls).fetchall()

        if not calls:
            print('No matching callsigns found')
            return

        for c in calls:
            callsign = c.callsign
            cid = c.cid
            logon = c.logon_time
            print('\n---')
            print(f'Callsign: {callsign}, cid: {cid}, logon_time: {logon}, flight_records: {c.flight_count}')

            sql_occ = text('''
            SELECT sector_name,
                   COUNT(*) AS entries,
                   COUNT(*) FILTER (WHERE exit_timestamp IS NULL) AS open_entries,
                   SUM(duration_seconds) AS total_seconds,
                   AVG(duration_seconds) AS avg_seconds
            FROM flight_sector_occupancy
            WHERE callsign = :callsign
            GROUP BY sector_name
            ORDER BY total_seconds DESC
            ''')

            occ = conn.execute(sql_occ, {'callsign': callsign}).fetchall()
            if not occ:
                print('  No sector occupancy records for this callsign')
            else:
                for row in occ:
                    print(f"  Sector: {row.sector_name}, entries: {row.entries}, open: {row.open_entries}, total_s: {row.total_seconds}, avg_s: {row.avg_seconds}")

            # Show some problematic rows with zero duration
            sql_zero = text('''
            SELECT id, sector_name, entry_timestamp, exit_timestamp, duration_seconds
            FROM flight_sector_occupancy
            WHERE callsign = :callsign
            ORDER BY entry_timestamp DESC
            LIMIT 10
            ''')
            rows = conn.execute(sql_zero, {'callsign': callsign}).fetchall()
            for r in rows:
                print(f"    row id={r.id}, sector={r.sector_name}, entry={r.entry_timestamp}, exit={r.exit_timestamp}, duration_s={r.duration_seconds}")

if __name__ == '__main__':
    main()


