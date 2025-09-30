#!/usr/bin/env python3
"""
Database sequence verification and synchronization utility.

This module provides functions to verify and synchronize PostgreSQL sequences
with their respective table data to prevent primary key conflicts.
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

async def verify_and_sync_sequences(session):
    """
    Verify that all PostgreSQL sequences are properly aligned with their tables 
    and reset them if necessary.
    
    This function should be called during application startup to prevent
    primary key conflicts due to sequence-data inconsistencies.
    
    Args:
        session: SQLAlchemy async session
        
    Returns:
        bool: True if all sequences are properly aligned or were successfully reset
    """
    try:
        # Get a list of all tables with sequences, filtering only user tables
        result = await session.execute(text("""
            SELECT 
                c.relname as table_name,
                a.attname as column_name,
                pg_get_serial_sequence(c.relname, a.attname) as sequence_name
            FROM 
                pg_class c
            JOIN 
                pg_attribute a ON a.attrelid = c.oid
            JOIN
                pg_namespace n ON n.oid = c.relnamespace
            WHERE 
                c.relkind = 'r' AND
                n.nspname = 'public' AND
                a.attnum > 0 AND 
                NOT a.attisdropped AND
                pg_get_serial_sequence(c.relname, a.attname) IS NOT NULL
        """))
        
        sequences = result.fetchall()
        logger.info(f"Verifying {len(sequences)} sequences")
        
        # Check and reset each sequence if needed
        sequences_fixed = 0
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
            
            if max_id > 0 and current_seq < max_id:
                new_seq_value = max_id + 1
                logger.warning(
                    f"Table {table_name}: Sequence {sequence_name} ({current_seq}) "
                    f"is behind MAX({column_name}) ({max_id}), resetting to {new_seq_value}"
                )
                
                # Reset the sequence
                await session.execute(
                    text(f"SELECT setval('{sequence_name}', {new_seq_value}, false)")
                )
                sequences_fixed += 1
        
        # Commit all changes
        await session.commit()
        
        if sequences_fixed > 0:
            logger.info(f"✅ Reset {sequences_fixed} sequences that were behind their table data")
        else:
            logger.info("✅ All sequences are properly aligned with their table data")
            
        return True
        
    except Exception as e:
        logger.error(f"Error verifying sequences: {e}")
        await session.rollback()
        return False