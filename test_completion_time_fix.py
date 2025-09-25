#!/usr/bin/env python3
"""
Test script to verify the completion time fix for JST780
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_database_session
from app.services.data_service import DataService
from sqlalchemy import text

async def test_completion_time_fix():
    """Test the completion time fix for JST780"""
    
    # Test parameters for JST780
    callsign = "JST780"
    departure = "YMML"
    arrival = "YPAD"
    cid = 1638887
    deptime = "0733"
    
    print(f"Testing completion time fix for {callsign}")
    print(f"Parameters: {departure} -> {arrival}, CID={cid}, deptime={deptime}")
    print()
    
    async with get_database_session() as session:
        # Test the new method
        data_service = DataService()
        actual_completion_time = await data_service._get_actual_completion_time_from_flights(
            callsign, departure, arrival, cid, deptime, session
        )
        
        print(f"✅ Actual completion time from flights table: {actual_completion_time}")
        
        # Compare with current flight summary
        result = await session.execute(text("""
            SELECT completion_time, created_at 
            FROM flight_summaries 
            WHERE callsign = :callsign 
            AND departure = :departure 
            AND arrival = :arrival 
            AND cid = :cid
            AND deptime = :deptime
            ORDER BY created_at DESC 
            LIMIT 1
        """), {
            "callsign": callsign,
            "departure": departure,
            "arrival": arrival,
            "cid": cid,
            "deptime": deptime
        })
        
        row = result.fetchone()
        if row:
            print(f"❌ Current flight summary completion_time: {row.completion_time}")
            print(f"📅 Flight summary created_at: {row.created_at}")
            
            # Calculate the difference
            if actual_completion_time and row.completion_time:
                diff_minutes = (actual_completion_time - row.completion_time).total_seconds() / 60
                print(f"⏰ Difference: {diff_minutes:.1f} minutes")
                
                if diff_minutes > 0:
                    print(f"🎯 The fix would add {diff_minutes:.1f} minutes of flight data!")
                else:
                    print("⚠️  No improvement expected")
        else:
            print("❌ No flight summary found")
        
        # Show the altitude data around the completion times
        print("\n📊 Altitude data around completion times:")
        
        # Current completion time
        if row and row.completion_time:
            result = await session.execute(text("""
                SELECT last_updated, altitude 
                FROM flights 
                WHERE callsign = :callsign 
                AND departure = :departure 
                AND arrival = :arrival 
                AND cid = :cid
                AND deptime = :deptime
                AND last_updated BETWEEN :start AND :end
                ORDER BY last_updated
            """), {
                "callsign": callsign,
                "departure": departure,
                "arrival": arrival,
                "cid": cid,
                "deptime": deptime,
                "start": row.completion_time - timedelta(minutes=5),
                "end": row.completion_time + timedelta(minutes=5)
            })
            
            print(f"\nAround current completion_time ({row.completion_time}):")
            for r in result.fetchall():
                print(f"  {r.last_updated}: {r.altitude}ft")
        
        # Actual completion time
        if actual_completion_time:
            result = await session.execute(text("""
                SELECT last_updated, altitude 
                FROM flights 
                WHERE callsign = :callsign 
                AND departure = :departure 
                AND arrival = :arrival 
                AND cid = :cid
                AND deptime = :deptime
                AND last_updated BETWEEN :start AND :end
                ORDER BY last_updated
            """), {
                "callsign": callsign,
                "departure": departure,
                "arrival": arrival,
                "cid": cid,
                "deptime": deptime,
                "start": actual_completion_time - timedelta(minutes=5),
                "end": actual_completion_time + timedelta(minutes=5)
            })
            
            print(f"\nAround actual completion_time ({actual_completion_time}):")
            for r in result.fetchall():
                print(f"  {r.last_updated}: {r.altitude}ft")

if __name__ == "__main__":
    from datetime import timedelta
    asyncio.run(test_completion_time_fix())

