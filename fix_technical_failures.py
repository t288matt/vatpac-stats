#!/usr/bin/env python3
"""
Fix flight summaries stuck in technical_failure status.

This script resets flight summaries from technical_failure to pending status
so they can be reprocessed by the enrichment worker.
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

async def fix_technical_failures():
    """Reset flight summaries from technical_failure to pending status."""
    async with get_database_session() as session:
        # Count how many records need fixing
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries 
            WHERE enrichment_status = 'technical_failure'
            AND enrichment_last_error LIKE '%Safety mechanism triggered%'
        """))
        count = result.scalar()
        logger.info(f"Found {count} flight summaries in technical_failure status")

        if count == 0:
            logger.info("No technical failures to fix")
            return

        # Reset enrichment attempts to 0 and status to pending
        result = await session.execute(text("""
            UPDATE flight_summaries
            SET enrichment_status = 'pending',
                enrichment_attempts = 0,
                enrichment_run_after = NOW(),
                enrichment_last_error = 'Reset from technical_failure by fix script',
                enrichment_error = NULL,
                updated_at = NOW()
            WHERE enrichment_status = 'technical_failure'
            AND enrichment_last_error LIKE '%Safety mechanism triggered%'
            RETURNING id, callsign
        """))
        
        updated = result.fetchall()
        logger.info(f"Reset {len(updated)} flight summaries from technical_failure to pending")
        
        # Commit the changes
        await session.commit()
        logger.info("Changes committed successfully")

async def main():
    """Main entry point."""
    logger.info("Starting fix_technical_failures script")
    await fix_technical_failures()
    logger.info("Script completed")

if __name__ == "__main__":
    asyncio.run(main())
