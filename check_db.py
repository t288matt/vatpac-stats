#!/usr/bin/env python
import asyncio
import json
from sqlalchemy import text
from app.database import get_database_session

async def check_flights():
    async with get_database_session() as session:
        print('Connected to database')
        
        # Get counts by enrichment status
        result = await session.execute(text("""
            SELECT enrichment_status, COUNT(*) 
            FROM flight_summaries 
            GROUP BY enrichment_status
        """))
        rows = result.fetchall()
        print(json.dumps({row[0]: row[1] for row in rows}, indent=2))
        
        # Check for pending flights with NULL completion time
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries 
            WHERE enrichment_status = 'pending' 
            AND completion_time IS NULL
        """))
        count = result.scalar()
        print(f'Pending flights with NULL completion_time: {count}')
        
        # Check for pending flights with NON-NULL completion time
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries 
            WHERE enrichment_status = 'pending' 
            AND completion_time IS NOT NULL
        """))
        count = result.scalar()
        print(f'Pending flights with NON-NULL completion_time: {count}')
        
        # Check for wait_for_completion flights with NULL completion time
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries 
            WHERE enrichment_status = 'wait_for_completion' 
            AND completion_time IS NULL
        """))
        count = result.scalar()
        print(f'Wait-for-completion flights with NULL completion_time: {count}')
        
        # Check for wait_for_completion flights with NON-NULL completion time
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries 
            WHERE enrichment_status = 'wait_for_completion' 
            AND completion_time IS NOT NULL
        """))
        count = result.scalar()
        print(f'Wait-for-completion flights with NON-NULL completion_time: {count}')
        
        # Check for in_progress flights
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries 
            WHERE enrichment_status = 'in_progress'
        """))
        count = result.scalar()
        print(f'In-progress flights: {count}')
        
        # Look for the recent automatic transitions
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries
            WHERE enrichment_status = 'pending'
            AND updated_at > NOW() - INTERVAL '30 minutes'
            AND (enrichment_last_error LIKE '%wait_for_completion%' OR enrichment_last_error LIKE '%completion_time%')
        """))
        count = result.scalar()
        print(f'Recent automatic transitions: {count}')

async def main():
    await check_flights()

if __name__ == "__main__":
    asyncio.run(main())


