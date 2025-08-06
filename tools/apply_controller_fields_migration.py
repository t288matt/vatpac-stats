#!/usr/bin/env python3
"""
Migration script to add missing VATSIM API fields to controllers table.
This adds the fields that map from VATSIM API to our database schema.
"""

import os
import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from database import SessionLocal, engine
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_migration():
    """Apply the controller fields migration"""
    try:
        # Read the migration SQL
        migration_file = Path(__file__).parent / "add_controller_fields_migration.sql"
        
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False
            
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Apply the migration
        with engine.connect() as connection:
            logger.info("Applying controller fields migration...")
            
            # Split the SQL into individual statements
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    logger.info(f"Executing: {statement[:50]}...")
                    connection.execute(text(statement))
            
            connection.commit()
            logger.info("Migration completed successfully!")
            
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def verify_migration():
    """Verify that the migration was applied correctly"""
    try:
        with SessionLocal() as db:
            # Check if the new columns exist
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'controllers' 
                AND column_name IN ('controller_id', 'controller_name', 'controller_rating')
                ORDER BY column_name
            """))
            
            columns = [row[0] for row in result.fetchall()]
            
            expected_columns = ['controller_id', 'controller_name', 'controller_rating']
            
            if set(columns) == set(expected_columns):
                logger.info("✅ Migration verification successful - all new columns exist")
                return True
            else:
                logger.error(f"❌ Migration verification failed - missing columns: {set(expected_columns) - set(columns)}")
                return False
                
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting controller fields migration...")
    
    if apply_migration():
        if verify_migration():
            logger.info("🎉 Migration completed and verified successfully!")
        else:
            logger.error("❌ Migration verification failed")
            sys.exit(1)
    else:
        logger.error("❌ Migration failed")
        sys.exit(1) 