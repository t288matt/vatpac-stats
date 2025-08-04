#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append('/app')

from app.services.vatsim_service import VATSIMService

async def debug_flight_data():
    """Debug VATSIM flight data structure"""
    try:
        # Get VATSIM data
        vatsim_service = VATSIMService()
        data = await vatsim_service.get_current_data()
        
        print(f"VATSIM Flight Data Structure:")
        print(f"- Total flights: {len(data.flights)}")
        
        if data.flights:
            print(f"\nFirst 3 flights:")
            for i, flight in enumerate(data.flights[:3]):
                print(f"Flight {i+1}:")
                print(f"  - Callsign: {flight.callsign}")
                print(f"  - Aircraft Type: '{flight.aircraft_type}'")
                print(f"  - Departure: '{flight.departure}'")
                print(f"  - Arrival: '{flight.arrival}'")
                print(f"  - Route: '{flight.route}'")
                print(f"  - Altitude: {flight.altitude}")
                print(f"  - Speed: {flight.speed}")
                print(f"  - Position: {flight.position}")
                print(f"  - Full dict: {flight.__dict__}")
                print()
        
        # Check for flights with aircraft type data
        flights_with_aircraft = [f for f in data.flights if f.aircraft_type and f.aircraft_type.strip()]
        print(f"Flights with aircraft type data: {len(flights_with_aircraft)}")
        
        if flights_with_aircraft:
            print(f"\nSample flights with aircraft data:")
            for i, flight in enumerate(flights_with_aircraft[:3]):
                print(f"  {flight.callsign}: {flight.aircraft_type}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_flight_data()) 