#!/usr/bin/env python3
"""
Simple Data Flow Test

This test verifies that data is being written to the database in the last 40 seconds.
It shows the actual timestamps of the most recent data for each table.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add the app directory to the path so we can import modules
sys.path.insert(0, '/app')

from app.config import get_config
from app.database import AsyncSessionLocal


@pytest.mark.asyncio
async def test_data_written_in_last_40_seconds():
    """
    Enhanced test: Shows when data was last written to each table
    
    This provides detailed timing information for each table:
    - Flights table: Most recent timestamp
    - Controllers table: Most recent timestamp  
    - Transceivers table: Most recent timestamp
    """
    # Create database session
    async with AsyncSessionLocal() as session:
        # Calculate cutoff time (40 seconds ago) - ensure timezone-aware
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=40)
        
        print(f"DEBUG: Cutoff time: {cutoff_time} (type: {type(cutoff_time)})")
        
        # Get most recent timestamps for each table
        flights_latest = await session.execute(
            text("SELECT MAX(created_at) FROM flights"),
            {}
        )
        flights_latest = flights_latest.scalar()
        print(f"DEBUG: Flights latest: {flights_latest} (type: {type(flights_latest)})")
        
        controllers_latest = await session.execute(
            text("SELECT MAX(created_at) FROM controllers"),
            {}
        )
        controllers_latest = controllers_latest.scalar()
        print(f"DEBUG: Controllers latest: {controllers_latest} (type: {type(controllers_latest)})")
        
        transceivers_latest = await session.execute(
            text("SELECT MAX(timestamp) FROM transceivers"),
            {}
        )
        transceivers_latest = transceivers_latest.scalar()
        print(f"DEBUG: Transceivers latest: {transceivers_latest} (type: {type(transceivers_latest)})")
        
        # Ensure all timestamps are timezone-aware for comparison
        now = datetime.now(timezone.utc)
        
        # Convert database timestamps to timezone-aware if they aren't already
        if flights_latest:
            if flights_latest.tzinfo is None:
                flights_latest = flights_latest.replace(tzinfo=timezone.utc)
                print(f"DEBUG: Converted flights_latest to timezone-aware: {flights_latest}")
        
        if controllers_latest:
            if controllers_latest.tzinfo is None:
                controllers_latest = controllers_latest.replace(tzinfo=timezone.utc)
                print(f"DEBUG: Converted controllers_latest to timezone-aware: {controllers_latest}")
        
        if transceivers_latest:
            if transceivers_latest.tzinfo is None:
                transceivers_latest = transceivers_latest.replace(tzinfo=timezone.utc)
                print(f"DEBUG: Converted transceivers_latest to timezone-aware: {transceivers_latest}")
        
        # Check if data exists and is recent
        flights_has_recent_data = flights_latest and flights_latest >= cutoff_time
        controllers_has_recent_data = controllers_latest and controllers_latest >= cutoff_time
        transceivers_has_recent_data = transceivers_latest and transceivers_latest >= cutoff_time
        
        # Print detailed results
        print(f"\nData Flow Analysis (cutoff: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S UTC')}):")
        print(f"  Flights: {'✓' if flights_has_recent_data else '✗'} - Latest: {flights_latest.strftime('%Y-%m-%d %H:%M:%S UTC') if flights_latest else 'No data'}")
        print(f"  Controllers: {'✓' if controllers_has_recent_data else '✗'} - Latest: {controllers_latest.strftime('%Y-%m-%d %H:%M:%S UTC') if controllers_latest else 'No data'}")
        print(f"  Transceivers: {'✓' if transceivers_latest else '✗'} - Latest: {transceivers_latest.strftime('%Y-%m-%d %H:%M:%S UTC') if transceivers_latest else 'No data'}")
        
        # Calculate time differences for recent data
        if flights_latest and flights_has_recent_data:
            flights_age = (now - flights_latest).total_seconds()
            print(f"    → Flights data is {flights_age:.1f} seconds old")
        
        if controllers_latest and controllers_has_recent_data:
            controllers_age = (now - controllers_latest).total_seconds()
            print(f"    → Controllers data is {controllers_age:.1f} seconds old")
        
        if transceivers_latest and transceivers_has_recent_data:
            transceivers_age = (now - transceivers_latest).total_seconds()
            print(f"    → Transceivers data is {transceivers_age:.1f} seconds old")
        
        # Test passes if ANY table has recent data (data flow is working)
        any_recent_data = flights_has_recent_data or controllers_has_recent_data or transceivers_has_recent_data
        
        assert any_recent_data, "No data written to any table in the last 40 seconds"
        
        print(f"\n✓ Test passed: Data flow is working")
        print(f"  Total tables with recent data: {sum([flights_has_recent_data, controllers_has_recent_data, transceivers_has_recent_data])}/3")


# For manual testing outside of pytest
async def main():
    """Run the test manually to check data flow."""
    try:
        await test_data_written_in_last_40_seconds()
        print("\n✅ Data flow test completed successfully!")
    except Exception as e:
        print(f"\n❌ Data flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
