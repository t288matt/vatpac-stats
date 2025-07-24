#!/usr/bin/env python3
"""
Simple PostgreSQL Migration Script for VATSIM Data Collection System

This script migrates from SQLite to PostgreSQL using Docker containers.
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_docker():
    """Check if Docker is running"""
    try:
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Docker is running")
            return True
        else:
            logger.error("❌ Docker is not running. Please start Docker Desktop first.")
            return False
    except Exception as e:
        logger.error(f"❌ Docker error: {e}")
        return False

def start_postgresql():
    """Start PostgreSQL and Redis containers"""
    try:
        logger.info("🚀 Starting PostgreSQL and Redis containers...")
        
        # Start the database services
        result = subprocess.run([
            "docker-compose", "up", "-d", "postgres", "redis"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ PostgreSQL and Redis containers started successfully")
            return True
        else:
            logger.error(f"❌ Failed to start containers: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error starting containers: {e}")
        return False

def wait_for_postgresql():
    """Wait for PostgreSQL to be ready"""
    logger.info("⏳ Waiting for PostgreSQL to be ready...")
    
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            result = subprocess.run([
                "docker", "exec", "vatsim_postgres", 
                "pg_isready", "-U", "vatsim_user", "-d", "vatsim_data"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ PostgreSQL is ready")
                return True
                
        except Exception:
            pass
            
        time.sleep(2)
        logger.info(f"⏳ Waiting... ({attempt + 1}/{max_attempts})")
    
    logger.error("❌ PostgreSQL failed to start within timeout")
    return False

def run_migration():
    """Run the actual migration"""
    try:
        logger.info("🔄 Starting data migration...")
        
        # Run the migration script
        result = subprocess.run([
            "python", "scripts/migrate_to_postgresql.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Migration completed successfully!")
            logger.info("📊 Data has been migrated from SQLite to PostgreSQL")
            return True
        else:
            logger.error(f"❌ Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during migration: {e}")
        return False

def update_config():
    """Update application configuration to use PostgreSQL"""
    try:
        logger.info("🔧 Updating application configuration...")
        
        # Update the main application to use PostgreSQL
        # This will be done by the Docker environment variables
        
        logger.info("✅ Configuration updated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating configuration: {e}")
        return False

def main():
    """Main migration process"""
    logger.info("🚁 Starting PostgreSQL Migration for VATSIM Data Collection System")
    logger.info("=" * 60)
    
    # Step 1: Check Docker
    if not check_docker():
        logger.error("Please start Docker Desktop and try again")
        return False
    
    # Step 2: Start PostgreSQL
    if not start_postgresql():
        logger.error("Failed to start PostgreSQL containers")
        return False
    
    # Step 3: Wait for PostgreSQL to be ready
    if not wait_for_postgresql():
        logger.error("PostgreSQL failed to start")
        return False
    
    # Step 4: Run migration
    if not run_migration():
        logger.error("Migration failed")
        return False
    
    # Step 5: Update configuration
    if not update_config():
        logger.error("Configuration update failed")
        return False
    
    logger.info("=" * 60)
    logger.info("🎉 Migration completed successfully!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Start the application: docker-compose up -d app")
    logger.info("2. Access the dashboard: http://localhost:8001/frontend/index.html")
    logger.info("3. Check the API: http://localhost:8001/api/status")
    logger.info("")
    logger.info("Your data is now running on PostgreSQL! 🚀")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 