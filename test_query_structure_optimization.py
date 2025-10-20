#!/usr/bin/env python3
"""
Query Structure Optimization Test
Tests proximity-first approach to reduce dataset before expensive calculations
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy import text
from app.database import get_database_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryStructureOptimizationTest:
    """Test different query structures for optimization"""
    
    def __init__(self):
        pass
    
    async def get_test_controller(self) -> Dict[str, Any]:
        """Get a test controller with substantial data"""
        async with get_database_session() as session:
            result = await session.execute(text("""
                SELECT callsign, 
                       COUNT(*) as transceiver_count,
                       MIN(timestamp) as earliest_time,
                       MAX(timestamp) as latest_time
                FROM transceivers 
                WHERE entity_type = 'atc' 
                AND timestamp >= NOW() - INTERVAL '7 days'
                AND callsign IS NOT NULL
                GROUP BY callsign
                HAVING COUNT(*) > 1000
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """))
            row = result.fetchone()
            if row:
                return {
                    'callsign': row.callsign,
                    'transceiver_count': row.transceiver_count,
                    'earliest_time': row.earliest_time,
                    'latest_time': row.latest_time
                }
            return None
    
    def get_current_query(self) -> str:
        """Current query structure - frequency first, then distance"""
        return """
            WITH controller_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'atc' 
                AND t.callsign = :controller_callsign
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            flight_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'flight' 
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            frequency_matches AS (
                SELECT ct.callsign as controller_callsign, ct.frequency_mhz, ct.timestamp as controller_time,
                       ft.callsign as flight_callsign, ft.timestamp as flight_time,
                       ct.position_lat as controller_lat, ct.position_lon as controller_lon,
                       ft.position_lat as flight_lat, ft.position_lon as flight_lon
                FROM controller_transceivers ct 
                JOIN flight_transceivers ft
                ON ABS(ct.frequency_mhz - ft.frequency_mhz) <= 0.005
                AND ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) <= :time_window
            )
            SELECT 
                controller_callsign,
                flight_callsign,
                frequency_mhz,
                controller_time,
                flight_time,
                controller_lat,
                controller_lon,
                flight_lat,
                flight_lon,
                ABS(EXTRACT(EPOCH FROM (controller_time - flight_time))) as time_diff_seconds
            FROM frequency_matches
            WHERE (
                (3440.065 * ACOS(
                    LEAST(1, GREATEST(-1, 
                        SIN(RADIANS(controller_lat)) * SIN(RADIANS(flight_lat)) +
                        COS(RADIANS(controller_lat)) * COS(RADIANS(flight_lat)) * 
                        COS(RADIANS(controller_lon - flight_lon))
                    ))
                )) <= :proximity_threshold_nm
            )
            ORDER BY flight_time, controller_time
        """
    
    def get_proximity_first_query(self) -> str:
        """Proximity-first query - filter by distance before frequency matching"""
        return """
            WITH controller_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'atc' 
                AND t.callsign = :controller_callsign
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            flight_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'flight' 
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            proximity_matches AS (
                SELECT ct.callsign as controller_callsign, ct.frequency_mhz, ct.timestamp as controller_time,
                       ft.callsign as flight_callsign, ft.timestamp as flight_time,
                       ct.position_lat as controller_lat, ct.position_lon as controller_lon,
                       ft.position_lat as flight_lat, ft.position_lon as flight_lon
                FROM controller_transceivers ct 
                CROSS JOIN flight_transceivers ft
                WHERE ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) <= :time_window
                AND (
                    -- Quick distance check first (bounding box approximation)
                    ABS(ct.position_lat - ft.position_lat) <= (:proximity_threshold_nm / 60.0) AND
                    ABS(ct.position_lon - ft.position_lon) <= (:proximity_threshold_nm / 60.0) AND
                    -- Then precise Haversine calculation
                    (3440.065 * ACOS(
                        LEAST(1, GREATEST(-1, 
                            SIN(RADIANS(ct.position_lat)) * SIN(RADIANS(ft.position_lat)) +
                            COS(RADIANS(ct.position_lat)) * COS(RADIANS(ft.position_lat)) * 
                            COS(RADIANS(ct.position_lon - ft.position_lon))
                        ))
                    )) <= :proximity_threshold_nm
                )
            )
            SELECT 
                controller_callsign,
                flight_callsign,
                frequency_mhz,
                controller_time,
                flight_time,
                controller_lat,
                controller_lon,
                flight_lat,
                flight_lon,
                ABS(EXTRACT(EPOCH FROM (controller_time - flight_time))) as time_diff_seconds
            FROM proximity_matches
            WHERE ABS(frequency_mhz - (
                SELECT frequency_mhz 
                FROM proximity_matches pm2 
                WHERE pm2.controller_callsign = proximity_matches.controller_callsign 
                AND pm2.flight_callsign = proximity_matches.flight_callsign
                AND pm2.controller_time = proximity_matches.controller_time
                AND pm2.flight_time = proximity_matches.flight_time
            )) <= 0.005
            ORDER BY flight_time, controller_time
        """
    
    def get_optimized_proximity_first_query(self) -> str:
        """Optimized proximity-first query with better structure"""
        return """
            WITH controller_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'atc' 
                AND t.callsign = :controller_callsign
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            flight_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'flight' 
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            proximity_matches AS (
                SELECT ct.callsign as controller_callsign, ct.frequency_mhz as controller_frequency, ct.timestamp as controller_time,
                       ft.callsign as flight_callsign, ft.frequency_mhz as flight_frequency, ft.timestamp as flight_time,
                       ct.position_lat as controller_lat, ct.position_lon as controller_lon,
                       ft.position_lat as flight_lat, ft.position_lon as flight_lon
                FROM controller_transceivers ct 
                CROSS JOIN flight_transceivers ft
                WHERE ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) <= :time_window
                AND ABS(ct.frequency_mhz - ft.frequency_mhz) <= 0.005
                AND (
                    -- Quick distance check first (bounding box approximation)
                    ABS(ct.position_lat - ft.position_lat) <= (:proximity_threshold_nm / 60.0) AND
                    ABS(ct.position_lon - ft.position_lon) <= (:proximity_threshold_nm / 60.0) AND
                    -- Then precise Haversine calculation
                    (3440.065 * ACOS(
                        LEAST(1, GREATEST(-1, 
                            SIN(RADIANS(ct.position_lat)) * SIN(RADIANS(ft.position_lat)) +
                            COS(RADIANS(ct.position_lat)) * COS(RADIANS(ft.position_lat)) * 
                            COS(RADIANS(ct.position_lon - ft.position_lon))
                        ))
                    )) <= :proximity_threshold_nm
                )
            )
            SELECT 
                controller_callsign,
                flight_callsign,
                controller_frequency as frequency_mhz,
                controller_time,
                flight_time,
                controller_lat,
                controller_lon,
                flight_lat,
                flight_lon,
                ABS(EXTRACT(EPOCH FROM (controller_time - flight_time))) as time_diff_seconds
            FROM proximity_matches
            ORDER BY flight_time, controller_time
        """
    
    def get_bounding_box_query(self) -> str:
        """Query using bounding box approximation for initial filtering"""
        return """
            WITH controller_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'atc' 
                AND t.callsign = :controller_callsign
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            flight_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'flight' 
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            bounding_box_matches AS (
                SELECT ct.callsign as controller_callsign, ct.frequency_mhz, ct.timestamp as controller_time,
                       ft.callsign as flight_callsign, ft.timestamp as flight_time,
                       ct.position_lat as controller_lat, ct.position_lon as controller_lon,
                       ft.position_lat as flight_lat, ft.position_lon as flight_lon
                FROM controller_transceivers ct 
                CROSS JOIN flight_transceivers ft
                WHERE ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) <= :time_window
                AND ABS(ct.frequency_mhz - ft.frequency_mhz) <= 0.005
                AND (
                    -- Bounding box check (much faster than Haversine)
                    ABS(ct.position_lat - ft.position_lat) <= (:proximity_threshold_nm / 60.0) AND
                    ABS(ct.position_lon - ft.position_lon) <= (:proximity_threshold_nm / 60.0)
                )
            )
            SELECT 
                controller_callsign,
                flight_callsign,
                frequency_mhz,
                controller_time,
                flight_time,
                controller_lat,
                controller_lon,
                flight_lat,
                flight_lon,
                ABS(EXTRACT(EPOCH FROM (controller_time - flight_time))) as time_diff_seconds
            FROM bounding_box_matches
            WHERE (
                -- Only do expensive Haversine calculation on pre-filtered results
                (3440.065 * ACOS(
                    LEAST(1, GREATEST(-1, 
                        SIN(RADIANS(controller_lat)) * SIN(RADIANS(flight_lat)) +
                        COS(RADIANS(controller_lat)) * COS(RADIANS(flight_lat)) * 
                        COS(RADIANS(controller_lon - flight_lon))
                    ))
                )) <= :proximity_threshold_nm
            )
            ORDER BY flight_time, controller_time
        """
    
    async def run_query_test(self, query: str, params: Dict[str, Any], query_name: str) -> Dict[str, Any]:
        """Run a query and measure performance"""
        start_time = time.time()
        
        try:
            async with get_database_session() as session:
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                return {
                    'query_name': query_name,
                    'execution_time_seconds': execution_time,
                    'row_count': len(rows),
                    'success': True,
                    'error': None
                }
                
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            return {
                'query_name': query_name,
                'execution_time_seconds': execution_time,
                'row_count': 0,
                'success': False,
                'error': str(e)
            }
    
    async def run_structure_optimization_test(self, controller: Dict[str, Any], time_window_hours: float = 2.0) -> Dict[str, Any]:
        """Test different query structures"""
        session_start = controller['earliest_time']
        session_end = session_start + timedelta(hours=time_window_hours)
        
        if session_end > controller['latest_time']:
            session_end = controller['latest_time']
        
        params = {
            'controller_callsign': controller['callsign'],
            'session_start': session_start,
            'session_end': session_end,
            'time_window': 180,  # 3 minutes
            'proximity_threshold_nm': 50.0  # 50 nautical miles
        }
        
        logger.info(f"Testing query structures for {controller['callsign']} - {time_window_hours}h window")
        
        # Test different query structures
        queries = [
            (self.get_current_query(), "Current (Frequency First)"),
            (self.get_bounding_box_query(), "Bounding Box Optimization"),
            (self.get_optimized_proximity_first_query(), "Optimized Proximity First")
        ]
        
        results = []
        
        for query, name in queries:
            logger.info(f"Testing {name}...")
            result = await self.run_query_test(query, params, name)
            results.append(result)
            
            if result['success']:
                logger.info(f"  {name}: {result['execution_time_seconds']:.2f}s, {result['row_count']} rows")
            else:
                logger.error(f"  {name}: FAILED - {result['error']}")
        
        return {
            'controller': controller,
            'time_window_hours': time_window_hours,
            'results': results
        }
    
    async def run_comprehensive_test(self):
        """Run comprehensive query structure optimization test"""
        logger.info("Starting Query Structure Optimization Test")
        
        # Get test controller
        controller = await self.get_test_controller()
        if not controller:
            logger.error("No suitable test controller found")
            return None
        
        logger.info(f"Using test controller: {controller['callsign']} ({controller['transceiver_count']} transceivers)")
        
        # Test with 2-hour window
        result = await self.run_structure_optimization_test(controller, 2.0)
        
        # Log results
        logger.info(f"\n=== QUERY STRUCTURE OPTIMIZATION RESULTS ===")
        logger.info(f"Controller: {controller['callsign']}")
        logger.info(f"Time window: {result['time_window_hours']} hours")
        
        baseline_result = None
        best_result = None
        
        for result_item in result['results']:
            if result_item['success']:
                logger.info(f"{result_item['query_name']}: {result_item['execution_time_seconds']:.2f}s ({result_item['row_count']} rows)")
                
                if result_item['query_name'] == "Current (Frequency First)":
                    baseline_result = result_item
                
                if not best_result or result_item['execution_time_seconds'] < best_result['execution_time_seconds']:
                    best_result = result_item
            else:
                logger.error(f"{result_item['query_name']}: FAILED")
        
        if baseline_result and best_result:
            improvement = ((baseline_result['execution_time_seconds'] - best_result['execution_time_seconds']) / baseline_result['execution_time_seconds']) * 100
            logger.info(f"\nBest improvement: {improvement:.1f}% faster with {best_result['query_name']}")
            
            if abs(baseline_result['row_count'] - best_result['row_count']) <= 1:
                logger.info(f"✅ Data accuracy: PASSED - Same row count")
            else:
                logger.error(f"❌ Data accuracy: FAILED - Row count mismatch")
        
        return result

async def main():
    """Main test execution"""
    test = QueryStructureOptimizationTest()
    result = await test.run_comprehensive_test()
    
    if result:
        print("\n=== SUMMARY ===")
        print(f"Controller: {result['controller']['callsign']}")
        print(f"Time window: {result['time_window_hours']} hours")
        
        successful_results = [r for r in result['results'] if r['success']]
        if successful_results:
            baseline = next((r for r in successful_results if r['query_name'] == "Current (Frequency First)"), None)
            best = min(successful_results, key=lambda x: x['execution_time_seconds'])
            
            if baseline and best:
                improvement = ((baseline['execution_time_seconds'] - best['execution_time_seconds']) / baseline['execution_time_seconds']) * 100
                print(f"Best improvement: {improvement:.1f}% faster")
                print(f"Best query: {best['query_name']}")

if __name__ == "__main__":
    asyncio.run(main())
