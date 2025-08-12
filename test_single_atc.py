#!/usr/bin/env python3
"""
Test Single ATC Detection

This script tests ATC detection on just one flight summary row to verify functionality.
"""

import asyncio
import logging
import sys
from pathlib import Path
import json

# Add the app directory to the Python path
sys.path.insert(0, "/app")

from app.services.atc_detection_service import ATCDetectionService
from app.database import get_database_session
from sqlalchemy import text
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_single_flight():
    """Test ATC detection on a single flight."""
    try:
        logger.info("Testing ATC detection on single flight...")
        
        # Get one flight summary that needs ATC data
        async with get_database_session() as session:
            result = await session.execute(text("""
                SELECT id, callsign, departure, arrival, logon_time, controller_callsigns, controller_time_percentage
                FROM flight_summaries 
                WHERE id = 23  -- Test flight ID 23 which previously had UNNT_GND matches
            """))
            
            flight = result.fetchone()
            if not flight:
                logger.info("No flight summaries need ATC data")
                return
            
            logger.info(f"Testing flight: {flight.callsign} ({flight.departure} → {flight.arrival})")
            logger.info(f"Current controller_callsigns: {flight.controller_callsigns}")
            logger.info(f"Current controller_time_percentage: {flight.controller_time_percentage}")
            
            # Initialize ATC detection service
            atc_service = ATCDetectionService()
            
            # Test ATC detection with timeout
            try:
                atc_data = await asyncio.wait_for(
                    atc_service.detect_flight_atc_interactions(
                        flight.callsign, 
                        flight.departure, 
                        flight.arrival, 
                        flight.logon_time
                    ),
                    timeout=30.0
                )
                
                logger.info(f"ATC Detection completed successfully!")
                logger.info(f"Controllers found: {len(atc_data['controller_callsigns'])}")
                logger.info(f"Controller time percentage: {atc_data['controller_time_percentage']}%")
                logger.info(f"ATC contacts detected: {atc_data['atc_contacts_detected']}")
                
                if atc_data['controller_callsigns']:
                    logger.info("Controller details:")
                    for callsign, data in atc_data['controller_callsigns'].items():
                        logger.info(f"  {callsign}: {data['type']} - {data['time_minutes']} minutes")
                
                # Update the flight summary with ATC data
                await session.execute(text("""
                    UPDATE flight_summaries 
                    SET controller_callsigns = :controller_callsigns,
                        controller_time_percentage = :controller_time_percentage,
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "controller_callsigns": json.dumps(atc_data["controller_callsigns"]),  # Convert dict to JSON string
                    "controller_time_percentage": atc_data["controller_time_percentage"],
                    "id": flight.id
                })
                
                await session.commit()
                logger.info(f"Successfully updated flight summary {flight.id}")
                
            except asyncio.TimeoutError:
                logger.error("ATC Detection timed out after 30 seconds")
            except Exception as e:
                logger.error(f"ATC Detection failed: {e}")
                
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

async def main():
    """Main entry point."""
    try:
        await test_single_flight()
        logger.info("Single flight ATC test completed")
    except Exception as e:
        logger.error(f"Single flight ATC test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
