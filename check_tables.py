#!/usr/bin/env python3
"""
Check what tables exist in the database
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append('/app')

from app.database import get_database_session
from sqlalchemy import text

async def check_tables():
    """Check what tables exist in the database"""
    try:
        async with get_database_session() as session:
            print("🔌 Database connection established")
            
            # Check if our new tables exist
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('flight_summaries', 'flights_archive', 'flight_sector_occupancy')
                ORDER BY table_name
            """))
            
            existing_tables = [row[0] for row in result.fetchall()]
            
            print(f"📋 Found {len(existing_tables)} flight summary tables:")
            for table in existing_tables:
                print(f"   ✅ {table}")
            
            # Check all tables to see what's there
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            
            all_tables = [row[0] for row in result.fetchall()]
            print(f"\n📊 Total tables in database: {len(all_tables)}")
            
            # Show tables that might be related
            flight_related = [t for t in all_tables if 'flight' in t.lower()]
            if flight_related:
                print(f"✈️  Flight-related tables: {', '.join(flight_related)}")
            
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(check_tables())
