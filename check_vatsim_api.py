#!/usr/bin/env python3
import asyncio
import httpx
import json

async def check_vatsim_api():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://data.vatsim.net/v3/vatsim-data.json')
        data = response.json()
        
        print('=== SAMPLE VATSIM API FLIGHTS ===')
        for i, pilot in enumerate(data['pilots'][:5]):
            print(f'Flight {i+1}: {pilot.get("callsign", "N/A")}')
            fp = pilot.get("flight_plan")
            print(f'  flight_plan type: {type(fp)}')
            if fp:
                print(f'  flight_plan.route: {fp.get("route", "N/A")[:50]}...')
            else:
                print(f'  flight_plan: None')
            print()
            
        # Count flights with and without flight plans
        total_flights = len(data['pilots'])
        flights_with_plans = sum(1 for p in data['pilots'] if p.get('flight_plan') is not None)
        flights_without_plans = total_flights - flights_with_plans
        
        print('=== FLIGHT PLAN STATISTICS ===')
        print(f'Total flights: {total_flights}')
        print(f'Flights with flight plans: {flights_with_plans}')
        print(f'Flights without flight plans: {flights_without_plans}')
        print(f'Percentage with plans: {flights_with_plans/total_flights*100:.1f}%')
        
        # Show a sample flight with a flight plan if any exist
        if flights_with_plans > 0:
            print('\n=== SAMPLE FLIGHT WITH PLAN ===')
            for pilot in data['pilots']:
                if pilot.get('flight_plan') is not None:
                    print(f'Callsign: {pilot.get("callsign")}')
                    print(f'Flight plan: {json.dumps(pilot.get("flight_plan"), indent=2)}')
                    break

if __name__ == "__main__":
    asyncio.run(check_vatsim_api())

