#!/usr/bin/env python3
"""
Test script to verify PostgreSQL migration setup
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sqlite_database():
    """Test if SQLite database exists and is accessible"""
    try:
        import sqlite3
        
        db_path = "atc_optimization.db"
        if not os.path.exists(db_path):
            logger.error(f"SQLite database not found: {db_path}")
            return False
        
        # Test connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"SQLite database found with {len(tables)} tables: {tables}")
        
        # Check record counts
        for table in ['controllers', 'flights', 'traffic_movements']:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"Table {table}: {count} records")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"SQLite test failed: {e}")
        return False

def test_postgresql_connection():
    """Test PostgreSQL connection if available"""
    try:
        import psycopg2
        
        # Try to get connection string from environment
        db_url = os.getenv("DATABASE_URL")
        if not db_url or not db_url.startswith("postgresql://"):
            logger.info("No PostgreSQL DATABASE_URL found, skipping PostgreSQL test")
            return True
        
        # Test connection
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check version
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        logger.info(f"PostgreSQL connection successful: {version.split(',')[0]}")
        
        # Check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"PostgreSQL database has {len(tables)} tables: {tables}")
        
        conn.close()
        return True
        
    except ImportError:
        logger.warning("psycopg2 not installed. Run: pip install psycopg2-binary")
        return False
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        return False

def test_migration_scripts():
    """Test if migration scripts are available"""
    scripts = [
        "migrate_to_postgresql.py",
        "migrate_windows.py", 
        "setup_postgresql.py"
    ]
    
    for script in scripts:
        if os.path.exists(script):
            logger.info(f"✓ Migration script found: {script}")
        else:
            logger.warning(f"✗ Migration script missing: {script}")
    
    return True

def test_application_setup():
    """Test if application is configured for PostgreSQL migration"""
    try:
        from app.database import get_database_info
        
        db_info = get_database_info()
        logger.info(f"Database type: {db_info['database_type']}")
        logger.info(f"Connection pool size: {db_info['pool_size']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Application setup test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Testing PostgreSQL migration setup...")
    
    tests = [
        ("SQLite Database", test_sqlite_database),
        ("PostgreSQL Connection", test_postgresql_connection),
        ("Migration Scripts", test_migration_scripts),
        ("Application Setup", test_application_setup)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✓ {test_name} test passed")
            else:
                logger.error(f"✗ {test_name} test failed")
        except Exception as e:
            logger.error(f"✗ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("MIGRATION SETUP TEST RESULTS")
    logger.info("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Ready for PostgreSQL migration.")
        logger.info("\nNext steps:")
        logger.info("1. For Windows: python migrate_windows.py")
        logger.info("2. For Linux/macOS: python setup_postgresql.py && python migrate_to_postgresql.py")
        logger.info("3. Manual: Install PostgreSQL, create database, set DATABASE_URL")
    else:
        logger.error("❌ Some tests failed. Please fix issues before migration.")
        logger.info("\nCommon fixes:")
        logger.info("1. Install psycopg2: pip install psycopg2-binary")
        logger.info("2. Install PostgreSQL from https://www.postgresql.org/download/")
        logger.info("3. Create database 'vatsim_data'")
        logger.info("4. Set DATABASE_URL environment variable")

if __name__ == "__main__":
    main() 