#!/usr/bin/env python3
import sys
sys.path.append('/app')
from app.services.data_service import DataService
from app.services.vatsim_service import VATSIMService
from dataclasses import asdict
import asyncio

async def debug_flight_plan_flow():
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
        
    print(f'=== TESTING FLIGHT: {test_flight.callsign} ===')
    
    # Simulate our data service processing
    flight_dict = asdict(test_flight)
    
    # Apply our flight plan consolidation logic (from data_service.py)
    print(f'flight_dict has individual flight plan fields:')
    print(f'  departure: {flight_dict.get("departure")}')
    print(f'  arrival: {flight_dict.get("arrival")}')
    print(f'  route: {flight_dict.get("route")}')
    
    # Now test what happens in the flush operation
    from app.models import Flight
    from sqlalchemy.dialects.postgresql import insert as postgresql_insert
    from app.database import SessionLocal
    
    print('\n=== TESTING POSTGRESQL INSERT ===')
    
    # Test the exact insert method used in _flush_memory_to_disk
    db = SessionLocal()
    try:
        stmt = postgresql_insert(Flight).values(**flight_dict)
        print(f'PostgreSQL insert statement created successfully')
        print(f'Insert values include individual fields: departure, arrival, route')
        
        # Execute the insert
        result = db.execute(stmt)
        db.commit()
        
        # Check what was actually saved
        saved_flight = db.query(Flight).filter(Flight.callsign == test_flight.callsign).order_by(Flight.id.desc()).first()
        if saved_flight:
            print(f'Saved flight found: {saved_flight.callsign}')
            print(f'Saved route: {saved_flight.route}')
            print(f'Saved departure: {saved_flight.departure}')
        else:
            print('No saved flight found')
            
    except Exception as e:
        print(f'ERROR in PostgreSQL insert: {e}')
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_flight_plan_flow())

