#!/usr/bin/env python3
"""
Query script to find the sector with the highest amount of flight time
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_database_session
from sqlalchemy import text

async def query_highest_flight_time_sector():
    """Query to find the sector with the highest total flight time"""
    try:
        async with get_database_session() as session:
            
            print("="*100)
            print("SECTOR WITH HIGHEST TOTAL FLIGHT TIME")
            print("="*100)
            
            # Query to find sector with highest total flight time
            result = await session.execute(text("""
                SELECT 
                    sector_name,
                    SUM(duration_seconds) as total_flight_time_seconds,
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN exit_timestamp IS NOT NULL THEN 1 END) as completed_entries,
                    COUNT(CASE WHEN exit_timestamp IS NULL THEN 1 END) as active_entries,
                    AVG(duration_seconds) as avg_duration_seconds,
                    MIN(entry_timestamp) as first_entry,
                    MAX(entry_timestamp) as last_entry
                FROM flight_sector_occupancy 
                WHERE sector_name IS NOT NULL
                GROUP BY sector_name
                ORDER BY total_flight_time_seconds DESC
                LIMIT 10
            """))
            
            rows = result.fetchall()
            
            if rows:
                print(f"Found {len(rows)} sectors with flight time data")
                print("\n" + "="*100)
                
                # Print header
                print(f"{'Rank':<5} {'Sector':<8} {'Total Time (hrs)':<15} {'Total Time (min)':<15} {'Entries':<8} {'Completed':<10} {'Active':<8} {'Avg Duration':<12}")
                print("-" * 100)
                
                for i, row in enumerate(rows, 1):
                    sector = row[0] if row[0] else "N/A"
                    total_seconds = row[1] if row[1] else 0
                    total_entries = row[2] if row[2] else 0
                    completed_entries = row[3] if row[3] else 0
                    active_entries = row[4] if row[4] else 0
                    avg_duration = row[5] if row[5] else 0
                    
                    # Convert to hours and minutes
                    total_hours = total_seconds / 3600
                    total_minutes = total_seconds / 60
                    
                    print(f"{i:<5} {sector:<8} {total_hours:<15.2f} {total_minutes:<15.1f} {total_entries:<8} {completed_entries:<10} {active_entries:<8} {avg_duration:<12.1f}")
                
                print("\n" + "="*100)
                
                # Show the top sector in detail
                top_sector = rows[0]
                print(f"\n🏆 TOP SECTOR: {top_sector[0]}")
                print("-" * 50)
                print(f"Total flight time: {top_sector[1]:,} seconds ({top_sector[1]/3600:.2f} hours)")
                print(f"Total entries: {top_sector[2]:,}")
                print(f"Completed entries: {top_sector[3]:,}")
                print(f"Active entries: {top_sector[4]:,}")
                print(f"Average duration: {top_sector[5]:.1f} seconds ({top_sector[5]/60:.1f} minutes)")
                print(f"First entry: {top_sector[6]}")
                print(f"Last entry: {top_sector[7]}")
                
                # Additional statistics
                print(f"\n📊 ADDITIONAL STATISTICS:")
                print("-" * 50)
                
                # Total across all sectors
                total_all_sectors = sum(row[1] for row in rows if row[1])
                print(f"Total flight time across all sectors: {total_all_sectors:,} seconds ({total_all_sectors/3600:.2f} hours)")
                
                # Percentage of top sector
                if total_all_sectors > 0:
                    percentage = (top_sector[1] / total_all_sectors) * 100
                    print(f"Top sector percentage: {percentage:.1f}% of total flight time")
                
                # Show sectors with no active entries (fully completed)
                completed_only = [row for row in rows if row[4] == 0]
                if completed_only:
                    print(f"\n✅ Sectors with no active entries (fully completed): {len(completed_only)}")
                    for row in completed_only[:5]:  # Show first 5
                        print(f"  - {row[0]}: {row[1]/3600:.2f} hours")
                
                # Show sectors with active entries
                active_sectors = [row for row in rows if row[4] > 0]
                if active_sectors:
                    print(f"\n🔄 Sectors with active entries: {len(active_sectors)}")
                    for row in active_sectors[:5]:  # Show first 5
                        print(f"  - {row[0]}: {row[4]} active, {row[1]/3600:.2f} hours total")
                
            else:
                print("No sector occupancy data found in the database")
            
            print("\n" + "="*100)
            
    except Exception as e:
        print(f"Error querying database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(query_highest_flight_time_sector())






