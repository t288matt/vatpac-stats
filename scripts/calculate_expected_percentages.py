#!/usr/bin/env python3
"""
Script to calculate expected controller time percentages for flights with good data.
This will be used to compare with what the app generates after it starts.
"""

import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path for imports
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

from app.config import get_config

async def calculate_expected_percentages():
    """Calculate expected controller time percentages for flights with good data."""
    
    # Get database URL from config
    config = get_config()
    database_url = config.database.url
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        print("Calculating expected controller time percentages...")
        
        # Find flights with both flight and ATC transceiver data
        query = """
        SELECT DISTINCT f.callsign, f.departure, f.arrival, f.aircraft_type, 
               f.logon_time, f.last_updated,
               EXTRACT(EPOCH FROM (f.last_updated - f.logon_time))/60 as duration_minutes
        FROM flights f 
        WHERE EXISTS (SELECT 1 FROM transceivers t1 WHERE t1.callsign = f.callsign AND t1.entity_type = 'flight')
        AND EXISTS (SELECT 1 FROM transceivers t2 WHERE t2.callsign = f.callsign AND t2.entity_type = 'atc')
        AND f.logon_time IS NOT NULL 
        AND f.last_updated IS NOT NULL
        ORDER BY f.logon_time DESC
        LIMIT 20
        """
        
        result = await conn.execute(text(query))
        flights = result.fetchall()
        
        print(f"Found {len(flights)} flights with both flight and ATC data")
        print("=" * 80)
        
        # Store results for comparison
        expected_results = []
        
        for flight in flights:
            callsign = flight.callsign
            departure = flight.departure
            arrival = flight.arrival
            logon_time = flight.logon_time
            last_updated = flight.last_updated
            duration_minutes = flight.duration_minutes
            
            print(f"\nFlight: {callsign} ({departure} -> {arrival})")
            print(f"Duration: {duration_minutes:.2f} minutes")
            print(f"Period: {logon_time} to {last_updated}")
            
            # Get ATC interactions during flight time
            atc_query = f"""
            SELECT t.timestamp, t.frequency, t.position_lat, t.position_lon
            FROM transceivers t 
            WHERE t.callsign = '{callsign}'
            AND t.entity_type = 'atc'
            AND t.timestamp BETWEEN '{logon_time}' AND '{last_updated}'
            ORDER BY t.timestamp
            """
            
            atc_result = await conn.execute(text(atc_query))
            atc_interactions = atc_result.fetchall()
            
            if atc_interactions:
                first_atc = atc_interactions[0].timestamp
                last_atc = atc_interactions[-1].timestamp
                atc_duration = (last_atc - first_atc).total_seconds() / 60
                
                # Calculate controller time percentage
                controller_percentage = (atc_duration / duration_minutes) * 100
                
                print(f"ATC Interactions: {len(atc_interactions)} records")
                print(f"ATC Period: {first_atc} to {last_atc}")
                print(f"ATC Duration: {atc_duration:.2f} minutes")
                print(f"Expected Controller Time: {controller_percentage:.2f}%")
                
                # Check sector occupancy during ATC interactions
                sector_query = f"""
                SELECT fso.sector_name, fso.entry_timestamp, fso.exit_timestamp
                FROM flight_sector_occupancy fso
                WHERE fso.callsign = '{callsign}'
                AND (
                    (fso.entry_timestamp <= '{first_atc}' AND fso.exit_timestamp >= '{first_atc}') OR
                    (fso.entry_timestamp <= '{last_atc}' AND fso.exit_timestamp >= '{last_atc}') OR
                    (fso.entry_timestamp >= '{first_atc}' AND fso.exit_timestamp <= '{last_atc}')
                )
                ORDER BY fso.entry_timestamp
                """
                
                sector_result = await conn.execute(text(sector_query))
                sectors = sector_result.fetchall()
                
                if sectors:
                    print(f"Sectors during ATC: {[s.sector_name for s in sectors]}")
                    # Calculate airborne controller time
                    airborne_time = 0
                    for sector in sectors:
                        sector_start = max(sector.entry_timestamp, first_atc)
                        sector_end = min(sector.exit_timestamp, last_atc)
                        if sector_end > sector_start:
                            airborne_time += (sector_end - sector_start).total_seconds() / 60
                    
                    airborne_percentage = (airborne_time / atc_duration) * 100 if atc_duration > 0 else 0
                    print(f"Airborne during ATC: {airborne_time:.2f} minutes")
                    print(f"Expected Airborne Controller Time: {airborne_percentage:.2f}%")
                else:
                    print("Sectors during ATC: None (uncontrolled airspace)")
                    airborne_percentage = 0
                    print(f"Expected Airborne Controller Time: 0.00%")
                
                # Store results
                expected_results.append({
                    'callsign': callsign,
                    'departure': departure,
                    'arrival': arrival,
                    'duration_minutes': duration_minutes,
                    'atc_duration': atc_duration,
                    'expected_controller_percentage': controller_percentage,
                    'expected_airborne_percentage': airborne_percentage,
                    'atc_count': len(atc_interactions),
                    'sectors_during_atc': [s.sector_name for s in sectors] if sectors else []
                })
                
            else:
                print("No ATC interactions found during flight time")
                expected_results.append({
                    'callsign': callsign,
                    'departure': departure,
                    'arrival': arrival,
                    'duration_minutes': duration_minutes,
                    'atc_duration': 0,
                    'expected_controller_percentage': 0,
                    'expected_airborne_percentage': 0,
                    'atc_count': 0,
                    'sectors_during_atc': []
                })
            
            print("-" * 60)
        
        # Save results to a file for comparison
        print(f"\n{'='*80}")
        print("SUMMARY OF EXPECTED PERCENTAGES")
        print(f"{'='*80}")
        print(f"{'Callsign':<10} {'Route':<15} {'Duration':<10} {'ATC Time':<10} {'Ctrl%':<8} {'Airborne%':<12} {'Sectors':<20}")
        print(f"{'':<10} {'':<15} {'(min)':<10} {'(min)':<10} {'':<8} {'':<12} {'':<20}")
        print("-" * 80)
        
        for result in expected_results:
            sectors_str = ', '.join(result['sectors_during_atc']) if result['sectors_during_atc'] else 'None'
            print(f"{result['callsign']:<10} {result['departure']}-{result['arrival']:<15} "
                  f"{result['duration_minutes']:<10.1f} {result['atc_duration']:<10.1f} "
                  f"{result['expected_controller_percentage']:<8.1f} {result['expected_airborne_percentage']:<12.1f} "
                  f"{sectors_str:<20}")
        
        # Save detailed results to file
        with open('/app/expected_percentages.txt', 'w') as f:
            f.write("EXPECTED CONTROLLER TIME PERCENTAGES\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            
            for result in expected_results:
                f.write(f"Flight: {result['callsign']} ({result['departure']} -> {result['arrival']})\n")
                f.write(f"Duration: {result['duration_minutes']:.2f} minutes\n")
                f.write(f"ATC Duration: {result['atc_duration']:.2f} minutes\n")
                f.write(f"Expected Controller Time: {result['expected_controller_percentage']:.2f}%\n")
                f.write(f"Expected Airborne Controller Time: {result['expected_airborne_percentage']:.2f}%\n")
                f.write(f"Sectors during ATC: {', '.join(result['sectors_during_atc']) if result['sectors_during_atc'] else 'None'}\n")
                f.write("-" * 40 + "\n")
        
        print(f"\nDetailed results saved to: /app/expected_percentages.txt")
        print(f"Total flights analyzed: {len(expected_results)}")
    
    await engine.dispose()
    print("\nExpected percentages calculation completed!")

if __name__ == "__main__":
    asyncio.run(calculate_expected_percentages())
