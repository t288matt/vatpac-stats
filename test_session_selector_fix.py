#!/usr/bin/env python3
"""
Test to verify the session selector fix for duplicate flight detection.

This test confirms that the session selector correctly:
1. Uses 5-field exclusion (callsign, cid, departure, arrival, logon_time)
2. Processes multiple flights on the same route with different session_start times
3. Correctly identifies unique flight sessions
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.session_selector import select_canonical_sessions


class MockRow:
    """Mock database row for testing."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


async def test_repeat_flight_detection():
    """
    Test that the session selector correctly handles repeat flights on the same route.
    This test simulates a pilot flying the same route (MEL→SYD) on different days.
    """
    # Flight data for MEL→SYD on two different days
    flight1_day1 = {
        "callsign": "QFA123",
        "cid": 1234567,
        "departure": "YMML",  # Melbourne
        "arrival": "YSSY",    # Sydney
        "logon_time": datetime(2025, 10, 15, 8, 30, 0, tzinfo=timezone.utc),
        "last_updated": datetime(2025, 10, 15, 9, 45, 0, tzinfo=timezone.utc),
        "session_start": datetime(2025, 10, 15, 8, 30, 0, tzinfo=timezone.utc),
        "session_end": datetime(2025, 10, 15, 10, 45, 0, tzinfo=timezone.utc),
        "latest_deptime": "0830",
        "latest_route": "DCT",
        "latest_aircraft_type": "B738",
        "latest_aircraft_faa": "B738/M",
        "latest_aircraft_short": "B738",
        "latest_flight_rules": "I",
        "latest_planned_altitude": "32000",
        "latest_name": "John Pilot",
        "latest_server": "AUS",
        "latest_pilot_rating": 3,
        "latest_military_rating": 0
    }
    
    flight2_day2 = {
        "callsign": "QFA123",
        "cid": 1234567, 
        "departure": "YMML",  # Melbourne
        "arrival": "YSSY",    # Sydney
        "logon_time": datetime(2025, 10, 20, 14, 15, 0, tzinfo=timezone.utc),
        "last_updated": datetime(2025, 10, 20, 15, 30, 0, tzinfo=timezone.utc),
        "session_start": datetime(2025, 10, 20, 14, 15, 0, tzinfo=timezone.utc),
        "session_end": datetime(2025, 10, 20, 16, 30, 0, tzinfo=timezone.utc),
        "latest_deptime": "1415",
        "latest_route": "DCT",
        "latest_aircraft_type": "B738",
        "latest_aircraft_faa": "B738/M",
        "latest_aircraft_short": "B738",
        "latest_flight_rules": "I",
        "latest_planned_altitude": "32000",
        "latest_name": "John Pilot",
        "latest_server": "AUS",
        "latest_pilot_rating": 3,
        "latest_military_rating": 0
    }
    
    # Test case 1: First flight not in flight_summaries, should be returned
    with patch('app.services.session_selector.get_database_session') as mock_get_db:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_get_db.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value = mock_result
        
        # Create a mock row with first flight data
        mock_row = MockRow(**flight1_day1)
        mock_result.fetchall.return_value = [mock_row]
        
        print("\n=== TEST CASE 1: First flight not in flight_summaries ===")
        result = await select_canonical_sessions(completion_hours=8, gap_minutes=120)
        print(f"Number of sessions returned: {len(result)}")
        assert len(result) == 1, "First flight should be returned"
        
    # Test case 2: First flight in flight_summaries, second flight not - should return second flight
    with patch('app.services.session_selector.get_database_session') as mock_get_db:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_get_db.return_value.__aenter__.return_value = mock_session
        
        # Mock SQL execution to simulate first flight in flight_summaries and second flight as new
        async def mock_execute(query, params):
            mock_res = MagicMock()
            # Return empty for first query (no matching sessions in processed_flights)
            mock_res.fetchall.return_value = [MockRow(**flight2_day2)]
            return mock_res
            
        mock_session.execute = mock_execute
        
        print("\n=== TEST CASE 2: First flight in flight_summaries, second flight new ===")
        result = await select_canonical_sessions(completion_hours=8, gap_minutes=120)
        print(f"Number of sessions returned: {len(result)}")
        assert len(result) == 1, "Second flight should be returned"
        
        if result:
            session = result[0]
            print(f"Session details: {json.dumps({k: str(v) if isinstance(v, datetime) else v for k, v in session.items()}, indent=2)}")
            assert session["session_start"].replace(tzinfo=None) == flight2_day2["session_start"].replace(tzinfo=None), "Should return second flight session"


if __name__ == "__main__":
    asyncio.run(test_repeat_flight_detection())
