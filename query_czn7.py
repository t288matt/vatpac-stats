#!/usr/bin/env python3
"""
Query script to find flight data for aircraft "czn7"
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_database_session
from sqlalchemy import text

async def query_czn7_flights():
    """Query the database for all flight data for aircraft 'czn7'"""
    try:
        async with get_database_session() as session:
            # Query for flights with callsign containing 'czn7' (case insensitive)
            result = await session.execute(
                text("""
                    SELECT 
                        callsign, cid, name, server, pilot_rating,
                        latitude, longitude, altitude, groundspeed, heading, transponder,
                        departure, arrival, aircraft_type, flight_rules, planned_altitude,
                        route, logon_time, last_updated, last_updated_api,
                        aircraft_faa, aircraft_short, alternate, cruise_tas, deptime,
                        enroute_time, fuel_time, remarks, revision_id, assigned_transponder,
                        military_rating, qnh_i_hg, qnh_mb
                    FROM flights 
                    WHERE callsign ILIKE :callsign 
                    ORDER BY last_updated DESC
                """),
                {"callsign": "%czn7%"}
            )
            
            rows = result.fetchall()
            print(f"Found {len(rows)} flights for aircraft containing 'czn7'")
            print("=" * 80)
            
            if not rows:
                print("No flight data found for aircraft 'czn7'")
                return
            
            # Get column names
            columns = result.keys()
            
            for i, row in enumerate(rows):
                print(f"\nFlight #{i+1}:")
                print("-" * 40)
                
                # Create a dictionary for easier reading
                flight_data = dict(zip(columns, row))
                
                # Print key flight information
                print(f"Callsign: {flight_data.get('callsign', 'N/A')}")
                print(f"Pilot: {flight_data.get('name', 'N/A')} (CID: {flight_data.get('cid', 'N/A')})")
                print(f"Server: {flight_data.get('server', 'N/A')}")
                print(f"Rating: {flight_data.get('pilot_rating', 'N/A')}")
                print(f"Aircraft: {flight_data.get('aircraft_type', 'N/A')} / {flight_data.get('aircraft_short', 'N/A')}")
                
                # Flight plan
                print(f"Route: {flight_data.get('departure', 'N/A')} → {flight_data.get('arrival', 'N/A')}")
                print(f"Planned Altitude: {flight_data.get('planned_altitude', 'N/A')}")
                print(f"Flight Rules: {flight_data.get('flight_rules', 'N/A')}")
                print(f"Route: {flight_data.get('route', 'N/A')}")
                
                # Position data
                if flight_data.get('latitude') and flight_data.get('longitude'):
                    print(f"Position: {flight_data.get('latitude', 'N/A')}, {flight_data.get('longitude', 'N/A')}")
                    print(f"Altitude: {flight_data.get('altitude', 'N/A')} ft")
                    print(f"Groundspeed: {flight_data.get('groundspeed', 'N/A')} kts")
                    print(f"Heading: {flight_data.get('heading', 'N/A')}°")
                
                # Timestamps
                print(f"Logon Time: {flight_data.get('logon_time', 'N/A')}")
                print(f"Last Updated: {flight_data.get('last_updated', 'N/A')}")
                print(f"API Last Updated: {flight_data.get('last_updated_api', 'N/A')}")
                
                # Additional details
                if flight_data.get('transponder'):
                    print(f"Transponder: {flight_data.get('transponder', 'N/A')}")
                if flight_data.get('alternate'):
                    print(f"Alternate: {flight_data.get('alternate', 'N/A')}")
                if flight_data.get('remarks'):
                    print(f"Remarks: {flight_data.get('remarks', 'N/A')}")
                
                print()
            
            # Summary statistics
            print("=" * 80)
            print("SUMMARY STATISTICS:")
            print(f"Total flights found: {len(rows)}")
            
            # Count unique callsigns
            unique_callsigns = set(row[0] for row in rows)
            print(f"Unique callsigns: {len(unique_callsigns)}")
            print(f"Callsigns: {', '.join(sorted(unique_callsigns))}")
            
            # Count by aircraft type
            aircraft_types = {}
            for row in rows:
                aircraft_type = row[13]  # aircraft_type column
                if aircraft_type:
                    aircraft_types[aircraft_type] = aircraft_types.get(aircraft_type, 0) + 1
            
            if aircraft_types:
                print("\nAircraft types:")
                for aircraft_type, count in sorted(aircraft_types.items()):
                    print(f"  {aircraft_type}: {count}")
            
            # Count by route
            routes = {}
            for row in rows:
                departure = row[11]  # departure column
                arrival = row[12]    # arrival column
                if departure and arrival:
                    route = f"{departure}-{arrival}"
                    routes[route] = routes.get(route, 0) + 1
            
            if routes:
                print("\nRoutes:")
                for route, count in sorted(routes.items()):
                    print(f"  {route}: {count}")
            
    except Exception as e:
        print(f"Error querying database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(query_czn7_flights())
