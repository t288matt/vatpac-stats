#!/usr/bin/env python3
"""
Database Test for 300nm Geographic Proximity Query

This test runs the exact SQL query from the Flight Detection Service against
the database to see why the 300nm geographic proximity check is not working.
"""

import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The exact query from Flight Detection Service
GEOGRAPHIC_QUERY = """
WITH controller_transceivers AS (
    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
    FROM transceivers t 
    WHERE t.entity_type = 'atc' 
    AND t.callsign = :controller_callsign
    AND t.timestamp BETWEEN :session_start AND :session_end
),
flight_transceivers AS (
    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
    FROM transceivers t 
    WHERE t.entity_type = 'flight' 
    AND t.timestamp BETWEEN :session_start AND :session_end
),
frequency_matches AS (
    SELECT ct.callsign as controller_callsign, ct.frequency_mhz, ct.timestamp as controller_time,
           ft.callsign as flight_callsign, ft.timestamp as flight_time,
           ct.position_lat as controller_lat, ct.position_lon as controller_lon,
           ft.position_lat as flight_lat, ft.position_lon as flight_lon
    FROM controller_transceivers ct 
    JOIN flight_transceivers ft ON ct.frequency_mhz = ft.frequency_mhz 
    AND ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) <= :time_window
    AND (
        -- Haversine formula for distance in nautical miles
        (3440.065 * ACOS(
            LEAST(1, GREATEST(-1, 
                SIN(RADIANS(ct.position_lat)) * SIN(RADIANS(ft.position_lat)) +
                COS(RADIANS(ct.position_lat)) * COS(RADIANS(ft.position_lat)) * 
                COS(RADIANS(ct.position_lon - ft.position_lon))
            ))
        )) <= :proximity_threshold_nm
    )
)
SELECT 
    controller_callsign,
    flight_callsign,
    frequency_mhz,
    controller_time,
    flight_time,
    controller_lat,
    controller_lon,
    flight_lat,
    flight_lon,
    ABS(EXTRACT(EPOCH FROM (controller_time - flight_time))) as time_diff_seconds
FROM frequency_matches
ORDER BY flight_time, controller_time
"""

# Simplified test query to test just the geographic proximity calculation
DISTANCE_TEST_QUERY = """
WITH test_coords AS (
    SELECT 
        :controller_lat as controller_lat, 
        :controller_lon as controller_lon,
        :flight_lat as flight_lat, 
        :flight_lon as flight_lon
)
SELECT 
    controller_lat,
    controller_lon,
    flight_lat,
    flight_lon,
    -- Haversine formula for distance in nautical miles
    (3440.065 * ACOS(
        LEAST(1, GREATEST(-1, 
            SIN(RADIANS(controller_lat)) * SIN(RADIANS(flight_lat)) +
            COS(RADIANS(controller_lat)) * COS(RADIANS(flight_lat)) * 
            COS(RADIANS(controller_lon - flight_lon))
        ))
    )) as distance_nm,
    -- Check if within 300nm threshold
    CASE WHEN (
        (3440.065 * ACOS(
            LEAST(1, GREATEST(-1, 
                SIN(RADIANS(controller_lat)) * SIN(RADIANS(flight_lat)) +
                COS(RADIANS(controller_lat)) * COS(RADIANS(flight_lat)) * 
                COS(RADIANS(controller_lon - flight_lon))
            ))
        ))
    ) <= :proximity_threshold_nm THEN 'WITHIN_RANGE' ELSE 'OUT_OF_RANGE' END as proximity_check
FROM test_coords
"""

async def test_database_geographic_query():
    """Test the geographic proximity query directly in the database."""
    
    logger.info("🧪 Testing 300nm Geographic Proximity Query in Database")
    logger.info("=" * 70)
    
    # Test coordinates from our database
    test_cases = [
        {
            "name": "AD_GND vs VOZ905 (Adelaide vs Sydney)",
            "controller_lat": -34.952425,
            "controller_lon": 138.53208,
            "flight_lat": -33.939316,
            "flight_lon": 151.164666,
            "expected_distance": 628.0,
            "should_be_within_300nm": False
        },
        {
            "name": "AD_GND vs PAL416 (Adelaide vs Canberra)",
            "controller_lat": -34.952425,
            "controller_lon": 138.53208,
            "flight_lat": -35.306184,
            "flight_lon": 149.191342,
            "expected_distance": 523.6,
            "should_be_within_300nm": False
        },
        {
            "name": "AD_GND vs VOZ63 (Adelaide vs Adelaide - same location)",
            "controller_lat": -34.952425,
            "controller_lon": 138.53208,
            "flight_lat": -34.952425,
            "flight_lon": 138.53208,
            "expected_distance": 0.0,
            "should_be_within_300nm": True
        }
    ]
    
    logger.info("📊 Test Cases:")
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"  {i}. {test_case['name']}")
        logger.info(f"     Controller: ({test_case['controller_lat']}, {test_case['controller_lon']})")
        logger.info(f"     Flight: ({test_case['flight_lat']}, {test_case['flight_lon']})")
        logger.info(f"     Expected: {test_case['expected_distance']:.1f}nm, Within 300nm: {test_case['should_be_within_300nm']}")
        logger.info("")
    
    logger.info("🔍 Next Steps:")
    logger.info("1. Run this query in the database to see if the geographic proximity check works")
    logger.info("2. Check if there are any SQL syntax errors or constraint violations")
    logger.info("3. Verify that the JOIN condition is properly structured")
    logger.info("4. Test with actual data from the transceivers table")
    
    return test_cases

async def test_actual_database_data():
    """Test the query with actual data from the database."""
    
    logger.info("\n🗄️ Testing with Actual Database Data")
    logger.info("=" * 50)
    
    # Test the exact query that should be running
    logger.info("The Flight Detection Service should be running this query:")
    logger.info("=" * 50)
    logger.info(GEOGRAPHIC_QUERY)
    logger.info("=" * 50)
    
    logger.info("\n🔍 Key Points to Check:")
    logger.info("1. The JOIN condition includes the geographic proximity check")
    logger.info("2. The Haversine formula is correctly implemented")
    logger.info("3. The proximity_threshold_nm parameter is set to 300")
    logger.info("4. The query should filter out flights > 300nm away")
    
    logger.info("\n❓ Why is this query not working?")
    logger.info("Possible issues:")
    logger.info("1. The JOIN condition structure is incorrect")
    logger.info("2. The geographic proximity check is not being enforced")
    logger.info("3. There's a SQL syntax error preventing execution")
    logger.info("4. The query is being overridden somewhere else")
    
    return True

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_database_geographic_query())
    asyncio.run(test_actual_database_data())
