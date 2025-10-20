#!/usr/bin/env python3
"""
Script to run the session selector test specifically for SIA223 at 09:06:03 only.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.session_selector import select_canonical_sessions


class MockRow:
    """Mock database row for testing."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


async def test_sia223_scenario_only_0906():
    """
    Test the SIA223 scenario with ONLY the 09:06:03 record.
    This simulates what would happen if the system only had the first record
    when SIA223 entered Australian airspace, without any later records.
    """
    # SIA223 data at 09:06:03 only
    sia223_first_record = {
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
    
    # Test case: Only the 09:06:03 record exists
    with patch('app.services.session_selector.get_database_session') as mock_get_db:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_get_db.return_value.__aenter__.return_value = mock_session
        mock_session.execute.return_value = mock_result
        
        # Create a mock row with the first record data only
        mock_row = MockRow(
            callsign=sia223_first_record["callsign"],
            cid=sia223_first_record["cid"],
            departure=sia223_first_record["departure"],
            arrival=sia223_first_record["arrival"],
            session_start=sia223_first_record["logon_time"],
            session_end=sia223_first_record["last_updated"],  # This is the critical part - session_end is 09:06:03
            latest_deptime=sia223_first_record["deptime"],
            latest_route=sia223_first_record["route"],
            latest_aircraft_type=sia223_first_record["aircraft_type"],
            latest_aircraft_faa=sia223_first_record["aircraft_faa"],
            latest_aircraft_short=sia223_first_record["aircraft_short"],
            latest_flight_rules=sia223_first_record["flight_rules"],
            latest_planned_altitude=sia223_first_record["planned_altitude"],
            latest_name=sia223_first_record["name"],
            latest_server=sia223_first_record["server"],
            latest_pilot_rating=sia223_first_record["pilot_rating"],
            latest_military_rating=sia223_first_record["military_rating"]
        )
        
        mock_result.fetchall.return_value = [mock_row]
        
        print("\n=== TEST CASE: SIA223 with ONLY the first record (09:06:03) ===")
        result = await select_canonical_sessions(completion_hours=8, gap_minutes=120)
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
            print(f"  completion_time would be set to: {formatted_result['session_end']}")
            
            # Explain what happens in the canonical processor
            print("\nEXPLANATION:")
            print("  1. The session selector found only one record for SIA223 at 09:06:03")
            print("  2. It set session_start to the logon_time (02:21:48)")
            print("  3. It set session_end to the last_updated time (09:06:03)")
            print("  4. When this session is processed by the canonical processor:")
            print("     - It will insert a new flight summary with completion_time = session_end (09:06:03)")
            print("     - time_online_minutes will be 0 because there's only one record")
            print("  5. Later, when more records come in (up to 13:23:39), they won't update the summary")
            print("     because the anti-join prevents reprocessing flights that already have summaries")


if __name__ == "__main__":
    asyncio.run(test_sia223_scenario_only_0906())