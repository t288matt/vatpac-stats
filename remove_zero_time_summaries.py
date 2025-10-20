import asyncio
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from app.database import get_database_session
from app.utils.logging import get_logger_for_module

logger = get_logger_for_module(__name__)

async def remove_zero_time_summaries():
    """
    Removes flight summaries where time_online_minutes is 0.
    """
    logger.info("🔍 Identifying and removing flight summaries with time_online_minutes = 0...")

    async with get_database_session() as session:
        # First, count how many summaries have time_online_minutes = 0
        count_query = text("SELECT COUNT(*) FROM flight_summaries WHERE time_online_minutes = 0;")
        count_result = await session.execute(count_query)
        total_zero_summaries = count_result.scalar_one()
        logger.info(f"Found {total_zero_summaries} flight summaries with time_online_minutes = 0.")

        if total_zero_summaries == 0:
            logger.info("No summaries with 0 online minutes found. Exiting.")
            return

        # Get a sample of these summaries before deletion
        sample_query = text("""
            SELECT id, callsign, logon_time, completion_time, time_online_minutes
            FROM flight_summaries
            WHERE time_online_minutes = 0
            ORDER BY created_at DESC
            LIMIT 5;
        """)
        sample_result = await session.execute(sample_query)
        sample_summaries = sample_result.fetchall()
        logger.info("Sample of summaries to be deleted:")
        for s in sample_summaries:
            logger.info(f"  ID: {s.id}, Callsign: {s.callsign}, Logon: {s.logon_time}, Completion: {s.completion_time}, Time Online: {s.time_online_minutes}")

        # Confirm deletion
        confirm = input(f"Are you sure you want to delete all {total_zero_summaries} flight summaries with 0 online minutes? (yes/no): ")
        if confirm.lower() != 'yes':
            logger.info("Deletion cancelled by user.")
            return

        # Delete summaries with time_online_minutes = 0
        delete_query = text("DELETE FROM flight_summaries WHERE time_online_minutes = 0;")
        delete_result = await session.execute(delete_query)
        await session.commit()
        logger.info(f"Successfully deleted {delete_result.rowcount} flight summaries with 0 online minutes.")

        # Log that scheduled processing will recreate them
        logger.info("The next scheduled flight summary processing will recreate these summaries correctly.")
        logger.info("Verification step: After the next processing cycle, check flight_summaries table for recreated records.")

if __name__ == "__main__":
    asyncio.run(remove_zero_time_summaries())