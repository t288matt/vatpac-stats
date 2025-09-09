#!/usr/bin/env python3
"""Check for open sector entries."""
from app.database import _get_engine
from sqlalchemy import text

def main():
    eng = _get_engine()
    with eng.connect() as conn:
        # Count open sectors
        res = conn.execute(text("SELECT COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NULL"))
        open_count = res.scalar()
        print(f"Open sectors: {open_count}")
        
        # Show some examples
        if open_count > 0:
            res = conn.execute(text("""
                SELECT callsign, sector_name, entry_timestamp, 
                       EXTRACT(EPOCH FROM (NOW() - entry_timestamp))/60 as minutes_open
                FROM flight_sector_occupancy 
                WHERE exit_timestamp IS NULL 
                ORDER BY entry_timestamp DESC 
                LIMIT 10
            """))
            print("\nRecent open sectors:")
            for row in res.fetchall():
                print(f"  {row.callsign} in {row.sector_name} for {row.minutes_open:.1f} minutes")

if __name__ == '__main__':
    main()
