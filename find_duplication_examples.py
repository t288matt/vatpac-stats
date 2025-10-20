#!/usr/bin/env python3
"""
Find similar examples of flight_summaries duplication like the BUCK03 case.

This script analyzes the database to find flights with multiple route formats
that would cause the same duplication issue described in the production report.
"""

import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy import text
from app.database import get_database_session

async def find_duplication_examples():
    """Find flights with multiple route formats that cause duplication."""
    
    print("Analyzing flight_summaries duplication patterns...")
    print("=" * 60)
    
    async with get_database_session() as session:
        # 1. Find flights with multiple summary records (like BUCK03)
        print("\n1. FLIGHTS WITH MULTIPLE SUMMARY RECORDS:")
        print("-" * 50)
        
        multiple_summaries_query = text("""
            SELECT 
                callsign,
                cid,
                departure,
                arrival,
                logon_time,
                COUNT(*) as summary_count,
                MIN(created_at) as first_created,
                MAX(created_at) as last_created,
                COUNT(DISTINCT route) as route_variations
            FROM flight_summaries
            GROUP BY callsign, cid, departure, arrival, logon_time
            HAVING COUNT(*) > 1
            ORDER BY summary_count DESC, callsign
            LIMIT 20
        """)
        
        result = await session.execute(multiple_summaries_query)
        rows = result.fetchall()
        
        if rows:
            print(f"Found {len(rows)} flights with multiple summary records:")
            for row in rows:
                print(f"  - {row.callsign} (CID: {row.cid}) - {row.summary_count} summaries")
                print(f"    Route: {row.departure}→{row.arrival}, Logon: {row.logon_time}")
                print(f"    Route variations: {row.route_variations}, Span: {row.first_created} to {row.last_created}")
                print()
        else:
            print("  No flights with multiple summary records found.")
        
        # 2. Find flights with multiple route formats in the flights table
        print("\n2. FLIGHTS WITH MULTIPLE ROUTE FORMATS (ROOT CAUSE):")
        print("-" * 50)
        
        route_variations_query = text("""
            WITH route_analysis AS (
                SELECT 
                    callsign,
                    cid,
                    departure,
                    arrival,
                    logon_time,
                    route,
                    COUNT(*) as record_count,
                    MIN(last_updated) as first_seen,
                    MAX(last_updated) as last_seen
                FROM flights
                WHERE route IS NOT NULL 
                  AND route != ''
                  AND last_updated >= NOW() - INTERVAL '7 days'
                GROUP BY callsign, cid, departure, arrival, logon_time, route
            ),
            flight_groups AS (
                SELECT 
                    callsign,
                    cid,
                    departure,
                    arrival,
                    logon_time,
                    COUNT(DISTINCT route) as route_count,
                    SUM(record_count) as total_records,
                    STRING_AGG(DISTINCT route, ' | ') as all_routes
                FROM route_analysis
                GROUP BY callsign, cid, departure, arrival, logon_time
                HAVING COUNT(DISTINCT route) > 1
            )
            SELECT *
            FROM flight_groups
            ORDER BY route_count DESC, total_records DESC
            LIMIT 15
        """)
        
        result = await session.execute(route_variations_query)
        rows = result.fetchall()
        
        if rows:
            print(f"Found {len(rows)} flights with multiple route formats:")
            for row in rows:
                print(f"  - {row.callsign} (CID: {row.cid}) - {row.route_count} route formats")
                print(f"    Route: {row.departure}→{row.arrival}, Logon: {row.logon_time}")
                print(f"    Total records: {row.total_records}")
                print(f"    Routes: {row.all_routes}")
                print()
        else:
            print("  No flights with multiple route formats found in recent data.")
        
        # 3. Find specific examples like BUCK03 (high duplication factor)
        print("\n3. HIGH DUPLICATION EXAMPLES (210+ records like BUCK03):")
        print("-" * 50)
        
        high_duplication_query = text("""
            SELECT 
                callsign,
                cid,
                departure,
                arrival,
                logon_time,
                COUNT(*) as summary_count,
                COUNT(DISTINCT route) as route_variations,
                STRING_AGG(DISTINCT route, ' | ') as all_routes
            FROM flight_summaries
            GROUP BY callsign, cid, departure, arrival, logon_time
            HAVING COUNT(*) >= 50  -- High duplication threshold
            ORDER BY summary_count DESC
            LIMIT 10
        """)
        
        result = await session.execute(high_duplication_query)
        rows = result.fetchall()
        
        if rows:
            print(f"Found {len(rows)} flights with high duplication (50+ records):")
            for row in rows:
                print(f"  - {row.callsign} (CID: {row.cid}) - {row.summary_count} summaries")
                print(f"    Route: {row.departure}→{row.arrival}, Logon: {row.logon_time}")
                print(f"    Route variations: {row.route_variations}")
                if len(row.all_routes) > 100:
                    print(f"    Routes: {row.all_routes[:100]}...")
                else:
                    print(f"    Routes: {row.all_routes}")
                print()
        else:
            print("  No flights with high duplication (50+ records) found.")
        
        # 4. Analyze the UPDATE WHERE clause issue
        print("\n4. UPDATE WHERE CLAUSE ANALYSIS:")
        print("-" * 50)
        
        update_issue_query = text("""
            -- Find flights where the UPDATE WHERE clause would fail to match
            -- due to multiple records with same (callsign, cid, departure, arrival, logon_time)
            -- but different route formats
            WITH flight_route_groups AS (
                SELECT 
                    f.callsign,
                    f.cid,
                    f.departure,
                    f.arrival,
                    COALESCE(f.logon_time, f.last_updated) as logon_time,
                    f.route,
                    COUNT(*) as record_count
                FROM flights f
                WHERE f.last_updated >= NOW() - INTERVAL '7 days'
                  AND f.route IS NOT NULL
                  AND f.route != ''
                GROUP BY f.callsign, f.cid, f.departure, f.arrival, 
                         COALESCE(f.logon_time, f.last_updated), f.route
            ),
            problematic_flights AS (
                SELECT 
                    callsign,
                    cid,
                    departure,
                    arrival,
                    logon_time,
                    COUNT(DISTINCT route) as route_variations,
                    SUM(record_count) as total_records,
                    STRING_AGG(DISTINCT route, ' | ') as all_routes
                FROM flight_route_groups
                GROUP BY callsign, cid, departure, arrival, logon_time
                HAVING COUNT(DISTINCT route) > 1
            )
            SELECT *
            FROM problematic_flights
            ORDER BY route_variations DESC, total_records DESC
            LIMIT 10
        """)
        
        result = await session.execute(update_issue_query)
        rows = result.fetchall()
        
        if rows:
            print(f"Found {len(rows)} flights where UPDATE WHERE clause would fail:")
            for row in rows:
                print(f"  - {row.callsign} (CID: {row.cid}) - {row.route_variations} route formats")
                print(f"    Route: {row.departure}→{row.arrival}, Logon: {row.logon_time}")
                print(f"    Total records: {row.total_records}")
                print(f"    Routes: {row.all_routes[:150]}...")
                print()
        else:
            print("  No flights with UPDATE WHERE clause issues found.")
        
        # 5. Check for recent BUCK03-like patterns
        print("\n5. RECENT BUCK03-LIKE PATTERNS (October 2024):")
        print("-" * 50)
        
        recent_patterns_query = text("""
            SELECT 
                callsign,
                cid,
                departure,
                arrival,
                logon_time,
                COUNT(*) as summary_count,
                COUNT(DISTINCT route) as route_variations,
                MIN(created_at) as first_created,
                MAX(created_at) as last_created
            FROM flight_summaries
            WHERE created_at >= '2024-10-01'
              AND created_at < '2024-11-01'
            GROUP BY callsign, cid, departure, arrival, logon_time
            HAVING COUNT(*) >= 10  -- Moderate duplication threshold
            ORDER BY summary_count DESC
            LIMIT 10
        """)
        
        result = await session.execute(recent_patterns_query)
        rows = result.fetchall()
        
        if rows:
            print(f"Found {len(rows)} flights with duplication in October 2024:")
            for row in rows:
                print(f"  - {row.callsign} (CID: {row.cid}) - {row.summary_count} summaries")
                print(f"    Route: {row.departure}→{row.arrival}, Logon: {row.logon_time}")
                print(f"    Route variations: {row.route_variations}")
                print(f"    Created: {row.first_created} to {row.last_created}")
                print()
        else:
            print("  No flights with duplication found in October 2024.")
        
        # 6. Summary statistics
        print("\n6. SUMMARY STATISTICS:")
        print("-" * 50)
        
        stats_query = text("""
            SELECT 
                COUNT(*) as total_summaries,
                COUNT(DISTINCT callsign) as unique_flights,
                COUNT(DISTINCT CONCAT(callsign, '|', cid, '|', departure, '|', arrival, '|', logon_time)) as unique_sessions,
                AVG(duplicate_count) as avg_duplicates_per_session
            FROM (
                SELECT 
                    callsign,
                    cid,
                    departure,
                    arrival,
                    logon_time,
                    COUNT(*) as duplicate_count
                FROM flight_summaries
                GROUP BY callsign, cid, departure, arrival, logon_time
            ) session_counts
        """)
        
        result = await session.execute(stats_query)
        row = result.fetchone()
        
        if row:
            print(f"  Total flight summaries: {row.total_summaries:,}")
            print(f"  Unique flights (callsigns): {row.unique_flights:,}")
            print(f"  Unique sessions: {row.unique_sessions:,}")
            print(f"  TOTAL DUPLICATES: {row.total_summaries - row.unique_sessions:,}")
            print(f"  Average duplicates per session: {row.avg_duplicates_per_session:.2f}")
            
            if row.total_summaries > row.unique_sessions:
                duplication_percentage = ((row.total_summaries - row.unique_sessions) / row.total_summaries) * 100
                print(f"  DUPLICATION PERCENTAGE: {duplication_percentage:.2f}%")
        
        print("\n" + "=" * 60)
        print("Analysis complete. Check the results above for duplication patterns.")
        print("The UPDATE WHERE clause issue is in lines 2663-2667 of data_service.py")
        print("WHERE callsign = :callsign AND cid = :cid AND departure = :departure")
        print("AND arrival = :arrival AND logon_time = :session_start")
        print("This should be simplified to:")
        print("WHERE callsign = :callsign AND cid = :cid AND logon_time = :session_start")

async def main():
    """Main entry point."""
    try:
        await find_duplication_examples()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
