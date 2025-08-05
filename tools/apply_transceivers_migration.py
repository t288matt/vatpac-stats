#!/usr/bin/env python3
"""
Apply transceivers table migration
Adds the transceivers table and related views to the database
"""

import os
import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from database import get_db, engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_transceivers_migration():
    """Apply the transceivers table migration"""
    try:
        # Read the SQL migration file
        migration_file = Path(__file__).parent / "create_transceivers_table.sql"
        
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            sql_script = f.read()
        
        # Split the script into individual statements
        statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
        
        # Execute each statement
        with engine.connect() as conn:
            for statement in statements:
                if statement:
                    logger.info(f"Executing: {statement[:100]}...")
                    conn.execute(text(statement))
                    conn.commit()
        
        logger.info("Transceivers migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error applying transceivers migration: {e}")
        return False

def verify_migration():
    """Verify that the transceivers table was created successfully"""
    try:
        with engine.connect() as conn:
            # Check if transceivers table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'transceivers'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                # Check if views were created
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.views 
                    WHERE view_name IN ('flights_with_transceivers', 'atc_with_transceivers', 'active_radio_frequencies');
                """))
                view_count = result.scalar()
                
                logger.info(f"Transceivers table exists: {table_exists}")
                logger.info(f"Related views created: {view_count}/3")
                
                return table_exists and view_count == 3
            else:
                logger.error("Transceivers table was not created")
                return False
                
    except Exception as e:
        logger.error(f"Error verifying migration: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting transceivers migration...")
    
    if apply_transceivers_migration():
        logger.info("Migration applied successfully")
        
        if verify_migration():
            logger.info("Migration verified successfully")
        else:
            logger.error("Migration verification failed")
            sys.exit(1)
    else:
        logger.error("Migration failed")
        sys.exit(1) 