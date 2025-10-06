#!/usr/bin/env python3
"""
Validation script for flight THY3PT with data quality issues.

This script validates the flight data for THY3PT from YPAM to YBTL,
focusing on the discrepancies in time calculations and sector breakdowns.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from app.database import get_database_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
              AND departure = 'YPAM' 
              AND arrival = 'YBTL'
              AND completion_time IS NOT NULL
            ORDER BY updated_at DESC 
            LIMIT 1
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
        if sector_minutes_sum and flight.total_enroute_time_minutes is not None:
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
        
        # Check underlying flight_sector_occupancy records
        logger.info("\nSECTOR OCCUPANCY RECORDS:")
        sector_result = await session.execute(text("""
            SELECT 
                sector_name,
                entry_timestamp,
                exit_timestamp,
                duration_seconds
            FROM flight_sector_occupancy
            WHERE callsign = :callsign
              AND entry_timestamp >= :logon_time
              AND (exit_timestamp <= :completion_time OR exit_timestamp IS NULL)
            ORDER BY entry_timestamp
        """), {
            "callsign": flight.callsign,
            "logon_time": flight.logon_time,
            "completion_time": flight.completion_time
        })
        
        sectors = sector_result.fetchall()
        logger.info(f"  Found {len(sectors)} sector occupancy records:")
        total_seconds = 0
        for idx, sector in enumerate(sectors):
            duration = sector.duration_seconds if sector.duration_seconds is not None else 0
            total_seconds += duration
            logger.info(f"  {idx+1}. Sector: {sector.sector_name}")
            logger.info(f"     Entry: {sector.entry_timestamp}")
            logger.info(f"     Exit: {sector.exit_timestamp}")
            logger.info(f"     Duration: {duration} seconds ({duration/60:.1f} minutes)")
            
        total_minutes = total_seconds / 60
        logger.info(f"\n  Total sector time from occupancy records: {total_minutes:.1f} minutes")
        if total_minutes > 0 and flight.total_enroute_time_minutes is not None:
            logger.info(f"  Comparison to total_enroute_time_minutes: {flight.total_enroute_time_minutes} minutes")
            diff = total_minutes - flight.total_enroute_time_minutes
            logger.info(f"  Difference: {diff:.1f} minutes")
        
        # Check if we need to reset this flight for reprocessing
        if (flight.enrichment_status == 'completed' and 
            (flight.time_online_minutes == 0 or 
             flight.time_online_minutes is None or
             (sector_minutes_sum > 0 and flight.total_enroute_time_minutes != sector_minutes_sum))):
            logger.info("\n\nRECOMMENDED ACTION:")
            logger.info("  This flight summary appears to have data consistency issues.")
            logger.info("  Recommended to reset it for reprocessing by running:")
            logger.info("  UPDATE flight_summaries SET")
            logger.info("    enrichment_status = 'pending',")
            logger.info("    enrichment_attempts = 0,") 
            logger.info("    enrichment_run_after = NOW(),")
            logger.info("    enrichment_last_error = 'Reset due to data validation issues',")
            logger.info("    updated_at = NOW()")
            logger.info(f"  WHERE id = {flight.id};")

async def main():
    """Main entry point."""
    logger.info("Starting validation for THY3PT flight")
    await validate_flight()
    logger.info("Validation completed")

if __name__ == "__main__":
    asyncio.run(main())






