#!/usr/bin/env python3
"""
Query script to show all sector occupancy records for QFA91
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_database_session
from sqlalchemy import text

async def query_jst721_sectors():
    """Query all sector occupancy records for JST721"""
    try:
        async with get_database_session() as session:
            
            print("="*100)
            print("JST721 - ALL SECTOR OCCUPANCY RECORDS")
            print("="*100)
            
            result = await session.execute(text("""
                SELECT 
                    callsign,
                    TO_CHAR(entry_timestamp, 'YYYY-MM-DD HH24:MI:SS') as entry_time,
                    TO_CHAR(exit_timestamp, 'YYYY-MM-DD HH24:MI:SS') as exit_time,
                    sector_name,
                    duration_seconds,
                    entry_altitude,
                    exit_altitude,
                    CASE 
                        WHEN exit_timestamp IS NULL THEN 'ACTIVE'
                        ELSE 'COMPLETED'
                    END as status
                FROM flight_sector_occupancy 
                WHERE callsign = 'JST721'
                ORDER BY entry_timestamp DESC
            """))
            
            rows = result.fetchall()
            
            if rows:
                print(f"Found {len(rows)} sector occupancy records for JST721")
                print("\n" + "="*100)
                
                # Print header
                print(f"{'Entry Time':<20} {'Exit Time':<20} {'Sector':<8} {'Duration(s)':<12} {'Entry Alt':<10} {'Exit Alt':<10} {'Status':<10}")
                print("-" * 100)
                
                for row in rows:
                    callsign = row[0]
                    entry_time = row[1] if row[1] else "N/A"
                    exit_time = row[2] if row[2] else "N/A"
                    sector = row[3] if row[3] else "N/A"
                    duration = row[4] if row[4] else "N/A"
                    entry_alt = row[5] if row[5] else "N/A"
                    exit_alt = row[6] if row[6] else "N/A"
                    status = row[7]
                    
                    print(f"{entry_time:<20} {exit_time:<20} {sector:<8} {duration:<12} {entry_alt:<10} {exit_alt:<10} {status:<10}")
                
                print("\n" + "="*100)
                
                # Summary statistics
                print("\nSUMMARY STATISTICS:")
                print("-" * 50)
                
                # Count active vs completed
                active_count = sum(1 for row in rows if row[7] == 'ACTIVE')
                completed_count = sum(1 for row in rows if row[7] == 'COMPLETED')
                
                print(f"Total records: {len(rows)}")
                print(f"Active sectors: {active_count}")
                print(f"Completed sectors: {completed_count}")
                
                # Total time in sectors
                total_duration = sum(row[4] for row in rows if row[4] is not None)
                print(f"Total time in sectors: {total_duration} seconds ({total_duration/60:.1f} minutes)")
                
                # Unique sectors visited
                unique_sectors = set(row[3] for row in rows if row[3])
                print(f"Unique sectors visited: {', '.join(sorted(unique_sectors))}")
                
                # Current position (if active)
                active_sectors = [row for row in rows if row[7] == 'ACTIVE']
                if active_sectors:
                    print(f"\nCurrently in sector: {active_sectors[0][3]} (since {active_sectors[0][1]})")
                    print(f"Entry altitude: {active_sectors[0][5]}ft")
                else:
                    print("\nNo active sectors - flight completed")
                
            else:
                print("No sector occupancy records found for JST721")
            
            print("\n" + "="*100)
            
    except Exception as e:
        print(f"Error querying database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(query_jst721_sectors())
