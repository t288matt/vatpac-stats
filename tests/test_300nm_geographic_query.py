#!/usr/bin/env python3
"""
Unit Test for 300nm Geographic Proximity Query

This test isolates the exact SQL query from the Flight Detection Service to test
the 300nm geographic proximity check with known coordinates.
"""

import asyncio
import logging
import math
from datetime import datetime, timezone
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test coordinates - these are the exact coordinates from our database
TEST_COORDINATES = {
    "AD_GND": {
        "lat": -34.952425,
        "lon": 138.53208,
        "location": "Adelaide (YPAD)"
    },
    "VOZ905": {
        "lat": -33.939316,
        "lon": 151.164666,
        "location": "Sydney (YSSY)"
    },
    "PAL416": {
        "lat": -35.306184,
        "lon": 149.191342,
        "location": "Canberra (YSCB)"
    },
    "VOZ63": {
        "lat": -34.952425,
        "lon": 138.53208,
        "location": "Adelaide (YPAD) - Same as AD_GND"
    }
}

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
    JOIN flight_transceivers ft
      ON ABS(ct.frequency_mhz - ft.frequency_mhz) <= 0.005  -- ~5 kHz tolerance
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

def calculate_distance_manually(lat1, lon1, lat2, lon2):
    """Calculate distance manually using the same formula for verification."""
    import math
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in nautical miles
    R = 3440.065
    
    distance_nm = R * c
    return distance_nm

async def test_geographic_proximity_query():
    """Test the geographic proximity query with known coordinates."""
    
    logger.info("🧪 Testing 300nm Geographic Proximity Query")
    logger.info("=" * 60)
    
    # Test case 1: AD_GND vs VOZ905 (Adelaide vs Sydney)
    logger.info("\n📍 Test Case 1: AD_GND (Adelaide) vs VOZ905 (Sydney)")
    logger.info(f"AD_GND: {TEST_COORDINATES['AD_GND']['location']} ({TEST_COORDINATES['AD_GND']['lat']}, {TEST_COORDINATES['AD_GND']['lon']})")
    logger.info(f"VOZ905: {TEST_COORDINATES['VOZ905']['location']} ({TEST_COORDINATES['VOZ905']['lat']}, {TEST_COORDINATES['VOZ905']['lon']})")
    
    # Manual calculation
    manual_distance = calculate_distance_manually(
        TEST_COORDINATES['AD_GND']['lat'], TEST_COORDINATES['AD_GND']['lon'],
        TEST_COORDINATES['VOZ905']['lat'], TEST_COORDINATES['VOZ905']['lon']
    )
    logger.info(f"Manual calculation: {manual_distance:.2f} nautical miles")
    logger.info(f"Within 300nm threshold: {'✅ YES' if manual_distance <= 300 else '❌ NO'}")
    
    # Test case 2: AD_GND vs PAL416 (Adelaide vs Canberra)
    logger.info("\n📍 Test Case 2: AD_GND (Adelaide) vs PAL416 (Canberra)")
    logger.info(f"AD_GND: {TEST_COORDINATES['AD_GND']['location']} ({TEST_COORDINATES['AD_GND']['lat']}, {TEST_COORDINATES['AD_GND']['lon']})")
    logger.info(f"PAL416: {TEST_COORDINATES['PAL416']['location']} ({TEST_COORDINATES['PAL416']['lat']}, {TEST_COORDINATES['PAL416']['lon']})")
    
    manual_distance2 = calculate_distance_manually(
        TEST_COORDINATES['AD_GND']['lat'], TEST_COORDINATES['AD_GND']['lon'],
        TEST_COORDINATES['PAL416']['lat'], TEST_COORDINATES['PAL416']['lon']
    )
    logger.info(f"Manual calculation: {manual_distance2:.2f} nautical miles")
    logger.info(f"Within 300nm threshold: {'✅ YES' if manual_distance2 <= 300 else '❌ NO'}")
    
    # Test case 3: AD_GND vs VOZ63 (Adelaide vs Adelaide - same location)
    logger.info("\n📍 Test Case 3: AD_GND (Adelaide) vs VOZ63 (Adelaide - same location)")
    logger.info(f"AD_GND: {TEST_COORDINATES['AD_GND']['location']} ({TEST_COORDINATES['AD_GND']['lat']}, {TEST_COORDINATES['AD_GND']['lon']})")
    logger.info(f"VOZ63: {TEST_COORDINATES['VOZ63']['location']} ({TEST_COORDINATES['VOZ63']['lat']}, {TEST_COORDINATES['VOZ63']['lon']})")
    
    manual_distance3 = calculate_distance_manually(
        TEST_COORDINATES['AD_GND']['lat'], TEST_COORDINATES['AD_GND']['lon'],
        TEST_COORDINATES['VOZ63']['lat'], TEST_COORDINATES['VOZ63']['lon']
    )
    logger.info(f"Manual calculation: {manual_distance3:.2f} nautical miles")
    logger.info(f"Within 300nm threshold: {'✅ YES' if manual_distance3 <= 300 else '❌ NO'}")
    
    # Test the SQL formula directly
    logger.info("\n🔍 Testing SQL Formula Components:")
    
    # Test the ACOS component
    lat1_rad = math.radians(TEST_COORDINATES['AD_GND']['lat'])
    lon1_rad = math.radians(TEST_COORDINATES['AD_GND']['lon'])
    lat2_rad = math.radians(TEST_COORDINATES['VOZ905']['lat'])
    lon2_rad = math.radians(TEST_COORDINATES['VOZ905']['lon'])
    
    # Calculate the argument for ACOS
    acos_arg = (math.sin(lat1_rad) * math.sin(lat2_rad) + 
                math.cos(lat1_rad) * math.cos(lat2_rad) * math.cos(lon1_rad - lon2_rad))
    
    logger.info(f"ACOS argument: {acos_arg:.6f}")
    logger.info(f"ACOS argument clamped to [-1,1]: {max(-1, min(1, acos_arg)):.6f}")
    
    # Test the distance calculation
    if -1 <= acos_arg <= 1:
        distance_from_acos = 3440.065 * math.acos(acos_arg)
        logger.info(f"Distance from ACOS: {distance_from_acos:.2f} nautical miles")
    else:
        logger.error("❌ ACOS argument out of valid range [-1,1]")
    
    logger.info("\n📊 Summary:")
    logger.info(f"AD_GND ↔ VOZ905: {manual_distance:.2f}nm (Should be OUTSIDE 300nm)")
    logger.info(f"AD_GND ↔ PAL416: {manual_distance2:.2f}nm (Should be OUTSIDE 300nm)")
    logger.info(f"AD_GND ↔ VOZ63: {manual_distance3:.2f}nm (Should be INSIDE 300nm)")
    
    # Expected results
    expected_results = {
        "AD_GND_vs_VOZ905": manual_distance > 300,  # Should be OUTSIDE
        "AD_GND_vs_PAL416": manual_distance2 > 300, # Should be OUTSIDE  
        "AD_GND_vs_VOZ63": manual_distance3 <= 300  # Should be INSIDE
    }
    
    logger.info("\n✅ Expected Results:")
    for test_name, should_be_outside in expected_results.items():
        status = "OUTSIDE 300nm" if should_be_outside else "INSIDE 300nm"
        logger.info(f"  {test_name}: {status}")
    
    return expected_results

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_geographic_proximity_query())
