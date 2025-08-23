#!/usr/bin/env python3
"""
Script to move controller summaries data to the controllers table.
This handles the mapping between controller_summaries and controllers schemas.
"""

import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path for imports
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

from app.config import get_config

async def move_controller_summaries_to_controllers():
    """Move all controller summaries to the controllers table."""
    
    # Get database URL from config
    config = get_config()
    database_url = config.database.url
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        # First, let's see how many controller summaries we have
        result = await conn.execute(text("SELECT COUNT(*) FROM controller_summaries"))
        count = result.scalar()
        print(f"Found {count} controller summaries to move")
        
        if count == 0:
            print("No controller summaries to move")
            return
        
        # Check if there are existing controllers to avoid duplicates
        result = await conn.execute(text("SELECT COUNT(*) FROM controllers"))
        existing_count = result.scalar()
        print(f"Existing controllers count: {existing_count}")
        
        # Insert controller summaries into controllers table
        # Map the fields appropriately between the two schemas
        # Since there's no unique constraint on callsign, we'll insert all records
        insert_query = """
        INSERT INTO controllers (
            callsign, cid, name, rating, facility, server, 
            logon_time, last_updated, created_at, updated_at
        )
        SELECT 
            cs.callsign,
            cs.cid,
            cs.name,
            cs.rating,
            cs.facility,
            cs.server,
            cs.session_start_time as logon_time,
            COALESCE(cs.session_end_time, NOW()) as last_updated,
            cs.created_at,
            cs.updated_at
        FROM controller_summaries cs
        """
        
        print("Moving controller summaries to controllers table...")
        await conn.execute(text(insert_query))
        
        # Verify the move
        result = await conn.execute(text("SELECT COUNT(*) FROM controllers"))
        controllers_count = result.scalar()
        print(f"Controllers table now contains {controllers_count} records")
        print(f"Added {controllers_count - existing_count} new controller records")
        
        # Show some sample data
        result = await conn.execute(text("""
            SELECT callsign, facility, rating, server, logon_time
            FROM controllers 
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        print("\nSample controllers data:")
        for row in result:
            print(f"  {row.callsign}: Facility {row.facility}, Rating {row.rating}, Server {row.server} - Logon: {row.logon_time}")
    
    await engine.dispose()
    print("\nController summaries moved successfully!")

if __name__ == "__main__":
    asyncio.run(move_controller_summaries_to_controllers())
