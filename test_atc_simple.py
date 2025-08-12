#!/usr/bin/env python3
"""
Simple ATC Detection Test Script

This script tests the ATC detection service step by step to identify performance issues.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, "/app")

from app.services.atc_detection_service import ATCDetectionService
from app.database import get_database_session
from sqlalchemy import text
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_database_connection():
    """Test basic database connectivity."""
    try:
        logger.info("Testing database connection...")
        async with get_database_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM flight_summaries"))
            count = result.scalar()
            logger.info(f"Database connection successful. Flight summaries count: {count}")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

async def test_transceivers_query():
    """Test the transceivers query performance."""
    try:
        logger.info("Testing transceivers query...")
        async with get_database_session() as session:
            # Test flight transceivers query
            start_time = asyncio.get_event_loop().time()
            result = await session.execute(text("""
                SELECT COUNT(*) FROM transceivers 
                WHERE entity_type = 'flight' 
                AND callsign = 'QFA1'
            """))
            flight_count = result.scalar()
            flight_time = asyncio.get_event_loop().time() - start_time
            
            # Test ATC transceivers query
            start_time = asyncio.get_event_loop().time()
            result = await session.execute(text("""
                SELECT COUNT(*) FROM transceivers t
                INNER JOIN controllers c ON t.callsign = c.callsign
                WHERE t.entity_type = 'atc' 
                AND c.facility != 0
            """))
            atc_count = result.scalar()
            atc_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"Flight transceivers: {flight_count} records in {flight_time:.3f}s")
            logger.info(f"ATC transceivers: {atc_count} records in {atc_time:.3f}s")
            return True
    except Exception as e:
        logger.error(f"Transceivers query failed: {e}")
        return False

async def test_atc_service():
    """Test the ATC detection service with timeout."""
    try:
        logger.info("Testing ATC detection service...")
        service = ATCDetectionService()
        
        # Set a timeout for the ATC detection
        try:
            result = await asyncio.wait_for(
                service.detect_flight_atc_interactions(
                    'QFA1', 'YSSY', 'WSSS', 
                    datetime(2025, 8, 11, 10, 5, 41, tzinfo=timezone.utc)
                ),
                timeout=30.0  # 30 second timeout
            )
            logger.info(f"ATC Detection completed: {result}")
            return True
        except asyncio.TimeoutError:
            logger.error("ATC Detection timed out after 30 seconds")
            return False
            
    except Exception as e:
        logger.error(f"ATC service test failed: {e}")
        return False

async def main():
    """Main test function."""
    logger.info("Starting ATC detection tests...")
    
    # Test 1: Database connection
    if not await test_database_connection():
        logger.error("Database connection test failed")
        return
    
    # Test 2: Transceivers queries
    if not await test_transceivers_query():
        logger.error("Transceivers query test failed")
        return
    
    # Test 3: ATC service
    if not await test_atc_service():
        logger.error("ATC service test failed")
        return
    
    logger.info("All tests completed successfully")

if __name__ == "__main__":
    asyncio.run(main())
