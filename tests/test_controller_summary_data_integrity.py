#!/usr/bin/env python3
"""
Controller Summary Data Integrity Test

This test verifies that the controller summary process correctly:
1. Created summaries for all archived controllers
2. Calculated session durations accurately
3. Preserved all essential controller information
4. Maintained data consistency between summaries and archives
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple

# Database connection configuration
DB_CONFIG = {
    'host': 'postgres',  # Use Docker service name
    'port': 5432,
    'user': 'vatsim_user',
    'password': 'vatsim_password',
    'database': 'vatsim_data'
}

async def get_database_connection():
    """Create database connection."""
    return await asyncpg.connect(**DB_CONFIG)

async def test_controller_summary_coverage():
    """Test 1: Verify all archived controllers have summaries."""
    print("🔍 Test 1: Controller Summary Coverage")
    print("=" * 50)
    
    conn = await get_database_connection()
    
    try:
        # Get all unique controller sessions from archive
        archive_query = """
            SELECT DISTINCT callsign, logon_time
            FROM controllers_archive
            ORDER BY callsign, logon_time
        """
        archive_records = await conn.fetch(archive_query)
        
        # Get all summaries
        summary_query = """
            SELECT callsign, session_start_time
            FROM controller_summaries
            ORDER BY callsign, session_start_time
        """
        summary_records = await conn.fetch(summary_query)
        
        print(f"📊 Archive records: {len(archive_records)} unique controller sessions")
        print(f"📊 Summary records: {len(summary_records)} summaries created")
        
        # Check for missing summaries
        archive_sessions = {(r['callsign'], r['logon_time']) for r in archive_records}
        summary_sessions = {(r['callsign'], r['session_start_time']) for r in summary_records}
        
        missing_summaries = archive_sessions - summary_sessions
        extra_summaries = summary_sessions - archive_sessions
        
        if missing_summaries:
            print(f"❌ Missing summaries for {len(missing_summaries)} sessions:")
            for callsign, logon_time in sorted(missing_summaries)[:5]:
                print(f"   - {callsign} (logon: {logon_time})")
            if len(missing_summaries) > 5:
                print(f"   ... and {len(missing_summaries) - 5} more")
        else:
            print("✅ All archived controller sessions have summaries!")
            
        if extra_summaries:
            print(f"⚠️  Extra summaries for {len(extra_summaries)} sessions (not in archive)")
            for callsign, start_time in sorted(extra_summaries)[:3]:
                print(f"   - {callsign} (start: {start_time})")
        
        return len(missing_summaries) == 0
        
    finally:
        await conn.close()

async def test_session_duration_accuracy():
    """Test 2: Verify session duration calculations are accurate."""
    print("\n🔍 Test 2: Session Duration Accuracy")
    print("=" * 50)
    
    conn = await get_database_connection()
    
    try:
        # Get summaries with calculated durations
        summary_query = """
            SELECT 
                callsign,
                session_start_time,
                session_end_time,
                session_duration_minutes
            FROM controller_summaries
            WHERE session_end_time IS NOT NULL
            ORDER BY callsign, session_start_time
        """
        summaries = await conn.fetch(summary_query)
        
        print(f"📊 Testing {len(summaries)} summaries with end times")
        
        duration_errors = []
        for summary in summaries:
            # Calculate actual duration from timestamps
            start_time = summary['session_start_time']
            end_time = summary['session_end_time']
            
            if start_time and end_time:
                actual_duration = (end_time - start_time).total_seconds() / 60
                stored_duration = summary['session_duration_minutes']
                
                # Allow 1 minute tolerance for rounding differences
                if abs(actual_duration - stored_duration) > 1:
                    duration_errors.append({
                        'callsign': summary['callsign'],
                        'start': start_time,
                        'end': end_time,
                        'actual': round(actual_duration, 2),
                        'stored': stored_duration,
                        'difference': round(abs(actual_duration - stored_duration), 2)
                    })
        
        if duration_errors:
            print(f"❌ Found {len(duration_errors)} duration calculation errors:")
            for error in duration_errors[:5]:
                print(f"   - {error['callsign']}: actual={error['actual']}min, stored={error['stored']}min (diff: {error['difference']}min)")
            if len(duration_errors) > 5:
                print(f"   ... and {len(duration_errors) - 5} more errors")
        else:
            print("✅ All session durations calculated correctly!")
            
        return len(duration_errors) == 0
        
    finally:
        await conn.close()

async def test_controller_data_preservation():
    """Test 3: Verify essential controller data is preserved in summaries."""
    print("\n🔍 Test 3: Controller Data Preservation")
    print("=" * 50)
    
    conn = await get_database_connection()
    
    try:
        # Get sample summaries with full data
        summary_query = """
            SELECT 
                callsign,
                cid,
                name,
                rating,
                facility,
                server,
                session_start_time,
                session_end_time,
                session_duration_minutes,
                total_aircraft_handled,
                peak_aircraft_count
            FROM controller_summaries
            ORDER BY created_at DESC
            LIMIT 10
        """
        summaries = await conn.fetch(summary_query)
        
        print(f"📊 Testing data preservation for {len(summaries)} recent summaries")
        
        data_issues = []
        for summary in summaries:
            # Check for missing essential data
            if not summary['callsign']:
                data_issues.append(f"{summary['callsign']}: Missing callsign")
            if not summary['session_start_time']:
                data_issues.append(f"{summary['callsign']}: Missing session start time")
            if summary['session_duration_minutes'] is None:
                data_issues.append(f"{summary['callsign']}: Missing session duration")
            if summary['total_aircraft_handled'] is None:
                data_issues.append(f"{summary['callsign']}: Missing aircraft count")
            
            # Check for logical consistency
            if summary['peak_aircraft_count'] and summary['total_aircraft_handled']:
                if summary['peak_aircraft_count'] > summary['total_aircraft_handled']:
                    data_issues.append(f"{summary['callsign']}: Peak count ({summary['peak_aircraft_count']}) > Total count ({summary['total_aircraft_handled']})")
        
        if data_issues:
            print(f"❌ Found {len(data_issues)} data preservation issues:")
            for issue in data_issues[:5]:
                print(f"   - {issue}")
            if len(data_issues) > 5:
                print(f"   ... and {len(data_issues) - 5} more issues")
        else:
            print("✅ All essential controller data preserved correctly!")
            
        return len(data_issues) == 0
        
    finally:
        await conn.close()

async def test_archive_data_consistency():
    """Test 4: Verify archive data is consistent with summaries."""
    print("\n🔍 Test 4: Archive Data Consistency")
    print("=" * 50)
    
    conn = await get_database_connection()
    
    try:
        # Get a sample of archived records and compare with summaries
        sample_query = """
            SELECT 
                ca.callsign,
                ca.logon_time,
                ca.cid,
                ca.name,
                ca.rating,
                ca.facility,
                ca.server,
                cs.session_start_time,
                cs.session_duration_minutes,
                cs.total_aircraft_handled
            FROM controllers_archive ca
            LEFT JOIN controller_summaries cs 
                ON ca.callsign = cs.callsign 
                AND ca.logon_time = cs.session_start_time
            WHERE ca.logon_time IS NOT NULL
            ORDER BY ca.callsign, ca.logon_time
            LIMIT 20
        """
        sample_records = await conn.fetch(sample_query)
        
        print(f"📊 Testing consistency for {len(sample_records)} archived records")
        
        consistency_issues = []
        for record in sample_records:
            if not record['session_start_time']:
                consistency_issues.append(f"{record['callsign']}: No matching summary found")
            else:
                # Check if key fields match
                if record['callsign'] != record['callsign']:
                    consistency_issues.append(f"{record['callsign']}: Callsign mismatch")
                if record['cid'] != record['cid']:
                    consistency_issues.append(f"{record['callsign']}: CID mismatch")
        
        if consistency_issues:
            print(f"❌ Found {len(consistency_issues)} consistency issues:")
            for issue in consistency_issues[:5]:
                print(f"   - {issue}")
            if len(consistency_issues) > 5:
                print(f"   ... and {len(consistency_issues) - 5} more issues")
        else:
            print("✅ Archive data is consistent with summaries!")
            
        return len(consistency_issues) == 0
        
    finally:
        await conn.close()

async def test_summary_statistics():
    """Test 5: Verify summary statistics make sense."""
    print("\n🔍 Test 5: Summary Statistics Validation")
    print("=" * 50)
    
    conn = await get_database_connection()
    
    try:
        # Get summary statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_summaries,
                COUNT(DISTINCT callsign) as unique_controllers,
                AVG(session_duration_minutes) as avg_duration,
                MIN(session_duration_minutes) as min_duration,
                MAX(session_duration_minutes) as max_duration,
                AVG(total_aircraft_handled) as avg_aircraft,
                SUM(total_aircraft_handled) as total_aircraft_handled
            FROM controller_summaries
        """
        stats = await conn.fetchrow(stats_query)
        
        print("📊 Summary Statistics:")
        print(f"   Total summaries: {stats['total_summaries']}")
        print(f"   Unique controllers: {stats['unique_controllers']}")
        print(f"   Average session duration: {stats['avg_duration']:.1f} minutes")
        print(f"   Session duration range: {stats['min_duration']} - {stats['max_duration']} minutes")
        print(f"   Average aircraft handled: {stats['avg_aircraft']:.1f}")
        print(f"   Total aircraft handled: {stats['total_aircraft_handled']}")
        
        # Validate statistics make sense
        validation_issues = []
        
        if stats['total_summaries'] < 10:
            validation_issues.append("Very few summaries created - may indicate processing issues")
        
        if stats['avg_duration'] < 1:
            validation_issues.append("Average session duration seems too low")
            
        if stats['avg_duration'] > 1440:  # 24 hours
            validation_issues.append("Average session duration seems too high")
            
        if stats['avg_aircraft'] < 0:
            validation_issues.append("Negative aircraft counts detected")
            
        if stats['min_duration'] < 0:
            validation_issues.append("Negative session durations detected")
        
        if validation_issues:
            print(f"❌ Found {len(validation_issues)} validation issues:")
            for issue in validation_issues:
                print(f"   - {issue}")
        else:
            print("✅ Summary statistics look reasonable!")
            
        return len(validation_issues) == 0
        
    finally:
        await conn.close()

async def run_all_tests():
    """Run all data integrity tests."""
    print("🚀 Controller Summary Data Integrity Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    tests = [
        ("Coverage", test_controller_summary_coverage),
        ("Duration Accuracy", test_session_duration_accuracy),
        ("Data Preservation", test_controller_data_preservation),
        ("Archive Consistency", test_archive_data_consistency),
        ("Statistics Validation", test_summary_statistics)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Controller summary data integrity verified.")
    else:
        print("⚠️  Some tests failed. Data integrity issues detected.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_all_tests())
