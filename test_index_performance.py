#!/usr/bin/env python3
"""
Index Performance Test
Tests actual query performance with different index scenarios
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

class IndexPerformanceTest:
    """Test actual query performance with different index scenarios"""
    
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
    
    def get_base_query(self) -> str:
        """Get the ATC detection query"""
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
    
    async def run_query_performance_test(self, controller: Dict[str, Any], time_window_hours: float = 2.0) -> Dict[str, Any]:
        """Run the query and measure performance"""
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
        
        query = self.get_base_query()
        
        logger.info(f"Running query for {controller['callsign']} - {time_window_hours}h window")
        logger.info(f"Time range: {session_start} to {session_end}")
        
        start_time = time.time()
        
        try:
            async with get_database_session() as session:
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                return {
                    'controller': controller['callsign'],
                    'time_window_hours': time_window_hours,
                    'execution_time_seconds': execution_time,
                    'row_count': len(rows),
                    'success': True,
                    'error': None
                }
                
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            return {
                'controller': controller['callsign'],
                'time_window_hours': time_window_hours,
                'execution_time_seconds': execution_time,
                'row_count': 0,
                'success': False,
                'error': str(e)
            }
    
    async def test_different_time_windows(self, controller: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Test query performance with different time windows"""
        time_windows = [0.5, 1.0, 2.0, 4.0, 6.0, 8.0]  # hours
        results = []
        
        logger.info(f"Testing different time windows for controller: {controller['callsign']}")
        
        for window in time_windows:
            logger.info(f"Testing {window}h window...")
            result = await self.run_query_performance_test(controller, window)
            results.append(result)
            
            if result['success']:
                logger.info(f"  {window}h: {result['execution_time_seconds']:.2f}s, {result['row_count']} rows")
            else:
                logger.error(f"  {window}h: FAILED - {result['error']}")
        
        return results
    
    async def analyze_index_usage(self) -> Dict[str, Any]:
        """Analyze current index usage and suggest optimizations"""
        async with get_database_session() as session:
            # Get index usage statistics
            index_stats = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan / NULLIF(idx_tup_read, 0) as efficiency_ratio
                FROM pg_stat_user_indexes 
                WHERE tablename = 'transceivers'
                ORDER BY idx_scan DESC
            """))
            
            indexes = []
            for row in index_stats.fetchall():
                indexes.append({
                    'name': row.indexname,
                    'scans': row.idx_scan or 0,
                    'tuples_read': row.idx_tup_read or 0,
                    'tuples_fetched': row.idx_tup_fetch or 0,
                    'efficiency': row.efficiency_ratio or 0
                })
            
            # Get table statistics
            table_stats = await session.execute(text("""
                SELECT 
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples
                FROM pg_stat_user_tables 
                WHERE relname = 'transceivers'
            """))
            
            table_row = table_stats.fetchone()
            table_stats_dict = {
                'inserts': table_row.inserts if table_row else 0,
                'updates': table_row.updates if table_row else 0,
                'deletes': table_row.deletes if table_row else 0,
                'live_tuples': table_row.live_tuples if table_row else 0,
                'dead_tuples': table_row.dead_tuples if table_row else 0
            }
            
            return {
                'indexes': indexes,
                'table_stats': table_stats_dict
            }
    
    async def suggest_optimizations(self, performance_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Suggest optimizations based on performance results"""
        suggestions = []
        
        # Analyze performance scaling
        if len(performance_results) >= 2:
            # Find the point where performance degrades significantly
            for i in range(1, len(performance_results)):
                prev_result = performance_results[i-1]
                curr_result = performance_results[i]
                
                if prev_result['success'] and curr_result['success']:
                    time_ratio = curr_result['execution_time_seconds'] / prev_result['execution_time_seconds']
                    window_ratio = curr_result['time_window_hours'] / prev_result['time_window_hours']
                    
                    # If time increases more than proportionally to window size
                    if time_ratio > window_ratio * 1.5:
                        suggestions.append({
                            'type': 'time_window_optimization',
                            'description': f"Performance degrades significantly at {curr_result['time_window_hours']}h window",
                            'recommendation': f"Consider breaking large sessions into smaller chunks (max {prev_result['time_window_hours']}h)",
                            'impact': 'High'
                        })
                        break
        
        # General optimization suggestions
        suggestions.extend([
            {
                'type': 'index_optimization',
                'description': 'Current indexes may not be optimal for the query pattern',
                'recommendation': 'Create covering indexes for entity_type + callsign + timestamp combinations',
                'impact': 'Medium'
            },
            {
                'type': 'query_optimization',
                'description': 'Haversine calculation is expensive',
                'recommendation': 'Consider pre-calculating distance or using spatial indexes',
                'impact': 'Medium'
            },
            {
                'type': 'caching',
                'description': 'Query results could be cached for repeated controller sessions',
                'recommendation': 'Implement Redis caching for ATC detection results',
                'impact': 'High'
            }
        ])
        
        return suggestions
    
    async def run_comprehensive_test(self):
        """Run comprehensive performance test"""
        logger.info("Starting Comprehensive Index Performance Test")
        
        # Get test controller
        controller = await self.get_test_controller()
        if not controller:
            logger.error("No suitable test controller found")
            return None
        
        logger.info(f"Using test controller: {controller['callsign']} ({controller['transceiver_count']} transceivers)")
        
        # Test different time windows
        performance_results = await self.test_different_time_windows(controller)
        
        # Analyze index usage
        index_analysis = await self.analyze_index_usage()
        
        # Generate optimization suggestions
        suggestions = await self.suggest_optimizations(performance_results)
        
        # Log results
        logger.info(f"\n=== PERFORMANCE ANALYSIS ===")
        logger.info(f"Controller: {controller['callsign']}")
        
        for result in performance_results:
            if result['success']:
                logger.info(f"{result['time_window_hours']}h: {result['execution_time_seconds']:.2f}s ({result['row_count']} rows)")
            else:
                logger.error(f"{result['time_window_hours']}h: FAILED")
        
        logger.info(f"\n=== INDEX USAGE ANALYSIS ===")
        for idx in index_analysis['indexes']:
            logger.info(f"{idx['name']}: {idx['scans']} scans, {idx['efficiency']:.3f} efficiency")
        
        logger.info(f"\n=== OPTIMIZATION SUGGESTIONS ===")
        for suggestion in suggestions:
            logger.info(f"{suggestion['type']}: {suggestion['description']}")
            logger.info(f"  Recommendation: {suggestion['recommendation']}")
            logger.info(f"  Impact: {suggestion['impact']}")
        
        return {
            'controller': controller,
            'performance_results': performance_results,
            'index_analysis': index_analysis,
            'suggestions': suggestions
        }

async def main():
    """Main test execution"""
    test = IndexPerformanceTest()
    result = await test.run_comprehensive_test()
    
    if result:
        print("\n=== SUMMARY ===")
        print(f"Controller: {result['controller']['callsign']}")
        print(f"Performance tests: {len(result['performance_results'])}")
        print(f"Optimization suggestions: {len(result['suggestions'])}")
        
        # Show performance scaling
        successful_results = [r for r in result['performance_results'] if r['success']]
        if len(successful_results) >= 2:
            first_result = successful_results[0]
            last_result = successful_results[-1]
            time_ratio = last_result['execution_time_seconds'] / first_result['execution_time_seconds']
            window_ratio = last_result['time_window_hours'] / first_result['time_window_hours']
            print(f"Performance scaling: {time_ratio:.2f}x time for {window_ratio:.2f}x data")

if __name__ == "__main__":
    asyncio.run(main())
