#!/usr/bin/env python3
import sys
sys.path.append('/app')
from app.services.vatsim_service import VATSIMService
from dataclasses import asdict
import asyncio

async def debug_flight_dict():
    # Get a flight with flight plan from VATSIM
    vatsim_service = VATSIMService()
    vatsim_data = await vatsim_service.get_current_data()
    
    # Find a flight with flight plan data
    test_flight = None
    for flight in vatsim_data.flights:
        if flight.flight_rules:
            test_flight = flight
            break
    
    if not test_flight:
        print('No flights with flight plan found')
        return
        
    print(f'=== ANALYZING FLIGHT DICT: {test_flight.callsign} ===')
    
    # Convert to dict
    flight_dict = asdict(test_flight)
    
    print('All flight_dict keys:')
    for key, value in flight_dict.items():
        print(f'  {key}: {type(value)} = {value}')
    
    # Check Flight model fields
    from app.models import Flight
    print('\n=== FLIGHT MODEL COLUMNS ===')
    for column in Flight.__table__.columns:
        print(f'  {column.name}: {column.type}')
        if column.name not in flight_dict:
            print(f'    -> MISSING in flight_dict')
        else:
            print(f'    -> Present: {type(flight_dict[column.name])}')

if __name__ == "__main__":
    asyncio.run(debug_flight_dict())

