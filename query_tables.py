#!/usr/bin/env python3
"""
Query script to show last 20 records from each table with timestamps in table format
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_database_session
from sqlalchemy import text

def format_table(headers, rows, title):
    """Format data as a table with proper column alignment"""
    if not rows:
        print(f"{title}\nNo data found")
        return
    
    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(header)
        for row in rows:
            if row[i] is not None:
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)  # Add padding
    
    # Print title
    print(f"\n{title}")
    print("=" * (sum(col_widths) + len(headers) + 1))
    
    # Print headers
    header_row = "|"
    for i, header in enumerate(headers):
        header_row += f" {header:<{col_widths[i]}}|"
    print(header_row)
    
    # Print separator
    separator = "+"
    for width in col_widths:
        separator += "-" * (width + 1) + "+"
    print(separator)
    
    # Print data rows
    for row in rows:
        data_row = "|"
        for i, value in enumerate(row):
            if value is None:
                value = "N/A"
            elif isinstance(value, datetime):
                value = value.strftime("%H:%M:%S")
            data_row += f" {str(value):<{col_widths[i]}}|"
        print(data_row)
    
    print("=" * (sum(col_widths) + len(headers) + 1))

async def query_all_tables():
    """Query the last 20 records from each table with timestamps in table format"""
    try:
        async with get_database_session() as session:
            
            # FLIGHTS TABLE
            print("\n" + "="*100)
            print("FLIGHTS TABLE (Last 20 records)")
            print("="*100)
            
            result = await session.execute(text("""
                SELECT callsign, 
                       TO_CHAR(last_updated, 'HH24:MI:SS') as time,
                       TO_CHAR(last_updated_api, 'HH24:MI:SS') as api_time,
                       departure, arrival, aircraft_type, 
                       latitude, longitude, altitude, groundspeed
                FROM flights 
                ORDER BY last_updated DESC 
                LIMIT 20
            """))
            
            rows = result.fetchall()
            if rows:
                headers = ["Callsign", "Time", "API", "Departure", "Arrival", "Aircraft", "Lat", "Lon", "Alt(ft)", "Speed(kts)"]
                format_table(headers, rows, "FLIGHTS TABLE")
            else:
                print("No flights found")
            
            # CONTROLLERS TABLE
            print("\n" + "="*100)
            print("CONTROLLERS TABLE (Last 20 records)")
            print("="*100)
            
            result = await session.execute(text("""
                SELECT callsign, 
                       TO_CHAR(last_updated, 'HH24:MI:SS') as time,
                       TO_CHAR(logon_time, 'HH24:MI:SS') as logon,
                       facility, rating, name, server
                FROM controllers 
                ORDER BY last_updated DESC NULLS LAST
                LIMIT 20
            """))
            
            rows = result.fetchall()
            if rows:
                headers = ["Callsign", "Time", "Logon", "Facility", "Rating", "Name", "Server"]
                format_table(headers, rows, "CONTROLLERS TABLE")
            else:
                print("No controllers found")
            
            # TRANSCEIVERS TABLE
            print("\n" + "="*100)
            print("TRANSCEIVERS TABLE (Last 20 records)")
            print("="*100)
            
            result = await session.execute(text("""
                SELECT callsign, 
                       TO_CHAR(timestamp, 'HH24:MI:SS') as time,
                       frequency, entity_type, 
                       ROUND(position_lat::numeric, 4) as lat,
                       ROUND(position_lon::numeric, 4) as lon
                FROM transceivers 
                ORDER BY timestamp DESC 
                LIMIT 20
            """))
            
            rows = result.fetchall()
            if rows:
                headers = ["Callsign", "Time", "Frequency(Hz)", "Type", "Lat", "Lon"]
                format_table(headers, rows, "TRANSCEIVERS TABLE")
            else:
                print("No transceivers found")
            
            # FLIGHT SUMMARIES TABLE
            print("\n" + "="*100)
            print("FLIGHT SUMMARIES TABLE (Last 20 records)")
            print("="*100)
            
            result = await session.execute(text("""
                SELECT callsign, 
                       TO_CHAR(created_at, 'HH24:MI:SS') as created,
                       TO_CHAR(completion_time, 'HH24:MI:SS') as completed,
                       departure, arrival, aircraft_type, time_online_minutes
                FROM flight_summaries 
                ORDER BY created_at DESC 
                LIMIT 20
            """))
            
            rows = result.fetchall()
            if rows:
                headers = ["Callsign", "Created", "Completed", "Departure", "Arrival", "Aircraft", "Time(min)"]
                format_table(headers, rows, "FLIGHT SUMMARIES TABLE")
            else:
                print("No flight summaries found")
            
            # FLIGHT SECTOR OCCUPANCY TABLE
            print("\n" + "="*100)
            print("FLIGHT SECTOR OCCUPANCY TABLE (Last 20 records)")
            print("="*100)
            
            result = await session.execute(text("""
                SELECT callsign, 
                       TO_CHAR(entry_timestamp, 'HH24:MI:SS') as entry,
                       TO_CHAR(exit_timestamp, 'HH24:MI:SS') as exit,
                       sector_name, 
                       duration_seconds,
                       entry_altitude, exit_altitude
                FROM flight_sector_occupancy 
                ORDER BY entry_timestamp DESC 
                LIMIT 20
            """))
            
            rows = result.fetchall()
            if rows:
                headers = ["Callsign", "Entry", "Exit", "Sector", "Duration(s)", "Entry Alt", "Exit Alt"]
                format_table(headers, rows, "FLIGHT SECTOR OCCUPANCY TABLE")
            else:
                print("No sector occupancy records found")
            
            print("\n" + "="*100)
            
    except Exception as e:
        print(f"Error querying database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(query_all_tables())
