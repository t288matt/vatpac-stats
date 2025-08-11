#!/usr/bin/env python3
"""
Database Migration Runner
Executes migration 001_alter_transceiver_frequency_to_bigint.sql
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
from datetime import datetime

# Add the app directory to the path so we can import database
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from database import DATABASE_URL
except ImportError:
    print("Error: Could not import database. Make sure you're running from the project root.")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def check_current_schema(conn):
    """Check current schema before migration"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'transceivers' AND column_name = 'frequency'
        """)
        result = cursor.fetchone()
        if result:
            logger.info(f"Current frequency column: {result}")
            return result[1]  # Return data_type
        else:
            logger.error("Frequency column not found in transceivers table")
            return None
    finally:
        cursor.close()

def run_migration(conn):
    """Run the migration"""
    cursor = conn.cursor()
    migration_file = os.path.join(os.path.dirname(__file__), '001_alter_transceiver_frequency_to_bigint.sql')
    
    try:
        # Read migration SQL
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        logger.info("Starting migration: alter_transceiver_frequency_to_bigint")
        
        # Execute migration
        cursor.execute(migration_sql)
        
        logger.info("Migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    finally:
        cursor.close()

def verify_migration(conn):
    """Verify the migration was successful"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'transceivers' AND column_name = 'frequency'
        """)
        result = cursor.fetchone()
        if result and result[1] == 'bigint':
            logger.info("✅ Migration verification successful: frequency column is now BIGINT")
            return True
        else:
            logger.error(f"❌ Migration verification failed: frequency column is {result[1] if result else 'not found'}")
            return False
    finally:
        cursor.close()

def main():
    """Main migration execution"""
    logger.info("=" * 60)
    logger.info("Starting Database Migration: INTEGER to BIGINT for transceiver frequency")
    logger.info("=" * 60)
    
    conn = None
    try:
        # Connect to database
        conn = get_connection()
        logger.info("Connected to database successfully")
        
        # Check current schema
        current_type = check_current_schema(conn)
        if not current_type:
            logger.error("Cannot proceed with migration")
            return False
        
        if current_type == 'bigint':
            logger.info("Frequency column is already BIGINT. No migration needed.")
            return True
        
        if current_type != 'integer':
            logger.warning(f"Unexpected column type: {current_type}. Proceeding with caution.")
        
        # Run migration
        if run_migration(conn):
            # Verify migration
            if verify_migration(conn):
                logger.info("🎉 Migration completed and verified successfully!")
                return True
            else:
                logger.error("Migration completed but verification failed!")
                return False
        else:
            logger.error("Migration failed!")
            return False
            
    except Exception as e:
        logger.error(f"Migration process failed: {e}")
        return False
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
