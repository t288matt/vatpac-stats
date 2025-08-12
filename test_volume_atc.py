#!/usr/bin/env python3
"""
Volume ATC Detection Test

This script tests ATC detection on 50 flights to verify system performance and volume handling.
"""

import asyncio
import logging
import sys
from pathlib import Path
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, "/app")

from app.services.atc_detection_service import ATCDetectionService
from app.database import get_database_session
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_volume_atc():
    """Test ATC detection on multiple flights."""
    try:
        logger.info("Starting volume ATC detection test...")
        
        # Get flights that need ATC data
        async with get_database_session() as session:
            result = await session.execute(text("""
                SELECT id, callsign, departure, arrival, logon_time, controller_callsigns, controller_time_percentage
                FROM flight_summaries 
                WHERE controller_callsigns = '{}' OR controller_callsigns IS NULL
                ORDER BY id
                LIMIT 50
            """))
            
            flights = result.fetchall()
            if not flights:
                logger.info("No flight summaries need ATC data")
                return
            
            logger.info(f"Testing ATC detection on {len(flights)} flights...")
            
            # Initialize ATC detection service
            atc_service = ATCDetectionService()
            
            # Track results
            total_processed = 0
            total_with_atc = 0
            total_without_atc = 0
            total_errors = 0
            start_time = asyncio.get_event_loop().time()
            
            for i, flight in enumerate(flights, 1):
                try:
                    logger.info(f"[{i}/{len(flights)}] Processing flight: {flight.callsign} ({flight.departure} → {flight.arrival})")
                    
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
                        
                        # Update the flight summary with ATC data
                        await session.execute(text("""
                            UPDATE flight_summaries 
                            SET controller_callsigns = :controller_callsigns,
                                controller_time_percentage = :controller_time_percentage,
                                updated_at = NOW()
                            WHERE id = :id
                        """), {
                            "controller_callsigns": json.dumps(atc_data["controller_callsigns"]),
                            "controller_time_percentage": atc_data["controller_time_percentage"],
                            "id": flight.id
                        })
                        
                        await session.commit()
                        
                        # Track results
                        total_processed += 1
                        if atc_data["atc_contacts_detected"] > 0:
                            total_with_atc += 1
                            logger.info(f"  ✅ Found {len(atc_data['controller_callsigns'])} controllers, {atc_data['atc_contacts_detected']} contacts")
                        else:
                            total_without_atc += 1
                            logger.info(f"  ❌ No ATC contacts found")
                        
                    except asyncio.TimeoutError:
                        logger.error(f"  ⏰ ATC Detection timed out after 30 seconds")
                        total_errors += 1
                    except Exception as e:
                        logger.error(f"  💥 ATC Detection failed: {e}")
                        total_errors += 1
                        
                except Exception as e:
                    logger.error(f"  💥 Flight processing failed: {e}")
                    total_errors += 1
                
                # Progress update every 10 flights
                if i % 10 == 0:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    rate = i / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {i}/{len(flights)} flights processed ({rate:.2f} flights/sec)")
            
            # Final summary
            total_time = asyncio.get_event_loop().time() - start_time
            logger.info("=" * 60)
            logger.info("VOLUME TEST COMPLETED")
            logger.info("=" * 60)
            logger.info(f"Total flights processed: {total_processed}")
            logger.info(f"Flights with ATC contacts: {total_with_atc}")
            logger.info(f"Flights without ATC contacts: {total_without_atc}")
            logger.info(f"Errors encountered: {total_errors}")
            logger.info(f"Total processing time: {total_time:.2f} seconds")
            logger.info(f"Average processing rate: {total_processed/total_time:.2f} flights/sec")
            logger.info(f"ATC contact rate: {(total_with_atc/total_processed)*100:.1f}%" if total_processed > 0 else "N/A")
            
    except Exception as e:
        logger.error(f"Volume test failed: {e}")
        raise

async def main():
    """Main entry point."""
    try:
        await test_volume_atc()
        logger.info("Volume ATC test completed")
    except Exception as e:
        logger.error(f"Volume ATC test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
