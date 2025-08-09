#!/usr/bin/env python3
import sys
sys.path.append('/app')
from app.services.data_service import DataService
import asyncio

async def check_cache_data():
    data_service = DataService()
    
    print('=== CHECKING DATA SERVICE CACHE ===')
    
    # Check if there's any flight data in cache
    cache_items = list(data_service.cache['flights'].items())
    print(f'Flights in cache: {len(cache_items)}')
    
    if cache_items:
        # Check first few cached flights
        for i, (key, flight_data) in enumerate(cache_items[:3]):
            print(f'\nCached flight {i+1}: {key}')
            print(f'  callsign: {flight_data.get("callsign", "N/A")}')
            print(f'  Individual flight plan fields: departure={flight_data.get("departure")}, arrival={flight_data.get("arrival")}, route={flight_data.get("route")}')
                print(f'  Available keys: {list(flight_data.keys())}')

if __name__ == "__main__":
    asyncio.run(check_cache_data())

