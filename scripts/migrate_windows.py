#!/usr/bin/env python3
"""
Simplified PostgreSQL Migration for Windows

This script provides a simplified migration process for Windows users
who have PostgreSQL installed manually.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_postgresql_installation():
    """Check if PostgreSQL is installed and accessible"""
    try:
        import psycopg2
        logger.info("psycopg2 is available")
        return True
    except ImportError:
        logger.error("psycopg2 is not installed. Please run: pip install psycopg2-binary")
        return False

def create_database_connection():
    """Create database connection string for Windows"""
    
    # Default connection parameters
    db_host = "localhost"
    db_port = "5432"
    db_name = "vatsim_data"
    db_user = "postgres"  # Default PostgreSQL user
    db_password = "postgres"  # Default password
    
    # Try to get from environment or user input
    db_password = os.getenv("POSTGRES_PASSWORD", db_password)
    
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Test connection
    try:
        import psycopg2
        conn = psycopg2.connect(connection_string)
        conn.close()
        logger.info("Database connection successful")
        return connection_string
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.info("Please ensure PostgreSQL is running and accessible")
        logger.info("You may need to:")
        logger.info("1. Install PostgreSQL from https://www.postgresql.org/download/windows/")
        logger.info("2. Create a database named 'vatsim_data'")
        logger.info("3. Set the POSTGRES_PASSWORD environment variable")
        return None

def create_env_file(connection_string):
    """Create .env file with database configuration"""
    env_content = f"""
# Database Configuration
DATABASE_URL={connection_string}

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
"""
    
    env_file = Path(".env")
    with open(env_file, "w") as f:
        f.write(env_content.strip())
    
    logger.info("Created .env file with database configuration")

def run_migration():
    """Run the migration process"""
    try:
        # Check PostgreSQL installation
        if not check_postgresql_installation():
            return False
        
        # Create database connection
        connection_string = create_database_connection()
        if not connection_string:
            return False
        
        # Create .env file
        create_env_file(connection_string)
        
        # Import and run the main migration
        from migrate_to_postgresql import PostgreSQLMigrator
        
        sqlite_path = "atc_optimization.db"
        if not os.path.exists(sqlite_path):
            logger.error(f"SQLite database not found: {sqlite_path}")
            return False
        
        # Run migration
        migrator = PostgreSQLMigrator(sqlite_path, connection_string)
        migrator.run_migration()
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting PostgreSQL migration for Windows...")
    
    if run_migration():
        logger.info("Migration completed successfully!")
        logger.info("You can now run your application with PostgreSQL")
    else:
        logger.error("Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 