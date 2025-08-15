#!/usr/bin/env python3
"""
Query script to show all flights without origin (departure) in tabulated format
"""

import asyncio
import sys
import os

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
            elif isinstance(value, (int, float)) and value == 0:
                value = "0"
            data_row += f" {str(value):<{col_widths[i]}}|"
        print(data_row)
    
    print("=" * (sum(col_widths) + len(headers) + 1))

async def query_flights_no_origin():
    """Query all flights without origin (departure) and above 1000ft altitude"""
    try:
        async with get_database_session() as session:
            
            # Get total count of all flights
            result = await session.execute(text("SELECT COUNT(*) FROM flights"))
            total_flights = result.scalar()
            
            # Get count of flights without departure (all altitudes)
            result = await session.execute(text("""
                SELECT COUNT(*) FROM flights 
                WHERE departure IS NULL OR departure = ''
            """))
            flights_no_departure = result.scalar()
            
            # Get count of flights without departure and above 1000ft
            result = await session.execute(text("""
                SELECT COUNT(*) FROM flights 
                WHERE (departure IS NULL OR departure = '')
                AND altitude >= 1000
            """))
            flights_no_departure_above_1000ft = result.scalar()
            
            # Check flight summary table
            result = await session.execute(text("SELECT COUNT(*) FROM flight_summaries"))
            total_flight_summaries = result.scalar()
            
            result = await session.execute(text("""
                SELECT COUNT(*) FROM flight_summaries 
                WHERE departure IS NULL OR departure = ''
            """))
            flight_summaries_no_departure = result.scalar()
            
            # Calculate percentages
            percentage_all_altitudes = (flights_no_departure / total_flights * 100) if total_flights > 0 else 0
            percentage_above_1000ft = (flights_no_departure_above_1000ft / total_flights * 100) if total_flights > 0 else 0
            percentage_flight_summaries = (flight_summaries_no_departure / total_flight_summaries * 100) if total_flight_summaries > 0 else 0
            
            print("="*120)
            print("FLIGHT ORIGIN/DESTINATION ANALYSIS")
            print("="*120)
            print(f"Total flights in database: {total_flights:,}")
            print(f"Flights without departure (all altitudes): {flights_no_departure:,} ({percentage_all_altitudes:.1f}%)")
            print(f"Flights without departure (above 1000ft): {flights_no_departure_above_1000ft:,} ({percentage_above_1000ft:.1f}%)")
            print("="*120)
            print(f"Total flight summaries: {total_flight_summaries:,}")
            print(f"Flight summaries without departure: {flight_summaries_no_departure:,} ({percentage_flight_summaries:.1f}%)")
            print("="*120)
            
            # Get flight summaries without departure to analyze altitude changes
            result = await session.execute(text("""
                SELECT 
                    callsign,
                    departure,
                    arrival,
                    aircraft_type,
                    server,
                    pilot_rating,
                    time_online_minutes,
                    total_enroute_sectors,
                    total_enroute_time_minutes,
                    TO_CHAR(completion_time, 'YYYY-MM-DD HH24:MI:SS') as completion_time,
                    name
                FROM flight_summaries 
                WHERE departure IS NULL OR departure = ''
                ORDER BY completion_time DESC
            """))
            
            summary_rows = result.fetchall()
            
            # Analyze altitude changes for each flight summary using the flights table
            no_altitude_change_count = 0
            summary_rows_no_alt_change = []
            
            for row in summary_rows:
                callsign = row[0]
                
                # Check altitude changes for this callsign in the flights table
                result = await session.execute(text("""
                    SELECT MIN(altitude) as min_alt, MAX(altitude) as max_alt, COUNT(DISTINCT altitude) as unique_altitudes
                    FROM flights 
                    WHERE callsign = :callsign
                    AND altitude IS NOT NULL
                """), {'callsign': callsign})
                
                alt_data = result.fetchone()
                if alt_data:
                    min_alt, max_alt, unique_altitudes = alt_data
                    
                    # If there's only one unique altitude or no altitude data, consider it no altitude change
                    if unique_altitudes <= 1 or min_alt == max_alt:
                        no_altitude_change_count += 1
                        summary_rows_no_alt_change.append(row)
            
            print(f"Flight summaries without departure AND no altitude change: {no_altitude_change_count:,}")
            print(f"Percentage of no-departure summaries with no altitude change: {(no_altitude_change_count / flight_summaries_no_departure * 100) if flight_summaries_no_departure > 0 else 0:.1f}%")
            print("="*120)
            
            if summary_rows_no_alt_change:
                headers = ["Callsign", "Departure", "Arrival", "Aircraft", "Server", "Rating", "Time Online", "Sectors", "Enroute Time", "Completion Time", "Pilot"]
                format_table(headers, summary_rows_no_alt_change, "FLIGHT SUMMARIES WITHOUT ORIGIN AND NO ALTITUDE CHANGE")
                
                # Summary statistics for flight summaries with no altitude change
                print("\nFLIGHT SUMMARY STATISTICS (NO ALTITUDE CHANGE):")
                print("-" * 60)
                
                # Count by server
                servers = {}
                for row in summary_rows_no_alt_change:
                    server = row[4] or "Unknown"
                    servers[server] = servers.get(server, 0) + 1
                
                print("Flight Summaries by Server:")
                for server, count in sorted(servers.items()):
                    print(f"  {server}: {count}")
                
                # Count by aircraft type
                aircraft = {}
                for row in summary_rows_no_alt_change:
                    ac_type = row[3] or "Unknown"
                    aircraft[ac_type] = aircraft.get(ac_type, 0) + 1
                
                print("\nFlight Summaries by Aircraft Type:")
                for ac_type, count in sorted(aircraft.items()):
                    print(f"  {ac_type}: {count}")
                
                # Count by pilot rating
                ratings = {}
                for row in summary_rows_no_alt_change:
                    rating = str(row[5]) if row[5] is not None else "Unknown"
                    ratings[rating] = ratings.get(rating, 0) + 1
                
                print("\nFlight Summaries by Pilot Rating:")
                for rating, count in sorted(ratings.items()):
                    print(f"  {rating}: {count}")
                
                # Time online distribution
                time_ranges = {
                    "0-30 min": 0,
                    "30-60 min": 0,
                    "1-2 hours": 0,
                    "2+ hours": 0
                }
                
                for row in summary_rows_no_alt_change:
                    time_online = row[6] if row[6] is not None else 0
                    if time_online <= 30:
                        time_ranges["0-30 min"] += 1
                    elif time_online <= 60:
                        time_ranges["30-60 min"] += 1
                    elif time_online <= 120:
                        time_ranges["1-2 hours"] += 1
                    else:
                        time_ranges["2+ hours"] += 1
                
                print("\nTime Online Distribution:")
                for range_name, count in time_ranges.items():
                    if count > 0:
                        print(f"  {range_name}: {count}")
                
            else:
                print("No flight summaries found without departure and no altitude change")
            
            print("\n" + "="*120)
            
            if summary_rows:
                headers = ["Callsign", "Departure", "Arrival", "Aircraft", "Server", "Rating", "Time Online", "Sectors", "Enroute Time", "Completion Time", "Pilot"]
                format_table(headers, summary_rows, "ALL FLIGHT SUMMARIES WITHOUT ORIGIN")
                
                # Summary statistics for flight summaries
                print("\nFLIGHT SUMMARY STATISTICS:")
                print("-" * 50)
                
                # Count by server
                servers = {}
                for row in summary_rows:
                    server = row[4] or "Unknown"
                    servers[server] = servers.get(server, 0) + 1
                
                print("Flight Summaries by Server:")
                for server, count in sorted(servers.items()):
                    print(f"  {server}: {count}")
                
                # Count by aircraft type
                aircraft = {}
                for row in summary_rows:
                    ac_type = row[3] or "Unknown"
                    aircraft[ac_type] = aircraft.get(ac_type, 0) + 1
                
                print("\nFlight Summaries by Aircraft Type:")
                for ac_type, count in sorted(aircraft.items()):
                    print(f"  {ac_type}: {count}")
                
                # Count by pilot rating
                ratings = {}
                for row in summary_rows:
                    rating = str(row[5]) if row[5] is not None else "Unknown"
                    ratings[rating] = ratings.get(rating, 0) + 1
                
                print("\nFlight Summaries by Pilot Rating:")
                for rating, count in sorted(ratings.items()):
                    print(f"  {rating}: {count}")
                
                # Time online distribution
                time_ranges = {
                    "0-30 min": 0,
                    "30-60 min": 0,
                    "1-2 hours": 0,
                    "2+ hours": 0
                }
                
                for row in summary_rows:
                    time_online = row[6] if row[6] is not None else 0
                    if time_online <= 30:
                        time_ranges["0-30 min"] += 1
                    elif time_online <= 60:
                        time_ranges["30-60 min"] += 1
                    elif time_online <= 120:
                        time_ranges["1-2 hours"] += 1
                    else:
                        time_ranges["2+ hours"] += 1
                
                print("\nTime Online Distribution:")
                for range_name, count in time_ranges.items():
                    if count > 0:
                        print(f"  {range_name}: {count}")
                
            else:
                print("No flight summaries found without departure")
            
            print("\n" + "="*120)
            
            # Get all flights without departure and above 1000ft
            result = await session.execute(text("""
                SELECT 
                    callsign,
                    departure,
                    arrival,
                    aircraft_type,
                    latitude,
                    longitude,
                    altitude,
                    groundspeed,
                    TO_CHAR(last_updated, 'HH24:MI:SS') as time,
                    server,
                    name,
                    pilot_rating
                FROM flights 
                WHERE (departure IS NULL OR departure = '')
                AND altitude >= 1000
                ORDER BY last_updated DESC
            """))
            
            rows = result.fetchall()
            
            if rows:
                headers = ["Callsign", "Departure", "Arrival", "Aircraft", "Lat", "Lon", "Alt", "Speed", "Time", "Server", "Pilot", "Rating"]
                format_table(headers, rows, "FLIGHTS WITHOUT ORIGIN (ABOVE 1000FT)")
                
                # Summary statistics
                print("\nSUMMARY STATISTICS:")
                print("-" * 50)
                
                # Count by server
                servers = {}
                for row in rows:
                    server = row[9] or "Unknown"
                    servers[server] = servers.get(server, 0) + 1
                
                print("Flights by Server:")
                for server, count in sorted(servers.items()):
                    print(f"  {server}: {count}")
                
                # Count by aircraft type
                aircraft = {}
                for row in rows:
                    ac_type = row[3] or "Unknown"
                    aircraft[ac_type] = aircraft.get(ac_type, 0) + 1
                
                print("\nFlights by Aircraft Type:")
                for ac_type, count in sorted(aircraft.items()):
                    print(f"  {ac_type}: {count}")
                
                # Count by pilot rating
                ratings = {}
                for row in rows:
                    rating = str(row[11]) if row[11] is not None else "Unknown"
                    ratings[rating] = ratings.get(rating, 0) + 1
                
                print("\nFlights by Pilot Rating:")
                for rating, count in sorted(ratings.items()):
                    print(f"  {rating}: {count}")
                
                # Altitude distribution
                altitude_ranges = {
                    "1000-5000ft": 0,
                    "5000-10000ft": 0,
                    "10000-20000ft": 0,
                    "20000-30000ft": 0,
                    "30000ft+": 0
                }
                
                for row in rows:
                    alt = row[6] if row[6] is not None else 0
                    if 1000 <= alt < 5000:
                        altitude_ranges["1000-5000ft"] += 1
                    elif 5000 <= alt < 10000:
                        altitude_ranges["5000-10000ft"] += 1
                    elif 10000 <= alt < 20000:
                        altitude_ranges["10000-20000ft"] += 1
                    elif 20000 <= alt < 30000:
                        altitude_ranges["20000-30000ft"] += 1
                    elif alt >= 30000:
                        altitude_ranges["30000ft+"] += 1
                
                print("\nAltitude Distribution:")
                for range_name, count in altitude_ranges.items():
                    if count > 0:
                        print(f"  {range_name}: {count}")
                
            else:
                print("No flights found without departure and above 1000ft")
            
            print("\n" + "="*120)
            
    except Exception as e:
        print(f"Error querying database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(query_flights_no_origin())
