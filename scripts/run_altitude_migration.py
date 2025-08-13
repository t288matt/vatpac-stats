#!/usr/bin/env python3
"""
Migration Script: Add altitude fields to flight_sector_occupancy table

This script adds entry_altitude and exit_altitude fields to track
flight altitudes when entering and exiting sectors.

Run with: python scripts/run_altitude_migration.py
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from database import get_database_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_altitude_migration():
    """Run the altitude fields migration"""
    try:
        logger.info("Starting altitude fields migration...")
        
        async with get_database_session() as session:
            # Read the migration SQL
            migration_file = Path(__file__).parent / "add_altitude_fields_migration.sql"
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            # Execute the migration
            logger.info("Executing migration SQL...")
            await session.execute(migration_sql)
            await session.commit()
            
            logger.info("✅ Migration completed successfully!")
            
            # Verify the new fields exist
            result = await session.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'flight_sector_occupancy' 
                    AND column_name IN ('entry_altitude', 'exit_altitude')
                ORDER BY column_name
            """)
            
            columns = result.fetchall()
            logger.info("New fields added:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
                
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_altitude_migration())
