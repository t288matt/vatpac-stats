#!/usr/bin/env python3
"""
Test rebuilding a single flight
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from rebuild_sector_occupancy import SectorOccupancyRebuilder

async def test_single_flight():
    """Test rebuilding a single flight"""
    
    db_url = "postgresql+asyncpg://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
    geojson_path = os.path.join(os.path.dirname(__file__), "config", "australian_airspace_sectors.geojson")
    
    rebuilder = SectorOccupancyRebuilder(db_url, geojson_path)
    
    # Test with ETD77
    callsign = "ETD77"
    cid = 1957450
    completion_time = datetime(2025, 10, 13, 20, 16, 41, tzinfo=timezone.utc)
    
    print(f"Testing rebuild for {callsign} (CID: {cid})")
    
    # Check data coverage first
    coverage = await rebuilder.analyze_data_coverage(callsign, cid, completion_time)
    print(f"Data coverage: {coverage}")
    
    # Try to rebuild
    result = await rebuilder.rebuild_flight_sectors(callsign, cid, completion_time)
    
    if result:
        print(f"Success! Created {len(result)} sector records")
        for record in result[:3]:  # Show first 3 records
            print(f"  - {record['sector_name']}: {record['entry_timestamp']} to {record['exit_timestamp']}")
    else:
        print("No sector records created")

if __name__ == "__main__":
    asyncio.run(test_single_flight())



