#!/usr/bin/env python3
"""
Simple Data Flow Test

This test verifies that data is being written to the database in the last 40 seconds.
It's a basic yes/no check for each table.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import text


@pytest.mark.asyncio
async def test_data_written_in_last_40_seconds(db_session):
    """
    Simple test: Is data being written to the database in the last 40 seconds?
    
    This is a basic yes/no check for each table:
    - Flights table: Yes/No
    - Controllers table: Yes/No  
    - Transceivers table: Yes/No
    """
    # Calculate cutoff time (40 seconds ago)
    cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=40)
    
    # Simple yes/no check for each table
    flights_has_recent_data = db_session.execute(
        text("SELECT EXISTS(SELECT 1 FROM flights WHERE created_at >= :cutoff)"),
        {"cutoff": cutoff_time}
    ).scalar()
    
    controllers_has_recent_data = db_session.execute(
        text("SELECT EXISTS(SELECT 1 FROM controllers WHERE created_at >= :cutoff)"),
        {"cutoff": cutoff_time}
    ).scalar()
    
    transceivers_has_recent_data = db_session.execute(
        text("SELECT EXISTS(SELECT 1 FROM transceivers WHERE timestamp >= :cutoff)"),
        {"cutoff": cutoff_time}
    ).scalar()
    
    # Print results
    print(f"\nData written in last 40 seconds:")
    print(f"  Flights: {'Yes' if flights_has_recent_data else 'No'}")
    print(f"  Controllers: {'Yes' if controllers_has_recent_data else 'No'}")
    print(f"  Transceivers: {'Yes' if transceivers_has_recent_data else 'No'}")
    
    # Test passes if ANY table has recent data (data flow is working)
    any_recent_data = flights_has_recent_data or controllers_has_recent_data or transceivers_has_recent_data
    
    assert any_recent_data, "No data written to any table in the last 40 seconds"
    
    print(f"✓ Test passed: Data flow is working")
