#!/usr/bin/env python3
"""
Reset the flights_id_seq sequence to prevent primary key conflicts.

This script fixes the critical issue where PostgreSQL sequence is out of sync
with the actual data in the flights table, causing primary key constraint violations
during flight data insertion.
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

async def reset_flights_sequence():
    """Reset the flights_id_seq sequence to MAX(id) + 1"""
    async with get_database_session() as session:
        try:
            # Get the current sequence value
            seq_result = await session.execute(text("SELECT last_value FROM flights_id_seq"))
            current_seq = seq_result.scalar() or 0
            
            # Get the maximum ID from the flights table
            max_id_result = await session.execute(text("SELECT MAX(id) FROM flights"))
            max_id = max_id_result.scalar() or 0
            
            logger.info(f"Current sequence value: {current_seq}")
            logger.info(f"Maximum ID in flights table: {max_id}")
            
            # Only reset if sequence is behind max ID
            if current_seq <= max_id:
                new_seq_value = max_id + 1
                await session.execute(
                    text(f"SELECT setval('flights_id_seq', {new_seq_value}, false)")
                )
                logger.info(f"Reset flights_id_seq to {new_seq_value}")
                
                # Verify the update was successful
                verify_result = await session.execute(text("SELECT last_value FROM flights_id_seq"))
                new_seq = verify_result.scalar() or 0
                logger.info(f"Verified new sequence value: {new_seq}")
                
                if new_seq != new_seq_value:
                    logger.error(f"Sequence reset verification failed! Expected {new_seq_value}, got {new_seq}")
            else:
                logger.info("Sequence is already ahead of maximum ID, no reset needed")
            
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to reset flights sequence: {e}")
            await session.rollback()
            return False

async def main():
    """Main entry point for the script."""
    logger.info("Starting flights sequence reset procedure")
    success = await reset_flights_sequence()
    if success:
        logger.info("✅ Flights sequence reset completed successfully")
    else:
        logger.error("❌ Failed to reset flights sequence")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())