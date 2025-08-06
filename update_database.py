#!/usr/bin/env python3
"""
Database Update Script for VATSIM Data Collection System

This script updates the database schema using SQLAlchemy models and handles
any necessary migrations for the VATSIM data collection system.

USAGE:
    python update_database.py

FEATURES:
- Creates all tables defined in models.py
- Handles schema updates and migrations
- Provides detailed logging of operations
- Validates database connectivity
"""

import sys
import os
import logging
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import init_db, get_database_info, engine, SessionLocal
from app.models import (
    Controller, Sector, Flight, TrafficMovement, FlightSummary, 
    MovementSummary, AirportConfig, Airports, SystemConfig, Event, 
    Transceiver, MovementDetectionConfig
)
from app.utils.logging import get_logger_for_module

# Configure logging
logger = get_logger_for_module(__name__)

def update_database():
    """Update database schema using SQLAlchemy models"""
    try:
        logger.info("Starting database update...")
        
        # Test database connection
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute("SELECT version()")
            version = result.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version}")
        
        # Initialize database (creates all tables)
        logger.info("Creating/updating database tables...")
        init_db()
        logger.info("Database tables created/updated successfully")
        
        # Verify tables exist
        logger.info("Verifying table creation...")
        inspector = engine.dialect.inspector(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'controllers', 'sectors', 'flights', 'traffic_movements',
            'flight_summaries', 'movement_summaries', 'airport_config',
            'airports', 'system_config', 'events', 'transceivers',
            'movement_detection_config'
        ]
        
        for table in expected_tables:
            if table in tables:
                logger.info(f"✓ Table '{table}' exists")
            else:
                logger.warning(f"✗ Table '{table}' not found")
        
        # Get database info
        logger.info("Getting database information...")
        db_info = get_database_info()
        logger.info(f"Database pool size: {db_info['pool_size']}")
        logger.info(f"Checked in connections: {db_info['checked_in']}")
        logger.info(f"Checked out connections: {db_info['checked_out']}")
        
        logger.info("Database update completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database update failed: {e}")
        return False

def run_migrations():
    """Run any additional migrations if needed"""
    try:
        logger.info("Running additional migrations...")
        
        # Check if we need to run the transceivers migration
        with engine.connect() as conn:
            # Check if transceivers table exists and has data
            result = conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'transceivers'")
            if result.fetchone()[0] == 0:
                logger.info("Transceivers table doesn't exist, creating...")
                # Import and run the transceivers migration
                from tools.apply_transceivers_migration import apply_transceivers_migration
                apply_transceivers_migration()
                logger.info("Transceivers migration completed")
            else:
                logger.info("Transceivers table already exists")
        
        logger.info("All migrations completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def main():
    """Main function to update the database"""
    print("=" * 60)
    print("VATSIM Data Collection System - Database Update")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Update database schema
    if not update_database():
        print("❌ Database update failed!")
        sys.exit(1)
    
    # Run additional migrations
    if not run_migrations():
        print("❌ Migration failed!")
        sys.exit(1)
    
    print()
    print("✅ Database update completed successfully!")
    print(f"Completed at: {datetime.now()}")
    print("=" * 60)

if __name__ == "__main__":
    main() 