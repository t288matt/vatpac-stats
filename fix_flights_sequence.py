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

async def check_other_sequences():
    """Check if other tables might have similar sequence issues"""
    async with get_database_session() as session:
        try:
            # Get a list of all tables with sequences
            result = await session.execute(text("""
                SELECT 
                    c.relname as table_name,
                    a.attname as column_name,
                    pg_get_serial_sequence(c.relname, a.attname) as sequence_name
                FROM 
                    pg_class c
                JOIN 
                    pg_attribute a ON a.attrelid = c.oid
                WHERE 
                    c.relkind = 'r' AND
                    a.attnum > 0 AND 
                    NOT a.attisdropped AND
                    pg_get_serial_sequence(c.relname, a.attname) IS NOT NULL
            """))
            
            sequences = result.fetchall()
            logger.info(f"Found {len(sequences)} tables with sequences")
            
            # Check each sequence
            for seq in sequences:
                table_name = seq.table_name
                column_name = seq.column_name
                sequence_name = seq.sequence_name
                
                # Skip system tables
                if table_name.startswith('pg_') or table_name.startswith('sql_'):
                    continue
                
                # Get the current sequence value
                seq_result = await session.execute(text(f"SELECT last_value FROM {sequence_name}"))
                current_seq = seq_result.scalar() or 0
                
                # Get the maximum ID from the table
                max_id_result = await session.execute(text(f"SELECT MAX({column_name}) FROM {table_name}"))
                max_id = max_id_result.scalar() or 0
                
                if max_id > 0 and current_seq <= max_id:
                    logger.warning(f"Table {table_name}: Sequence {sequence_name} ({current_seq}) is behind MAX({column_name}) ({max_id})")
                    
            return True
        except Exception as e:
            logger.error(f"Error checking sequences: {e}")
            return False

async def main():
    """Main entry point."""
    logger.info("Starting fix_flights_sequence script")
    
    # Reset the flights_id_seq
    success = await reset_flights_sequence()
    if success:
        logger.info("Flights sequence reset completed successfully")
    else:
        logger.error("Failed to reset flights sequence")
    
    # Check other sequences
    logger.info("Checking other sequences for potential issues...")
    await check_other_sequences()
    
    logger.info("Script completed")

if __name__ == "__main__":
    asyncio.run(main())
