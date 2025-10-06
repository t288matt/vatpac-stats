#!/usr/bin/env python
"""Check flight completion processing status.

This script checks the current state of flight completion processing:
- Counts of flights in different enrichment_status states
- Checks for flights with mismatched completion_time and enrichment_status
"""
import asyncio
import logging
from sqlalchemy import text
from app.database import get_database_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_flight_completion_status():
    """Check the status of flight completion processing."""
    async with get_database_session() as session:
        # Count flights in each enrichment status
        result = await session.execute(text("""
            SELECT 
                enrichment_status, 
                COUNT(*) as count,
                COUNT(CASE WHEN completion_time IS NOT NULL THEN 1 END) as with_completion,
                COUNT(CASE WHEN completion_time IS NULL THEN 1 END) as without_completion
            FROM flight_summaries
            GROUP BY enrichment_status
            ORDER BY enrichment_status
        """))
        status_counts = result.fetchall()
        
        logger.info("Flight summary enrichment status counts:")
        logger.info("----------------------------------------")
        for status in status_counts:
            logger.info(f"Status: {status.enrichment_status}, Count: {status.count} " +
                       f"(With completion: {status.with_completion}, " +
                       f"Without completion: {status.without_completion})")
        
        # Check for anomalies - wait_for_completion flights with completion_time set
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries
            WHERE enrichment_status = 'wait_for_completion'
            AND completion_time IS NOT NULL
        """))
        anomaly_count = result.scalar()
        logger.info(f"\nAnomalies found: {anomaly_count} wait_for_completion flights with completion_time already set")
        
        if anomaly_count > 0:
            # Show sample of anomalous flights
            result = await session.execute(text("""
                SELECT id, callsign, departure, arrival, logon_time, completion_time,
                       enrichment_status, enrichment_attempts, enrichment_last_error
                FROM flight_summaries
                WHERE enrichment_status = 'wait_for_completion'
                AND completion_time IS NOT NULL
                ORDER BY completion_time DESC
                LIMIT 10
            """))
            anomalies = result.fetchall()
            
            logger.info("\nSample of anomalous flights:")
            logger.info("--------------------------")
            for flight in anomalies:
                logger.info(f"ID: {flight.id}, Callsign: {flight.callsign}, " +
                           f"Status: {flight.enrichment_status}, " +
                           f"Completion time: {flight.completion_time}")
                
        # Check pending flights to see if they have completion times
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries
            WHERE enrichment_status = 'pending'
            AND completion_time IS NOT NULL
        """))
        pending_with_completion = result.scalar()
        
        logger.info(f"\nPending flights with completion_time set: {pending_with_completion}")
        
        # Check if the automatic transition from wait_for_completion to pending is working
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries
            WHERE enrichment_status = 'wait_for_completion'
            AND completion_time IS NOT NULL
            AND updated_at < NOW() - INTERVAL '10 minutes'
        """))
        stuck_transitions = result.scalar()
        
        logger.info(f"\nStuck transitions: {stuck_transitions} wait_for_completion flights " +
                   "with completion_time set more than 10 minutes ago")

        # Check for recent automatic transitions (should be 0 if not working)
        result = await session.execute(text("""
            SELECT COUNT(*) 
            FROM flight_summaries
            WHERE enrichment_status = 'pending'
            AND updated_at > NOW() - INTERVAL '30 minutes'
            AND enrichment_last_error LIKE '%wait_for_completion%'
        """))
        recent_transitions = result.scalar()
        
        logger.info(f"\nRecent automatic transitions: {recent_transitions} flights transitioned " +
                   "from wait_for_completion to pending in the last 30 minutes")

async def main():
    logger.info("Checking flight completion processing status...")
    await check_flight_completion_status()
    logger.info("Check complete.")

if __name__ == "__main__":
    asyncio.run(main())


