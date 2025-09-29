#!/usr/bin/env python3
"""
Fix stuck flights in 'wait_for_completion' status with completion_time set.

This script identifies and fixes flight summaries that have completion_time set
but are still in 'wait_for_completion' status, which prevents them from being
processed by the enrichment worker.
"""
import asyncio
import logging
from sqlalchemy import text
from app.database import get_database_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fix_stuck_flights():
    """Fix stuck flights that have completion_time set but are still in wait_for_completion status."""
    async with get_database_session() as session:
        # Count how many records need fixing
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries 
            WHERE enrichment_status = 'wait_for_completion'
            AND completion_time IS NOT NULL
        """))
        count = result.scalar()
        logger.info(f"Found {count} stuck flights in 'wait_for_completion' status with completion_time set")
        
        if count == 0:
            logger.info("No stuck flights found. All good!")
            return
        
        # Fix the records by updating their status to 'pending'
        result = await session.execute(text("""
            UPDATE flight_summaries
            SET enrichment_status = 'pending',
                enrichment_run_after = NOW(),
                updated_at = NOW()
            WHERE enrichment_status = 'wait_for_completion'
            AND completion_time IS NOT NULL
            RETURNING id, callsign
        """))
        
        fixed_flights = result.fetchall()
        await session.commit()
        
        logger.info(f"Fixed {len(fixed_flights)} flights. Transitioning from 'wait_for_completion' to 'pending' status.")
        
        # Log a sample of fixed flights
        sample_size = min(10, len(fixed_flights))
        if sample_size > 0:
            logger.info(f"Sample of fixed flights (showing {sample_size}):")
            for i in range(sample_size):
                logger.info(f"  - id={fixed_flights[i].id}, callsign={fixed_flights[i].callsign}")
        
        # Verify that all records were fixed
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries 
            WHERE enrichment_status = 'wait_for_completion'
            AND completion_time IS NOT NULL
        """))
        
        remaining = result.scalar()
        if remaining > 0:
            logger.warning(f"WARNING: {remaining} flights still in 'wait_for_completion' with completion_time set")
        else:
            logger.info("All stuck flights have been fixed successfully!")

if __name__ == "__main__":
    asyncio.run(fix_stuck_flights())