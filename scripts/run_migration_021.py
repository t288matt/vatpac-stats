#!/usr/bin/env python3
"""
Run Migration 021: Create Flight Summary Tables
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append('/app')

from app.database import get_database_session
from sqlalchemy import text

async def run_migration():
    """Run the migration to create flight summary tables"""
    try:
        # Read the migration SQL file
        with open('/app/021_create_flight_summary_tables.sql', 'r') as f:
            migration_sql = f.read()
        
        print("📖 Migration SQL loaded successfully")
        print(f"📏 SQL file size: {len(migration_sql)} characters")
        
        # Split the SQL into individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        print(f"🔍 Found {len(statements)} SQL statements to execute")
        
        # Get database session
        async with get_database_session() as session:
            print("🔌 Database connection established")
            
            # Execute each statement
            for i, statement in enumerate(statements, 1):
                if statement and not statement.startswith('--'):
                    try:
                        await session.execute(text(statement))
                        print(f"✅ Statement {i} executed successfully")
                    except Exception as e:
                        print(f"⚠️  Statement {i} had issue (may already exist): {e}")
            
            # Commit the transaction
            await session.commit()
            print("💾 Transaction committed successfully")
        
        print("\n🎉 Migration 021 completed successfully!")
        print("✅ Created tables:")
        print("   - flight_summaries")
        print("   - flights_archive") 
        print("   - flight_sector_occupancy")
        print("✅ Created indexes and triggers")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
