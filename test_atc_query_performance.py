#!/usr/bin/env python3
"""
ATC Detection Query Performance Test
Tests current vs optimized Haversine-first query approach on dev dataset
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

class ATCQueryPerformanceTest:
    """Test framework for ATC detection query performance"""
    
    def __init__(self):
        self.results = []
    
    async def get_test_controllers(self) -> List[Dict[str, Any]]:
        """Get sample controllers for testing"""
        async with get_database_session() as session:
            # Get controllers with recent transceiver activity
            query = """
                SELECT DISTINCT t.callsign, 
                       COUNT(*) as transceiver_count,
                       MIN(t.timestamp) as earliest_time,
                       MAX(t.timestamp) as latest_time
                FROM transceivers t 
                WHERE t.entity_type = 'atc' 
                AND t.timestamp >= NOW() - INTERVAL '7 days'
                AND t.callsign IS NOT NULL
                GROUP BY t.callsign
                HAVING COUNT(*) > 100  -- Ensure sufficient data
                ORDER BY COUNT(*) DESC
                LIMIT 5
            """
            result = await session.execute(text(query))
            controllers = []
            for row in result.fetchall():
                controllers.append({
                    'callsign': row.callsign,
                    'transceiver_count': row.transceiver_count,
                    'earliest_time': row.earliest_time,
                    'latest_time': row.latest_time
                })
            return controllers
    
    async def get_dataset_stats(self) -> Dict[str, Any]:
        """Get dataset statistics for context"""
        async with get_database_session() as session:
            stats = {}
            
            # Transceiver counts
            result = await session.execute(text("""
                SELECT entity_type, COUNT(*) as count
                FROM transceivers 
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY entity_type
            """))
            for row in result.fetchall():
                stats[f"{row.entity_type}_transceivers"] = row.count
            
            # Time range
            result = await session.execute(text("""
                SELECT MIN(timestamp) as min_time, MAX(timestamp) as max_time
                FROM transceivers 
                WHERE timestamp >= NOW() - INTERVAL '7 days'
            """))
            row = result.fetchone()
            stats['time_range'] = {
                'min': row.min_time,
                'max': row.max_time,
                'duration_hours': (row.max_time - row.min_time).total_seconds() / 3600
            }
            
            return stats
    
    def create_current_query(self, controller_callsign: str, session_start: datetime, session_end: datetime, time_window: int, proximity_nm: float) -> str:
        """Create the current (problematic) query"""
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
                ON ABS(ct.frequency_mhz - ft.frequency_mhz) <= 0.005  -- ~5 kHz tolerance
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
                -- Haversine formula for distance in nautical miles
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
    
    def create_optimized_query(self, controller_callsign: str, session_start: datetime, session_end: datetime, time_window: int, proximity_nm: float) -> str:
        """Create the optimized Haversine-first query"""
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
            -- NEW: Pre-filter flights by geographic proximity to ANY controller position
            geographically_filtered_flights AS (
                SELECT ft.*
                FROM flight_transceivers ft
                WHERE EXISTS (
                    SELECT 1 FROM controller_transceivers ct
                    WHERE (3440.065 * ACOS(
                        LEAST(1, GREATEST(-1, 
                            SIN(RADIANS(ct.position_lat)) * SIN(RADIANS(ft.position_lat)) +
                            COS(RADIANS(ct.position_lat)) * COS(RADIANS(ft.position_lon)) * 
                            COS(RADIANS(ct.position_lon - ft.position_lon))
                        ))
                    )) <= :proximity_threshold_nm
                )
            ),
            frequency_matches AS (
                SELECT ct.callsign as controller_callsign, ct.frequency_mhz, ct.timestamp as controller_time,
                       ft.callsign as flight_callsign, ft.timestamp as flight_time,
                       ct.position_lat as controller_lat, ct.position_lon as controller_lon,
                       ft.position_lat as flight_lat, ft.position_lon as flight_lon
                FROM controller_transceivers ct 
                JOIN geographically_filtered_flights ft  -- Much smaller dataset!
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
            ORDER BY flight_time, controller_time
        """
    
    async def run_query_test(self, query: str, params: Dict[str, Any], query_name: str) -> Dict[str, Any]:
        """Run a single query test and measure performance"""
        start_time = time.time()
        
        try:
            async with get_database_session() as session:
                # Get query plan first
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                explain_result = await session.execute(text(explain_query), params)
                plan_data = explain_result.fetchone()[0]
                
                # Run actual query
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                return {
                    'query_name': query_name,
                    'execution_time_seconds': execution_time,
                    'row_count': len(rows),
                    'query_plan': plan_data,
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
                'query_plan': None,
                'success': False,
                'error': str(e)
            }
    
    async def test_controller(self, controller: Dict[str, Any]) -> Dict[str, Any]:
        """Test both queries on a single controller"""
        logger.info(f"Testing controller: {controller['callsign']}")
        
        # Use a 2-hour window for testing (smaller than full session)
        session_start = controller['earliest_time']
        session_end = session_start + timedelta(hours=2)
        
        # Ensure we don't go beyond the latest time
        if session_end > controller['latest_time']:
            session_end = controller['latest_time']
        
        params = {
            'controller_callsign': controller['callsign'],
            'session_start': session_start,
            'session_end': session_end,
            'time_window': 180,  # 3 minutes
            'proximity_threshold_nm': 50.0  # 50 nautical miles
        }
        
        # Test current query
        current_query = self.create_current_query(
            controller['callsign'], session_start, session_end, 180, 50.0
        )
        current_result = await self.run_query_test(current_query, params, "Current Query")
        
        # Test optimized query
        optimized_query = self.create_optimized_query(
            controller['callsign'], session_start, session_end, 180, 50.0
        )
        optimized_result = await self.run_query_test(optimized_query, params, "Optimized Query")
        
        return {
            'controller': controller,
            'time_window': {
                'start': session_start,
                'end': session_end,
                'duration_hours': (session_end - session_start).total_seconds() / 3600
            },
            'current_query': current_result,
            'optimized_query': optimized_result,
            'improvement': {
                'time_saved_seconds': current_result['execution_time_seconds'] - optimized_result['execution_time_seconds'],
                'time_saved_percentage': ((current_result['execution_time_seconds'] - optimized_result['execution_time_seconds']) / current_result['execution_time_seconds'] * 100) if current_result['execution_time_seconds'] > 0 else 0,
                'rows_reduction': current_result['row_count'] - optimized_result['row_count']
            }
        }
    
    async def run_performance_test(self):
        """Run the complete performance test suite"""
        logger.info("Starting ATC Query Performance Test")
        
        # Get dataset stats
        stats = await self.get_dataset_stats()
        logger.info(f"Dataset stats: {stats}")
        
        # Get test controllers
        controllers = await self.get_test_controllers()
        logger.info(f"Found {len(controllers)} test controllers")
        
        results = []
        for controller in controllers:
            try:
                result = await self.test_controller(controller)
                results.append(result)
                
                # Log results for this controller
                logger.info(f"Controller {controller['callsign']}:")
                logger.info(f"  Current query: {result['current_query']['execution_time_seconds']:.2f}s, {result['current_query']['row_count']} rows")
                logger.info(f"  Optimized query: {result['optimized_query']['execution_time_seconds']:.2f}s, {result['optimized_query']['row_count']} rows")
                logger.info(f"  Improvement: {result['improvement']['time_saved_percentage']:.1f}% faster")
                
            except Exception as e:
                logger.error(f"Error testing controller {controller['callsign']}: {e}")
                continue
        
        # Summary
        logger.info("\n=== PERFORMANCE TEST SUMMARY ===")
        total_current_time = sum(r['current_query']['execution_time_seconds'] for r in results)
        total_optimized_time = sum(r['optimized_query']['execution_time_seconds'] for r in results)
        total_improvement = ((total_current_time - total_optimized_time) / total_current_time * 100) if total_current_time > 0 else 0
        
        logger.info(f"Total execution time - Current: {total_current_time:.2f}s, Optimized: {total_optimized_time:.2f}s")
        logger.info(f"Overall improvement: {total_improvement:.1f}% faster")
        
        return {
            'dataset_stats': stats,
            'test_results': results,
            'summary': {
                'total_controllers_tested': len(results),
                'total_current_time': total_current_time,
                'total_optimized_time': total_optimized_time,
                'total_improvement_percentage': total_improvement
            }
        }

async def main():
    """Main test execution"""
    test = ATCQueryPerformanceTest()
    results = await test.run_performance_test()
    
    # Print detailed results
    print("\n=== DETAILED RESULTS ===")
    for result in results['test_results']:
        controller = result['controller']
        current = result['current_query']
        optimized = result['optimized_query']
        improvement = result['improvement']
        
        print(f"\nController: {controller['callsign']}")
        print(f"  Time window: {result['time_window']['duration_hours']:.1f} hours")
        print(f"  Current query: {current['execution_time_seconds']:.2f}s, {current['row_count']} rows, Success: {current['success']}")
        print(f"  Optimized query: {optimized['execution_time_seconds']:.2f}s, {optimized['row_count']} rows, Success: {optimized['success']}")
        print(f"  Improvement: {improvement['time_saved_percentage']:.1f}% faster, {improvement['time_saved_seconds']:.2f}s saved")
        
        if current['error']:
            print(f"  Current query error: {current['error']}")
        if optimized['error']:
            print(f"  Optimized query error: {optimized['error']}")

if __name__ == "__main__":
    asyncio.run(main())
