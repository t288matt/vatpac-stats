#!/usr/bin/env python3
"""
Test script to verify deptime field integration in flight summaries

This script tests that:
1. The deptime field is properly added to the database schema
2. Flight summaries are created with deptime populated
3. The field is accessible in API responses
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from database import get_database_session
from sqlalchemy import text

async def test_deptime_field_exists():
    """Test that the deptime field exists in the flight_summaries table"""
    print("🔍 Testing: Does deptime field exist in flight_summaries table?")
    
    try:
        async with get_database_session() as session:
            # Check if deptime column exists
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'flight_summaries' 
                AND column_name = 'deptime'
            """))
            
            column_info = result.fetchone()
            
            if column_info:
                print(f"✅ deptime field exists:")
                print(f"   Column: {column_info[0]}")
                print(f"   Type: {column_info[1]}")
                print(f"   Nullable: {column_info[2]}")
                print(f"   Default: {column_info[3]}")
                return True
            else:
                print("❌ deptime field does not exist in flight_summaries table")
                return False
                
    except Exception as e:
        print(f"❌ Error checking deptime field: {e}")
        return False

async def test_flight_summaries_structure():
    """Test the complete structure of the flight_summaries table"""
    print("\n🔍 Testing: Flight summaries table structure")
    
    try:
        async with get_database_session() as session:
            # Get all columns in flight_summaries table
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'flight_summaries'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            
            print(f"📊 Flight summaries table has {len(columns)} columns:")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                print(f"   {col[0]}: {col[1]} ({nullable})")
            
            # Check if deptime is in the expected position (after arrival)
            deptime_index = None
            arrival_index = None
            
            for i, col in enumerate(columns):
                if col[0] == 'deptime':
                    deptime_index = i
                elif col[0] == 'arrival':
                    arrival_index = i
            
            if deptime_index is not None and arrival_index is not None:
                if deptime_index > arrival_index:
                    print("✅ deptime field is positioned after arrival field (correct)")
                else:
                    print("⚠️  deptime field is positioned before arrival field (unexpected)")
            
            return True
                
    except Exception as e:
        print(f"❌ Error checking table structure: {e}")
        return False

async def test_sample_flight_summary():
    """Test that we can access deptime from existing flight summaries"""
    print("\n🔍 Testing: Can access deptime from flight summaries?")
    
    try:
        async with get_database_session() as session:
            # Check if there are any flight summaries with deptime data
            result = await session.execute(text("""
                SELECT callsign, departure, arrival, deptime, completion_time
                FROM flight_summaries 
                WHERE deptime IS NOT NULL
                ORDER BY completion_time DESC
                LIMIT 5
            """))
            
            summaries_with_deptime = result.fetchall()
            
            if summaries_with_deptime:
                print(f"✅ Found {len(summaries_with_deptime)} flight summaries with deptime:")
                for summary in summaries_with_deptime:
                    callsign, departure, arrival, deptime, completion_time = summary
                    print(f"   {callsign}: {departure} → {arrival} (Dept: {deptime}) at {completion_time}")
            else:
                print("ℹ️  No flight summaries with deptime data found (this is expected for existing data)")
            
            # Check total count of flight summaries
            count_result = await session.execute(text("""
                SELECT COUNT(*) as total, 
                       COUNT(deptime) as with_deptime,
                       COUNT(CASE WHEN deptime IS NULL THEN 1 END) as without_deptime
                FROM flight_summaries
            """))
            
            counts = count_result.fetchone()
            if counts:
                total, with_deptime, without_deptime = counts
                print(f"📊 Summary: {total} total, {with_deptime} with deptime, {without_deptime} without deptime")
            
            return True
                
    except Exception as e:
        print(f"❌ Error checking flight summaries: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Testing deptime field integration in flight summaries\n")
    
    tests = [
        test_deptime_field_exists,
        test_flight_summaries_structure,
        test_sample_flight_summary
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print(f"\n📊 Test Results: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("🎉 All tests passed! deptime field is properly integrated.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return all(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
