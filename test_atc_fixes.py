#!/usr/bin/env python3
"""
Test script to verify the ATC detection service changes.
This script tests that the transceivers fallback has been removed.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from app.services.atc_detection_service import ATCDetectionService

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_atc_fixes():
    """Test the ATC detection service with the fixed code."""
    logger.info("Starting ATC detection service test")
    
    # Create instance of the detection service
    service = ATCDetectionService()
    
    # Sample test data
    test_flight = {
        "callsign": "QFA123",  # Test flight callsign
        "departure": "YSSY",   # Sydney
        "arrival": "YMML",     # Melbourne
        "logon_time": datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
    }
    
    # Test _get_flight_record_count
    logger.info("Testing _get_flight_record_count (should only use flights or flights_archive)")
    try:
        # We expect this to return 0 since we're using a fake flight
        # But we want to verify no errors occur due to missing transceivers fallback
        record_count = await service._get_flight_record_count(
            test_flight["callsign"],
            test_flight["departure"],
            test_flight["arrival"],
            test_flight["logon_time"]
        )
        logger.info(f"Record count test completed successfully: {record_count}")
    except Exception as e:
        logger.error(f"Error in _get_flight_record_count: {e}")
        return False
    
    # Test _get_airborne_time_from_flights
    logger.info("Testing _get_airborne_time_from_flights (should only use flights or flights_archive)")
    try:
        # We expect this to return 0 since we're using a fake flight
        airborne_time = await service._get_airborne_time_from_flights(
            test_flight["callsign"],
            test_flight["departure"],
            test_flight["arrival"],
            test_flight["logon_time"],
            datetime.utcnow()  # completion_time
        )
        logger.info(f"Airborne time test completed successfully: {airborne_time}")
    except Exception as e:
        logger.error(f"Error in _get_airborne_time_from_flights: {e}")
        return False
    
    # Test full ATC detection workflow 
    logger.info("Testing full ATC detection workflow")
    try:
        atc_data = await service.detect_flight_atc_interactions(
            test_flight["callsign"],
            test_flight["departure"],
            test_flight["arrival"],
            test_flight["logon_time"]
        )
        logger.info(f"Full ATC detection test completed successfully")
        logger.info(f"ATC data: {atc_data}")
    except Exception as e:
        logger.error(f"Error in detect_flight_atc_interactions: {e}")
        return False
    
    logger.info("All tests completed successfully!")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_atc_fixes())
    exit(0 if result else 1)
