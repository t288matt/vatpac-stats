#!/usr/bin/env python3
"""
Simple Data Flow Test

This test verifies that data is being written to the database in the last 40 seconds.
It shows the actual timestamps of the most recent data for each table.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import text


@pytest.mark.asyncio
async def test_data_written_in_last_40_seconds(db_session):
    """
    Enhanced test: Shows when data was last written to each table
    
    This provides detailed timing information for each table:
    - Flights table: Most recent timestamp
    - Controllers table: Most recent timestamp  
    - Transceivers table: Most recent timestamp
    """
    # Calculate cutoff time (40 seconds ago)
    cutoff_time = datetime.now() - timedelta(seconds=40)
    
    # Get most recent timestamps for each table
    flights_latest = db_session.execute(
        text("SELECT MAX(created_at) FROM flights"),
        {}
    ).scalar()
    
    controllers_latest = db_session.execute(
        text("SELECT MAX(created_at) FROM controllers"),
        {}
    ).scalar()
    
    transceivers_latest = db_session.execute(
        text("SELECT MAX(timestamp) FROM transceivers"),
        {}
    ).scalar()
    
    # Check if data exists and is recent
    flights_has_recent_data = flights_latest and flights_latest >= cutoff_time
    controllers_has_recent_data = controllers_latest and controllers_latest >= cutoff_time
    transceivers_has_recent_data = transceivers_latest and transceivers_latest >= cutoff_time
    
    # Print detailed results
    print(f"\nData Flow Analysis (cutoff: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}):")
    print(f"  Flights: {'✓' if flights_has_recent_data else '✗'} - Latest: {flights_latest.strftime('%Y-%m-%d %H:%M:%S') if flights_latest else 'No data'}")
    print(f"  Controllers: {'✓' if controllers_has_recent_data else '✗'} - Latest: {controllers_latest.strftime('%Y-%m-%d %H:%M:%S') if controllers_latest else 'No data'}")
    print(f"  Transceivers: {'✓' if transceivers_has_recent_data else '✗'} - Latest: {transceivers_latest.strftime('%Y-%m-%d %H:%M:%S') if transceivers_latest else 'No data'}")
    
    # Calculate time differences for recent data
    now = datetime.now()
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
