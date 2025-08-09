#!/usr/bin/env python3
import sys
sys.path.append('/app')
from app.services.vatsim_service import VATSIMService
from dataclasses import asdict
import asyncio

async def trace_qtr359():
    print('=== TRACING QTR359 FROM API TO DATABASE ===')
    
    # Step 1: Get raw VATSIM API data
    vatsim_service = VATSIMService()
    vatsim_data = await vatsim_service.get_current_data()
    
    # Find QTR359 in the data
    qtr359_flight = None
    for flight in vatsim_data.flights:
        if flight.callsign == 'QTR359':
            qtr359_flight = flight
            break
    
    if not qtr359_flight:
        print('QTR359 not found in current VATSIM data')
        return
    
    print(f'STEP 1: Found QTR359 in VATSIM API data')
    print(f'  callsign: {qtr359_flight.callsign}')
    print(f'  departure: {qtr359_flight.departure}')
    print(f'  arrival: {qtr359_flight.arrival}')
    print(f'  flight_rules: {qtr359_flight.flight_rules}')
    print(f'  aircraft_faa: {qtr359_flight.aircraft_faa}')
    print(f'  remarks: {qtr359_flight.remarks[:50] if qtr359_flight.remarks else None}...')
    
    # Step 2: Convert to dict (like _process_data_in_memory does)
    flight_dict = asdict(qtr359_flight)
    
    print(f'\nSTEP 2: After _process_data_in_memory processing')
    print(f'  Flight data processed with individual fields (no flight_plan field)')
    
    # Step 3: Check if it passes filters
    from app.filters.flight_filter import FlightFilter
    from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
    
    flight_filter = FlightFilter()
    geo_filter = GeographicBoundaryFilter()
    
    # Test airport filter
    airport_filtered = flight_filter.filter_flights_list([flight_dict])
    print(f'\nSTEP 3a: Airport filter')
    print(f'  Input: 1 flight (QTR359)')
    print(f'  Output: {len(airport_filtered)} flights')
    print(f'  Passed airport filter: {len(airport_filtered) > 0}')
    
    if len(airport_filtered) > 0:
        # Test geographic filter
        geo_filtered = geo_filter.filter_flights_list(airport_filtered)
        print(f'\nSTEP 3b: Geographic filter')
        print(f'  Input: {len(airport_filtered)} flights')
        print(f'  Output: {len(geo_filtered)} flights')
        print(f'  Passed geographic filter: {len(geo_filtered) > 0}')
        
        if len(geo_filtered) > 0:
            print(f'\nSTEP 4: QTR359 passed all filters and would be saved to database')
            filtered_flight = geo_filtered[0]
            print(f'  Has individual flight plan fields: departure={filtered_flight.get("departure")}, arrival={filtered_flight.get("arrival")}')
        else:
            print(f'\nSTEP 4: QTR359 FILTERED OUT by geographic filter')
    else:
        print(f'\nSTEP 4: QTR359 FILTERED OUT by airport filter')
    
    # Step 5: Check if it's in database
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        from app.models import Flight
        db_flight = db.query(Flight).filter(Flight.callsign == 'QTR359').order_by(Flight.last_updated.desc()).first()
        
        print(f'\nSTEP 5: Database check')
        if db_flight:
            print(f'  QTR359 found in database')
            print(f'  departure: {db_flight.departure}')
            print(f'  arrival: {db_flight.arrival}')
            print(f'  route: {db_flight.route}')
            print(f'  last_updated: {db_flight.last_updated}')
        else:
            print(f'  QTR359 NOT found in database')
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(trace_qtr359())

