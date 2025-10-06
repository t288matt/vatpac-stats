#!/usr/bin/env python3
"""
Validation script for THY3PT flight data

This script checks the database record for flight THY3PT from YPAM to YBTL
and validates time calculations and sector breakdown inconsistencies.
"""
import asyncio
import json
import logging
from datetime import datetime
from sqlalchemy import text
from app.database import get_database_session

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

async def validate_flight():
    """Validate flight data for THY3PT and identify issues."""
    async with get_database_session() as session:
        # Get the flight summary
        result = await session.execute(text("""
            SELECT 
                id, callsign, departure, arrival, logon_time, completion_time,
                time_online_minutes, total_enroute_time_minutes, sector_breakdown,
                aircraft_short, enrichment_status, enrichment_attempts,
                enrichment_completed_at, enrichment_last_error
            FROM flight_summaries 
            WHERE callsign = 'THY3PT'
            ORDER BY id DESC
            LIMIT 5
        """))
        flight = result.fetchone()
        
        if not flight:
            logger.error("Flight THY3PT not found in database")
            return
            
        # Calculate expected duration
        expected_duration = None
        if flight.logon_time and flight.completion_time:
            expected_duration = flight.completion_time - flight.logon_time
            expected_minutes = expected_duration.total_seconds() / 60
        else:
            expected_minutes = None
            
        # Calculate sector time sum
        sector_data = {}
        sector_minutes_sum = 0
        if flight.sector_breakdown:
            try:
                sector_data = json.loads(flight.sector_breakdown)
                sector_minutes_sum = sum(int(v) for v in sector_data.values())
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing sector_breakdown: {e}")
        
        # Output validation results
        logger.info(f"\n{'='*50}")
        logger.info(f"FLIGHT VALIDATION: {flight.callsign} - {flight.departure} to {flight.arrival}")
        logger.info(f"{'='*50}")
        logger.info(f"Database ID: {flight.id}")
        logger.info(f"Logon Time: {flight.logon_time}")
        logger.info(f"Completion Time: {flight.completion_time}")
        
        # Time validation
        logger.info("\nTIME VALIDATION:")
        logger.info(f"  Expected Duration: {expected_minutes:.1f} minutes" if expected_minutes else "  Expected Duration: Unknown")
        logger.info(f"  Recorded time_online_minutes: {flight.time_online_minutes}")
        if expected_minutes and flight.time_online_minutes is not None:
            discrepancy = expected_minutes - flight.time_online_minutes
            logger.info(f"  Discrepancy: {discrepancy:.1f} minutes")
            if abs(discrepancy) > 5:
                logger.error(f"  ERROR: Time online minutes is significantly off by {discrepancy:.1f} minutes")
            
        # Sector validation
        logger.info("\nSECTOR VALIDATION:")
        logger.info(f"  Sector Breakdown: {sector_data}")
        logger.info(f"  Sum of Sector Minutes: {sector_minutes_sum}")
        logger.info(f"  Recorded total_enroute_time_minutes: {flight.total_enroute_time_minutes}")
        if sector_minutes_sum > 0 and flight.total_enroute_time_minutes is not None:
            sector_discrepancy = sector_minutes_sum - flight.total_enroute_time_minutes
            logger.info(f"  Sector Time Discrepancy: {sector_discrepancy} minutes")
            if abs(sector_discrepancy) > 0:
                logger.error(f"  ERROR: Sector time total doesn't match the sector breakdown sum")
                
        # Check for empty aircraft_short
        logger.info("\nAIRCRAFT VALIDATION:")
        logger.info(f"  aircraft_short: '{flight.aircraft_short}'")
        if not flight.aircraft_short:
            logger.warning("  WARNING: aircraft_short field is empty")
            
        # Enrichment status
        logger.info("\nENRICHMENT STATUS:")
        logger.info(f"  Status: {flight.enrichment_status}")
        logger.info(f"  Attempts: {flight.enrichment_attempts}")
        logger.info(f"  Completed At: {flight.enrichment_completed_at}")
        logger.info(f"  Last Error: {flight.enrichment_last_error}")
        
        # RECOMMENDED FIX
        if (flight.time_online_minutes == 0 or 
            sector_minutes_sum != flight.total_enroute_time_minutes):
            
            logger.info("\nRECOMMENDED FIX SQL:")
            logger.info("```sql")
            logger.info("BEGIN;")
            
            # Fix time_online_minutes
            if flight.time_online_minutes == 0 and expected_minutes:
                logger.info(f"-- Fix time_online_minutes")
                logger.info(f"UPDATE flight_summaries")
                logger.info(f"SET time_online_minutes = {int(expected_minutes)}")
                logger.info(f"WHERE id = {flight.id};")
            
            # Fix total_enroute_time_minutes
            if sector_minutes_sum != flight.total_enroute_time_minutes:
                logger.info(f"-- Fix total_enroute_time_minutes to match sector breakdown")
                logger.info(f"UPDATE flight_summaries")
                logger.info(f"SET total_enroute_time_minutes = {sector_minutes_sum}")
                logger.info(f"WHERE id = {flight.id};")
            
            # Reset enrichment for aircraft_short
            if not flight.aircraft_short:
                logger.info(f"-- Reset enrichment status to fix aircraft_short")
                logger.info(f"UPDATE flight_summaries")
                logger.info(f"SET enrichment_status = 'pending',")
                logger.info(f"    enrichment_attempts = 0,")
                logger.info(f"    enrichment_run_after = NOW()")
                logger.info(f"WHERE id = {flight.id};")
            
            logger.info("COMMIT;")
            logger.info("```")
        else:
            logger.info("\nNO FIX NEEDED: All validations passed!")

async def main():
    """Main entry point."""
    logger.info("Starting validation for THY3PT flight")
    await validate_flight()
    logger.info("Validation completed")

if __name__ == "__main__":
    asyncio.run(main())
