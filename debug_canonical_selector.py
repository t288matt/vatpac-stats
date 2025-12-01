#!/usr/bin/env python3
"""
Debug script to understand why canonical session selector might return multiple sessions
for the same flight, causing duplication in flight_summaries.
"""

import asyncio
from sqlalchemy import text
from app.database import get_database_session

async def debug_canonical_selector():
    """Debug the canonical session selector to find the duplication issue."""
    
    print("Debugging canonical session selector for duplication issue...")
    print("=" * 60)
    
    async with get_database_session() as session:
        # Check if there are any flights with multiple route formats that could cause issues
        print("\n1. CHECKING FOR FLIGHTS WITH MULTIPLE ROUTE FORMATS:")
        print("-" * 50)
        
        multi_route_query = text("""
            SELECT 
                callsign,
                cid,
                departure,
                arrival,
                logon_time,
                COUNT(DISTINCT route) as route_count,
                STRING_AGG(DISTINCT route, ' | ') as all_routes
            FROM flights
            WHERE route IS NOT NULL 
              AND route != ''
              AND last_updated >= NOW() - INTERVAL '7 days'
            GROUP BY callsign, cid, departure, arrival, logon_time
            HAVING COUNT(DISTINCT route) > 1
            ORDER BY route_count DESC
            LIMIT 5
        """)
        
        result = await session.execute(multi_route_query)
        rows = result.fetchall()
        
        if rows:
            print(f"Found {len(rows)} flights with multiple route formats:")
            for row in rows:
                print(f"  - {row.callsign} (CID: {row.cid}) - {row.route_count} route formats")
                print(f"    Route: {row.departure}→{row.arrival}, Logon: {row.logon_time}")
                print(f"    Routes: {row.all_routes[:100]}...")
                print()
        else:
            print("  No flights with multiple route formats found.")
        
        # Check the processed_flights CTE logic
        print("\n2. CHECKING PROCESSED_FLIGHTS CTE LOGIC:")
        print("-" * 50)
        
        processed_flights_query = text("""
            SELECT DISTINCT 
                callsign, 
                cid, 
                departure, 
                arrival,
                logon_time
            FROM flight_summaries
            ORDER BY callsign, logon_time
            LIMIT 10
        """)
        
        result = await session.execute(processed_flights_query)
        rows = result.fetchall()
        
        if rows:
            print(f"Sample processed flights from flight_summaries:")
            for row in rows:
                print(f"  - {row.callsign} (CID: {row.cid}) - {row.departure}→{row.arrival} @ {row.logon_time}")
        else:
            print("  No processed flights found in flight_summaries.")
        
        # Check if there are any duplicate sessions being created
        print("\n3. CHECKING FOR POTENTIAL DUPLICATE SESSIONS:")
        print("-" * 50)
        
        # Simulate the canonical session selector logic for a specific flight
        test_flight_query = text("""
            WITH processed_flights AS (
                SELECT DISTINCT 
                    callsign, 
                    cid, 
                    departure, 
                    arrival,
                    logon_time
                FROM flight_summaries
            ),
            flight_completion_times AS (
                SELECT 
                    callsign,
                    cid,
                    departure,
                    arrival,
                    MAX(last_updated) AS latest_record_time
                FROM (
                    SELECT callsign, cid, departure, arrival, last_updated
                    FROM flights
                    UNION ALL
                    SELECT callsign, cid, departure, arrival, last_updated
                    FROM flights_archive
                ) all_records
                GROUP BY callsign, cid, departure, arrival
            ),
            eligible_flights AS (
                SELECT callsign, cid, departure, arrival
                FROM flight_completion_times
                WHERE NOW() >= latest_record_time + (8 * INTERVAL '1 hour')
            ),
            base AS (
                SELECT 
                    f.callsign,
                    f.cid,
                    f.departure,
                    f.arrival,
                    COALESCE(f.logon_time, f.last_updated) AS logon_time,
                    f.last_updated,
                    f.route,
                    COUNT(*) OVER (PARTITION BY f.callsign, f.cid, f.departure, f.arrival) as total_records
                FROM flights f
                INNER JOIN eligible_flights ef
                    ON f.callsign = ef.callsign
                    AND f.cid = ef.cid
                    AND f.departure = ef.departure
                    AND f.arrival = ef.arrival
                WHERE f.callsign IN (SELECT callsign FROM flights WHERE route IS NOT NULL GROUP BY callsign HAVING COUNT(DISTINCT route) > 1 LIMIT 1)
            ),
            sessions AS (
                SELECT 
                    callsign,
                    cid,
                    departure,
                    arrival,
                    MIN(logon_time) AS session_start,
                    MAX(last_updated) AS session_end,
                    COUNT(DISTINCT route) as route_variations,
                    total_records
                FROM base
                GROUP BY callsign, cid, departure, arrival, total_records
            )
            SELECT *
            FROM sessions
            WHERE NOT EXISTS (
                SELECT 1
                FROM processed_flights pf
                WHERE pf.callsign = sessions.callsign
                AND pf.cid = sessions.cid
                AND pf.departure = sessions.departure
                AND pf.arrival = sessions.arrival
                AND pf.logon_time = sessions.session_start
            )
        """)
        
        result = await session.execute(test_flight_query)
        rows = result.fetchall()
        
        if rows:
            print(f"Found {len(rows)} sessions that would be processed:")
            for row in rows:
                print(f"  - {row.callsign} (CID: {row.cid}) - {row.departure}→{row.arrival}")
                print(f"    Session: {row.session_start} to {row.session_end}")
                print(f"    Route variations: {row.route_variations}, Total records: {row.total_records}")
                print()
        else:
            print("  No sessions would be processed (all already processed).")
        
        # Check the actual canonical session selector output
        print("\n4. TESTING ACTUAL CANONICAL SESSION SELECTOR:")
        print("-" * 50)
        
        from app.services.session_selector import select_canonical_sessions
        
        try:
            canonical_sessions = await select_canonical_sessions(
                completion_hours=8,
                gap_minutes=120,
                max_span_hours=8
            )
            
            print(f"Canonical selector returned {len(canonical_sessions)} sessions")
            
            # Group by flight signature to check for duplicates
            flight_signatures = {}
            for session in canonical_sessions:
                key = (session['callsign'], session['cid'], session['departure'], session['arrival'])
                if key not in flight_signatures:
                    flight_signatures[key] = []
                flight_signatures[key].append(session)
            
            duplicates = {k: v for k, v in flight_signatures.items() if len(v) > 1}
            
            if duplicates:
                print(f"FOUND DUPLICATE SESSIONS: {len(duplicates)} flights with multiple sessions")
                for key, sessions in duplicates.items():
                    callsign, cid, departure, arrival = key
                    print(f"  - {callsign} (CID: {cid}) - {departure}→{arrival}: {len(sessions)} sessions")
                    for i, session in enumerate(sessions):
                        print(f"    Session {i+1}: {session['session_start']} to {session['session_end']}")
            else:
                print("  No duplicate sessions found - canonical selector working correctly")
                
        except Exception as e:
            print(f"  Error running canonical selector: {e}")

async def main():
    """Main entry point."""
    try:
        await debug_canonical_selector()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())









