#!/usr/bin/env python3
"""
Check the structure of the flight_summaries table
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_database_session
from sqlalchemy import text

async def check_table_structure():
    """Check the structure of the flight_summaries table"""
    try:
        async with get_database_session() as session:
            result = await session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'flight_summaries' 
                ORDER BY ordinal_position
            """))
            rows = result.fetchall()
            
            print("Flight summaries table columns:")
            for row in rows:
                print(f"  {row[0]}: {row[1]}")
                
    except Exception as e:
        print(f"Error checking table structure: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_table_structure())






