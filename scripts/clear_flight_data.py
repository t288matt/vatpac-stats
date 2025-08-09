#!/usr/bin/env python3
"""
Database Cleanup Script - Clear Flight Data

This script deletes all data from flight-related tables while preserving
the airports table data. This is useful for testing or resetting the system.

TABLES TO CLEAR:
- flights
- controllers  
# - traffic_movements  # REMOVED: Traffic Analysis Service - Phase 4
- transceivers
- frequency_matches
- transceivers
- frequency_matches

TABLES TO PRESERVE:
- airports

USAGE:
    python scripts/clear_flight_data.py

WARNING: This will permanently delete all flight data!
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import DATABASE_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_connection():
    """Create database connection."""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        return engine, Session()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)


def get_table_row_counts(session):
    """Get row counts for all tables to show before/after."""
    tables = [
        'flights', 'controllers',  # 'traffic_movements',  # REMOVED: Traffic Analysis Service - Phase 4
        'transceivers', 'frequency_matches', 'airports'
    ]
    
    counts = {}
    for table in tables:
        try:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            counts[table] = count
        except Exception as e:
            logger.warning(f"Could not get count for table {table}: {e}")
            counts[table] = 0
    
    return counts


def clear_flight_data():
    """Clear all flight-related data from the database."""
    
    logger.info("Starting database cleanup...")
    
    # Connect to database
    engine, session = get_database_connection()
    
    try:
        # Get initial row counts
        logger.info("Getting initial row counts...")
        initial_counts = get_table_row_counts(session)
        
        # Tables to clear (in dependency order to avoid foreign key issues)
        tables_to_clear = [
            'frequency_matches',      # No dependencies
            'transceivers',          # No dependencies  
            # 'traffic_movements',   # REMOVED: Traffic Analysis Service - Phase 4
            'flights',               # No dependencies
            'controllers'            # No dependencies
        ]
        
        # Tables to preserve
        tables_to_preserve = ['airports']
        
        logger.info("Tables to clear:")
        for table in tables_to_clear:
            count = initial_counts.get(table, 0)
            logger.info(f"  - {table}: {count:,} rows")
        
        logger.info("Tables to preserve:")
        for table in tables_to_preserve:
            count = initial_counts.get(table, 0)
            logger.info(f"  - {table}: {count:,} rows")
        
        # Confirm with user
        total_to_delete = sum(initial_counts.get(table, 0) for table in tables_to_clear)
        logger.warning(f"About to delete {total_to_delete:,} total rows!")
        
        confirm = input("\nAre you sure you want to proceed? (yes/no): ").lower().strip()
        if confirm != 'yes':
            logger.info("Operation cancelled by user.")
            return
        
        # Clear tables in dependency order
        deleted_counts = {}
        for table in tables_to_clear:
            try:
                # Disable foreign key checks temporarily
                session.execute(text("SET session_replication_role = replica;"))
                
                # Delete all rows from table
                result = session.execute(text(f"DELETE FROM {table}"))
                deleted_count = result.rowcount
                deleted_counts[table] = deleted_count
                
                # Re-enable foreign key checks
                session.execute(text("SET session_replication_role = DEFAULT;"))
                
                logger.info(f"Cleared {table}: {deleted_count:,} rows deleted")
                
            except Exception as e:
                logger.error(f"Failed to clear table {table}: {e}")
                session.rollback()
                continue
        
        # Commit all changes
        session.commit()
        
        # Get final row counts
        logger.info("Getting final row counts...")
        final_counts = get_table_row_counts(session)
        
        # Report results
        logger.info("\n" + "="*50)
        logger.info("CLEANUP COMPLETED")
        logger.info("="*50)
        
        for table in tables_to_clear:
            initial = initial_counts.get(table, 0)
            final = final_counts.get(table, 0)
            deleted = deleted_counts.get(table, 0)
            logger.info(f"{table}: {initial:,} → {final:,} rows (deleted {deleted:,})")
        
        for table in tables_to_preserve:
            initial = initial_counts.get(table, 0)
            final = final_counts.get(table, 0)
            logger.info(f"{table}: {initial:,} → {final:,} rows (preserved)")
        
        total_deleted = sum(deleted_counts.values())
        logger.info(f"\nTotal rows deleted: {total_deleted:,}")
        logger.info("Database cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


def main():
    """Main function."""
    logger.info("Database Cleanup Script")
    logger.info("=" * 30)
    logger.warning("This script will delete ALL flight-related data!")
    logger.warning("Only the airports table will be preserved.")
    logger.info("=" * 30)
    
    # Check if we're in the right directory
    if not os.path.exists('app'):
        logger.error("Please run this script from the project root directory")
        sys.exit(1)
    
    # Check database connection
    try:
        engine, session = get_database_connection()
        session.close()
        engine.dispose()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)
    
    # Run cleanup
    clear_flight_data()


if __name__ == "__main__":
    main()
