#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect('postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data')
cur = conn.cursor()

# Check QFA7 sector entries
cur.execute("""
    SELECT callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds 
    FROM flight_sector_occupancy 
    WHERE callsign = 'QFA7' 
    ORDER BY entry_timestamp DESC LIMIT 10
""")

rows = cur.fetchall()
print('QFA7 sector entries:')
for row in rows:
    print(f'{row[0]} -> {row[1]} at {row[2]}, exit: {row[3]}, duration: {row[4]}s')

conn.close()
