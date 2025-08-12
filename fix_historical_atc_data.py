#!/usr/bin/env python3
"""
Fix Historical ATC Data Script

This script updates existing flight summaries with proper ATC interaction data
by re-running the ATC detection logic against historical transceiver data.
"""

import asyncio
import logging
import sys
from pathlib import Path

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

async def fix_historical_atc_data():
    """Fix ATC data for all existing flight summaries."""
    try:
        logger.info("Starting historical ATC data fix...")
        
        # Initialize ATC detection service
        atc_service = ATCDetectionService()
        
        # Get all flight summaries that need fixing
        async with get_database_session() as session:
            # Find summaries with empty controller_callsigns
            result = await session.execute(text("""
                SELECT id, callsign, departure, arrival, logon_time, controller_callsigns, controller_time_percentage
                FROM flight_summaries 
                WHERE controller_callsigns = '{}' OR controller_callsigns IS NULL
                ORDER BY id
            """))
            
            summaries_to_fix = result.fetchall()
            total_summaries = len(summaries_to_fix)
            
            if total_summaries == 0:
                logger.info("No flight summaries need fixing - all have ATC data")
                return
            
            logger.info(f"Found {total_summaries} flight summaries to fix")
            
            # Process summaries in batches
            batch_size = 10
            processed = 0
            updated = 0
            
            for i in range(0, total_summaries, batch_size):
                batch = summaries_to_fix[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(total_summaries + batch_size - 1)//batch_size}")
                
                for summary in batch:
                    try:
                        # Detect ATC interactions for this flight
                        atc_data = await atc_service.detect_flight_atc_interactions(
                            summary.callsign, 
                            summary.departure, 
                            summary.arrival, 
                            summary.logon_time
                        )
                        
                        # Update the summary with ATC data
                        await session.execute(text("""
                            UPDATE flight_summaries 
                            SET controller_callsigns = :controller_callsigns,
                                controller_time_percentage = :controller_time_percentage,
                                updated_at = NOW()
                            WHERE id = :id
                        """), {
                            "controller_callsigns": atc_data["controller_callsigns"],
                            "controller_time_percentage": atc_data["controller_time_percentage"],
                            "id": summary.id
                        })
                        
                        updated += 1
                        
                        # Log progress for flights with ATC contact
                        if atc_data["atc_contacts_detected"] > 0:
                            logger.info(f"Updated {summary.callsign}: {atc_data['atc_contacts_detected']} ATC contacts, {atc_data['controller_time_percentage']}% coverage")
                        
                    except Exception as e:
                        logger.error(f"Error fixing summary {summary.id} ({summary.callsign}): {e}")
                        continue
                    
                    processed += 1
                
                # Commit batch
                await session.commit()
                logger.info(f"Committed batch {i//batch_size + 1}")
            
            logger.info(f"Historical ATC data fix completed: {processed} processed, {updated} updated")
            
    except Exception as e:
        logger.error(f"Error in historical ATC data fix: {e}")
        raise

async def main():
    """Main entry point."""
    try:
        await fix_historical_atc_data()
        logger.info("Historical ATC data fix completed successfully")
    except Exception as e:
        logger.error(f"Historical ATC data fix failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
