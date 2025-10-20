#!/usr/bin/env python3
"""
Test script that simulates the exact database query and results for SIA223 with only the 09:06:03 record.
This test shows exactly what would happen in the session selector when only the first record exists.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import text

from app.services.session_selector import select_canonical_sessions


class MockDatabaseSession:
    """Mock database session that simulates the exact query execution and results."""
    
    def __init__(self, flight_records):
        self.flight_records = flight_records
    
    async def execute(self, query, params):
        """Simulate query execution by processing the SQL directly."""
        # For this test, we'll simulate the SQL logic manually
        
        # Extract parameters
        completion_hours = params.get("completion_hours", 8)
        gap_minutes = params.get("gap_minutes", 120)
        
        # Filter records that are older than completion_hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=completion_hours)
        filtered_records = [r for r in self.flight_records if r["last_updated"] <= cutoff_time]
        
        # Group records by callsign, cid, departure, arrival
        grouped_records = {}
        for record in filtered_records:
            key = (record["callsign"], record["cid"], record["departure"], record["arrival"])
            if key not in grouped_records:
                grouped_records[key] = []
            grouped_records[key].append(record)
        
        # Process each group to find session_start and session_end
        results = []
        for (callsign, cid, departure, arrival), records in grouped_records.items():
            # Sort records by last_updated
            records.sort(key=lambda r: r["last_updated"])
            
            # Find session_start (MIN(logon_time))
            session_start = min(r["logon_time"] for r in records)
            
            # Find session_end (MAX(last_updated))
            session_end = max(r["last_updated"] for r in records)
            
            # Get latest values
            latest_record = records[-1]
            
            # Create a result row
            result_row = MagicMock()
            result_row.callsign = callsign
            result_row.cid = cid
            result_row.departure = departure
            result_row.arrival = arrival
            result_row.session_start = session_start
            result_row.session_end = session_end
            result_row.latest_deptime = latest_record["deptime"]
            result_row.latest_route = latest_record["route"]
            result_row.latest_aircraft_type = latest_record["aircraft_type"]
            result_row.latest_aircraft_faa = latest_record["aircraft_faa"]
            result_row.latest_aircraft_short = latest_record["aircraft_short"]
            result_row.latest_flight_rules = latest_record["flight_rules"]
            result_row.latest_planned_altitude = latest_record["planned_altitude"]
            result_row.latest_name = latest_record["name"]
            result_row.latest_server = latest_record["server"]
            result_row.latest_pilot_rating = latest_record["pilot_rating"]
            result_row.latest_military_rating = latest_record["military_rating"]
            
            results.append(result_row)
        
        # Create a mock result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = results
        
        return mock_result


async def test_sia223_exact_scenario():
    """Test the exact scenario for SIA223 with only the 09:06:03 record."""
    # Create the SIA223 record at 09:06:03
    sia223_record = {
        "callsign": "SIA223",
        "cid": 1666244,
        "departure": "EGLL",
        "arrival": "YSSY",
        "logon_time": datetime(2025, 10, 2, 2, 21, 48, tzinfo=timezone.utc),
        "last_updated": datetime(2025, 10, 2, 9, 6, 3, tzinfo=timezone.utc),
        "deptime": "1840",
        "route": "DET Q70 KOK UL607 MATUG DCT BOMBI DCT TENLO DCT DEXIT DCT PESAT DCT TEGRI DCT ENIMA DCT DINRO DCT KARDE UN644 ROLIN DCT LAGAS M747 SULEL N449 DUKAN B449 RANAH L750 ZB G201 BINDO L750 MERUN L333 JJP J1 KKJ L759 ENTAP W49 BBS L759 PUT B579 VPL W531 VIH A464 VKL DCT TOPOR A464 ARAMA P501 ANITO B470 PKP L511 SBR M766 BLI M635 ATMAP A576 PKS W440 AKMIR W113 ODALE",
        "aircraft_type": "A359",
        "aircraft_faa": "H/A359/L",
        "aircraft_short": "",
        "flight_rules": "I",
        "planned_altitude": 37000,
        "name": "Tomas Jones EGLF",
        "server": "UK",
        "pilot_rating": 0,
        "military_rating": 0
    }
    
    # Create a mock database session with only this record
    mock_db_session = MockDatabaseSession([sia223_record])
    
    # Patch the database session
    with patch('app.services.session_selector.get_database_session') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        
        # Make the completion_hours negative so the record is considered inactive
        # This simulates the record being older than the completion_hours threshold
        print("\n=== EXACT TEST SCENARIO: SIA223 with only the 09:06:03 record ===")
        result = await select_canonical_sessions(completion_hours=-1, gap_minutes=120)
        
        print(f"Number of sessions: {len(result)}")
        if result:
            # Convert datetime objects to strings for better readability
            formatted_result = result[0].copy()
            formatted_result["session_start"] = formatted_result["session_start"].isoformat()
            formatted_result["session_end"] = formatted_result["session_end"].isoformat()
            print(f"Session: {json.dumps(formatted_result, indent=2)}")
            
            # Highlight the critical values
            print("\nCRITICAL VALUES:")
            print(f"  logon_time (session_start): {formatted_result['session_start']}")
            print(f"  last_updated (session_end): {formatted_result['session_end']}")
            
            # Explain what happens next
            print("\nWHAT HAPPENS NEXT:")
            print("  1. The canonical processor receives this session")
            print("  2. It creates a flight summary with:")
            print(f"     - completion_time = {formatted_result['session_end']} (from session_end)")
            print("  3. It calculates time_online_minutes by querying:")
            print("     SELECT MIN(last_updated), MAX(last_updated) FROM flights")
            print("     WHERE callsign='SIA223' AND cid=1666244 AND departure='EGLL' AND arrival='YSSY'")
            print("     AND last_updated BETWEEN '2025-10-02 02:21:48' AND '2025-10-02 09:06:03'")
            print("  4. Since there's only one record at 09:06:03, MIN=MAX=09:06:03")
            print("  5. time_online_minutes = (MAX - MIN) = 0 minutes")
            print("  6. This explains why the flight summary has completion_time=09:06:03 and time_online_minutes=0")


if __name__ == "__main__":
    asyncio.run(test_sia223_exact_scenario())

