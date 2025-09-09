#!/usr/bin/env python3
"""Show flight_sector_occupancy entries for today."""
from app.database import _get_engine
from sqlalchemy import text

def main():
    eng = _get_engine()
    with eng.connect() as conn:
        # Get today's sector occupancy entries
        res = conn.execute(text("""
            SELECT 
                callsign,
                sector_name,
                entry_timestamp,
                exit_timestamp,
                duration_seconds,
                entry_lat,
                entry_lon,
                exit_lat,
                exit_lon,
                entry_altitude,
                exit_altitude,
                CASE 
                    WHEN exit_timestamp IS NULL THEN 'OPEN'
                    ELSE 'CLOSED'
                END as status
            FROM flight_sector_occupancy 
            WHERE DATE(entry_timestamp) = CURRENT_DATE
            ORDER BY entry_timestamp DESC
            LIMIT 50
        """))
        
        rows = res.fetchall()
        print(f"Today's sector occupancy entries: {len(rows)}")
        print()
        
        for row in rows:
            duration_min = row.duration_seconds / 60 if row.duration_seconds else 0
            print(f"{row.callsign} | {row.sector_name} | {row.status}")
            print(f"  Entry: {row.entry_timestamp} @ {row.entry_lat:.3f},{row.entry_lon:.3f} alt:{row.entry_altitude}")
            if row.exit_timestamp:
                print(f"  Exit:  {row.exit_timestamp} @ {row.exit_lat:.3f},{row.exit_lon:.3f} alt:{row.exit_altitude}")
                print(f"  Duration: {duration_min:.1f} minutes")
            else:
                print(f"  Duration: {duration_min:.1f} minutes (still open)")
            print()

if __name__ == '__main__':
    main()

