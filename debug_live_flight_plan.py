#!/usr/bin/env python3
import sys
sys.path.append('/app')
from app.services.data_service import DataService
import asyncio

async def debug_live_flight_plan():
    data_service = DataService()
    
    print('=== CHECKING LIVE FLIGHT DATA IN CACHE ===')
    
    # Check cached flight data
    cache_items = list(data_service.cache['flights'].items())
    print(f'Flights in cache: {len(cache_items)}')
    
    if cache_items:
        # Check first few cached flights
        for i, (key, flight_data) in enumerate(cache_items[:3]):
            print(f'\nCached flight {i+1}: {key}')
            print(f'  callsign: {flight_data.get("callsign", "N/A")}')
            print(f'  departure: {flight_data.get("departure", "N/A")}')
            print(f'  arrival: {flight_data.get("arrival", "N/A")}')
            print(f'  Individual flight plan fields: departure={flight_data.get("departure")}, arrival={flight_data.get("arrival")}, route={flight_data.get("route")}')
            
            # Check individual flight plan fields
            print(f'  flight_rules: {flight_data.get("flight_rules")}')
            print(f'  aircraft_faa: {flight_data.get("aircraft_faa")}')
            print(f'  remarks: {flight_data.get("remarks", "")[:50] if flight_data.get("remarks") else None}...')

if __name__ == "__main__":
    asyncio.run(debug_live_flight_plan())

