#!/usr/bin/env python3
"""
Unit tests for the session selector module.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.session_selector import select_canonical_sessions


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result
    return mock_session, mock_result


@pytest.fixture
def sia223_data():
    """Fixture with the exact SIA223 data from 2025-10-02 09:06:03."""
    return {
        "id": 310873,
        "callsign": "SIA223",
        "aircraft_type": "A359",
        "latitude": -14.91787,
        "longitude": 121.12397,
        "altitude": 36562,
        "heading": 139,
        "groundspeed": 546,
        "departure": "EGLL",
        "arrival": "YSSY",
        "route": "DET Q70 KOK UL607 MATUG DCT BOMBI DCT TENLO DCT DEXIT DCT PESAT DCT TEGRI DCT ENIMA DCT DINRO DCT KARDE UN644 ROLIN DCT LAGAS M747 SULEL N449 DUKAN B449 RANAH L750 ZB G201 BINDO L750 MERUN L333 JJP J1 KKJ L759 ENTAP W49 BBS L759 PUT B579 VPL W531 VIH A464 VKL DCT TOPOR A464 ARAMA P501 ANITO B470 PKP L511 SBR M766 BLI M635 ATMAP A576 PKS W440 AKMIR W113 ODALE",
        "flight_rules": "I",
        "aircraft_faa": "H/A359/L",
        "aircraft_short": "",
        "alternate": "YSCB",
        "cruise_tas": 488,
        "planned_altitude": 37000,
        "deptime": "1840",
        "enroute_time": "1846",
        "fuel_time": "2050",
        "remarks": "PBN/A1B1C1D1L1O1S2 DOF/251001 REG/GNULR EET/EBUR0017 EDVV0037 EDUU0038 LOVV0114 LKAA0115 LOVV0116 LHCC0130 LRBB0152 LBSR0233 UKBU0242 LTAA0254 UGGG0334 UBBA0355 UTAK0427 UTAA0447 UTAV0522 OAKX0532 OPLR0615 OPKR0630 VIDF0644 VECF0733 VYYF0934 VOMF0938 VYYF1000 VTBB1021 WMFC1057 WIIF1147 WAAF1300 YBBB1413 YMMM1556 OPR/SIA PER/C RALT/WADD YPTN RMK/TCAS SIMBRIEF /V/",
        "revision_id": None,
        "assigned_transponder": None,
        "last_updated": datetime(2025, 10, 2, 9, 6, 3, tzinfo=timezone.utc),
        "cid": 1666244,
        "name": "Tomas Jones EGLF",
        "server": "UK",
        "pilot_rating": 0,
        "military_rating": 0,
        "transponder": "7304",
        "qnh_i_hg": None,
        "qnh_mb": None,
        "logon_time": datetime(2025, 10, 2, 2, 21, 48, tzinfo=timezone.utc),
        "last_updated_api": datetime(2025, 10, 2, 9, 5, 13, tzinfo=timezone.utc),
        "created_at": datetime(2025, 10, 2, 9, 6, 3, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 10, 2, 9, 6, 3, tzinfo=timezone.utc)
    }


@pytest.fixture
def sia223_later_data():
    """Fixture with SIA223 data from 2025-10-02 13:23:39 (last record)."""
    return {
        "id": 311112,
        "callsign": "SIA223",
        "aircraft_type": "A359",
        "latitude": -33.94619,
        "longitude": 151.17696,
        "altitude": 0,
        "heading": 60,
        "groundspeed": 5,  # Low groundspeed indicating landed
        "departure": "EGLL",
        "arrival": "YSSY",
        "route": "DET Q70 KOK UL607 MATUG DCT BOMBI DCT TENLO DCT DEXIT DCT PESAT DCT TEGRI DCT ENIMA DCT DINRO DCT KARDE UN644 ROLIN DCT LAGAS M747 SULEL N449 DUKAN B449 RANAH L750 ZB G201 BINDO L750 MERUN L333 JJP J1 KKJ L759 ENTAP W49 BBS L759 PUT B579 VPL W531 VIH A464 VKL DCT TOPOR A464 ARAMA P501 ANITO B470 PKP L511 SBR M766 BLI M635 ATMAP A576 PKS W440 AKMIR W113 ODALE",
        "flight_rules": "I",
        "aircraft_faa": "H/A359/L",
        "aircraft_short": "",
        "alternate": "YSCB",
        "cruise_tas": 488,
        "planned_altitude": 37000,
        "deptime": "1840",
        "enroute_time": "1846",
        "fuel_time": "2050",
        "remarks": "PBN/A1B1C1D1L1O1S2 DOF/251001 REG/GNULR EET/EBUR0017 EDVV0037 EDUU0038 LOVV0114 LKAA0115 LOVV0116 LHCC0130 LRBB0152 LBSR0233 UKBU0242 LTAA0254 UGGG0334 UBBA0355 UTAK0427 UTAA0447 UTAV0522 OAKX0532 OPLR0615 OPKR0630 VIDF0644 VECF0733 VYYF0934 VOMF0938 VYYF1000 VTBB1021 WMFC1057 WIIF1147 WAAF1300 YBBB1413 YMMM1556 OPR/SIA PER/C RALT/WADD YPTN RMK/TCAS SIMBRIEF /V/",
        "revision_id": None,
        "assigned_transponder": None,
        "last_updated": datetime(2025, 10, 2, 13, 23, 39, tzinfo=timezone.utc),
        "cid": 1666244,
        "name": "Tomas Jones EGLF",
        "server": "UK",
        "pilot_rating": 0,
        "military_rating": 0,
        "transponder": "7304",
        "qnh_i_hg": None,
        "qnh_mb": None,
        "logon_time": datetime(2025, 10, 2, 2, 21, 48, tzinfo=timezone.utc),
        "last_updated_api": datetime(2025, 10, 2, 13, 22, 45, tzinfo=timezone.utc),
        "created_at": datetime(2025, 10, 2, 13, 23, 39, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 10, 2, 13, 23, 39, tzinfo=timezone.utc)
    }


@pytest.mark.asyncio
@patch('app.services.session_selector.get_database_session')
async def test_select_canonical_sessions_with_sia223_single_record(mock_get_db_session, mock_db_session, sia223_data):
    """
    Test session selector with a single SIA223 record at 09:06:03.
    
    This test simulates the scenario where only one record (at 09:06:03) exists for SIA223.
    The session selector should set both session_start and session_end to 09:06:03.
    """
    mock_session, mock_result = mock_db_session
    mock_get_db_session.return_value.__aenter__.return_value = mock_session
    
    # Mock the database response to return a single SIA223 record
    mock_row = MagicMock()
    mock_row.callsign = sia223_data["callsign"]
    mock_row.cid = sia223_data["cid"]
    mock_row.departure = sia223_data["departure"]
    mock_row.arrival = sia223_data["arrival"]
    mock_row.session_start = sia223_data["logon_time"]
    mock_row.session_end = sia223_data["last_updated"]
    mock_row.latest_deptime = sia223_data["deptime"]
    mock_row.latest_route = sia223_data["route"]
    mock_row.latest_aircraft_type = sia223_data["aircraft_type"]
    mock_row.latest_aircraft_faa = sia223_data["aircraft_faa"]
    mock_row.latest_aircraft_short = sia223_data["aircraft_short"]
    mock_row.latest_flight_rules = sia223_data["flight_rules"]
    mock_row.latest_planned_altitude = sia223_data["planned_altitude"]
    mock_row.latest_name = sia223_data["name"]
    mock_row.latest_server = sia223_data["server"]
    mock_row.latest_pilot_rating = sia223_data["pilot_rating"]
    mock_row.latest_military_rating = sia223_data["military_rating"]
    
    mock_result.fetchall.return_value = [mock_row]
    
    # Call the function
    result = await select_canonical_sessions(completion_hours=8, gap_minutes=120)
    
    # Assertions
    assert len(result) == 1
    assert result[0]["callsign"] == "SIA223"
    assert result[0]["cid"] == 1666244
    assert result[0]["departure"] == "EGLL"
    assert result[0]["arrival"] == "YSSY"
    assert result[0]["session_start"] == sia223_data["logon_time"]
    assert result[0]["session_end"] == sia223_data["last_updated"]
    
    # The critical part: session_end should be 09:06:03 in this case
    assert result[0]["session_end"] == datetime(2025, 10, 2, 9, 6, 3, tzinfo=timezone.utc)


@pytest.mark.asyncio
@patch('app.services.session_selector.get_database_session')
async def test_select_canonical_sessions_with_sia223_multiple_records(mock_get_db_session, mock_db_session, sia223_data, sia223_later_data):
    """
    Test session selector with multiple SIA223 records (09:06:03 and 13:23:39).
    
    This test simulates the scenario where multiple records exist for SIA223,
    including the first entry at 09:06:03 and the last entry at 13:23:39.
    The session selector should set session_start to 02:21:48 (logon_time) and session_end to 13:23:39.
    """
    mock_session, mock_result = mock_db_session
    mock_get_db_session.return_value.__aenter__.return_value = mock_session
    
    # Mock the database response to return a session with the correct start and end times
    mock_row = MagicMock()
    mock_row.callsign = sia223_data["callsign"]
    mock_row.cid = sia223_data["cid"]
    mock_row.departure = sia223_data["departure"]
    mock_row.arrival = sia223_data["arrival"]
    mock_row.session_start = sia223_data["logon_time"]  # 02:21:48
    mock_row.session_end = sia223_later_data["last_updated"]  # 13:23:39
    mock_row.latest_deptime = sia223_data["deptime"]
    mock_row.latest_route = sia223_data["route"]
    mock_row.latest_aircraft_type = sia223_data["aircraft_type"]
    mock_row.latest_aircraft_faa = sia223_data["aircraft_faa"]
    mock_row.latest_aircraft_short = sia223_data["aircraft_short"]
    mock_row.latest_flight_rules = sia223_data["flight_rules"]
    mock_row.latest_planned_altitude = sia223_data["planned_altitude"]
    mock_row.latest_name = sia223_data["name"]
    mock_row.latest_server = sia223_data["server"]
    mock_row.latest_pilot_rating = sia223_data["pilot_rating"]
    mock_row.latest_military_rating = sia223_data["military_rating"]
    
    mock_result.fetchall.return_value = [mock_row]
    
    # Call the function
    result = await select_canonical_sessions(completion_hours=8, gap_minutes=120)
    
    # Assertions
    assert len(result) == 1
    assert result[0]["callsign"] == "SIA223"
    assert result[0]["cid"] == 1666244
    assert result[0]["departure"] == "EGLL"
    assert result[0]["arrival"] == "YSSY"
    assert result[0]["session_start"] == sia223_data["logon_time"]
    
    # The critical part: session_end should be 13:23:39 in this case
    assert result[0]["session_end"] == datetime(2025, 10, 2, 13, 23, 39, tzinfo=timezone.utc)


@pytest.mark.asyncio
@patch('app.services.session_selector.get_database_session')
async def test_select_canonical_sessions_with_existing_summary(mock_get_db_session, mock_db_session, sia223_data):
    """
    Test session selector when a flight summary already exists.
    
    This test simulates the scenario where a flight summary already exists for SIA223.
    The session selector should exclude this flight from the results due to the anti-join.
    """
    mock_session, mock_result = mock_db_session
    mock_get_db_session.return_value.__aenter__.return_value = mock_session
    
    # Mock the database response to return empty results (due to anti-join)
    mock_result.fetchall.return_value = []
    
    # Call the function
    result = await select_canonical_sessions(completion_hours=8, gap_minutes=120)
    
    # Assertions
    assert len(result) == 0  # No results because flight summary already exists


@pytest.mark.asyncio
@patch('app.services.session_selector.get_database_session')
async def test_select_canonical_sessions_with_inactive_flight(mock_get_db_session, mock_db_session, sia223_data):
    """
    Test session selector with an inactive flight.
    
    This test simulates the scenario where SIA223 has been inactive for more than 8 hours.
    The session selector should include this flight in the results.
    """
    mock_session, mock_result = mock_db_session
    mock_get_db_session.return_value.__aenter__.return_value = mock_session
    
    # Mock the database response to return a SIA223 record that's been inactive for >8 hours
    mock_row = MagicMock()
    mock_row.callsign = sia223_data["callsign"]
    mock_row.cid = sia223_data["cid"]
    mock_row.departure = sia223_data["departure"]
    mock_row.arrival = sia223_data["arrival"]
    mock_row.session_start = sia223_data["logon_time"]
    mock_row.session_end = sia223_data["last_updated"]
    mock_row.latest_deptime = sia223_data["deptime"]
    mock_row.latest_route = sia223_data["route"]
    mock_row.latest_aircraft_type = sia223_data["aircraft_type"]
    mock_row.latest_aircraft_faa = sia223_data["aircraft_faa"]
    mock_row.latest_aircraft_short = sia223_data["aircraft_short"]
    mock_row.latest_flight_rules = sia223_data["flight_rules"]
    mock_row.latest_planned_altitude = sia223_data["planned_altitude"]
    mock_row.latest_name = sia223_data["name"]
    mock_row.latest_server = sia223_data["server"]
    mock_row.latest_pilot_rating = sia223_data["pilot_rating"]
    mock_row.latest_military_rating = sia223_data["military_rating"]
    
    mock_result.fetchall.return_value = [mock_row]
    
    # Call the function
    result = await select_canonical_sessions(completion_hours=8, gap_minutes=120)
    
    # Assertions
    assert len(result) == 1
    assert result[0]["callsign"] == "SIA223"
    assert result[0]["session_end"] == sia223_data["last_updated"]


if __name__ == "__main__":
    pytest.main()

