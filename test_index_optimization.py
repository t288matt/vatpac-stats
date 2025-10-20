#!/usr/bin/env python3
"""
Index Optimization Test for ATC Detection Query
Tests different index strategies to improve query performance
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

class IndexOptimizationTest:
    """Test framework for index optimization strategies"""
    
    def __init__(self):
        self.test_queries = []
        self.index_definitions = {}
    
    def get_base_query(self) -> str:
        """Get the current ATC detection query"""
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
    
    async def get_test_controller(self) -> Dict[str, Any]:
        """Get a test controller with substantial data"""
        async with get_database_session() as session:
            query = """
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
            """
            result = await session.execute(text(query))
            row = result.fetchone()
            if row:
                return {
                    'callsign': row.callsign,
                    'transceiver_count': row.transceiver_count,
                    'earliest_time': row.earliest_time,
                    'latest_time': row.latest_time
                }
            return None
    
    async def get_current_indexes(self) -> List[Dict[str, Any]]:
        """Get current indexes on transceivers table"""
        async with get_database_session() as session:
            query = """
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE tablename = 'transceivers'
                ORDER BY indexname
            """
            result = await session.execute(text(query))
            indexes = []
            for row in result.fetchall():
                indexes.append({
                    'name': row.indexname,
                    'definition': row.indexdef
                })
            return indexes
    
    async def create_test_indexes(self):
        """Create various test indexes for optimization"""
        async with get_database_session() as session:
            # Define test indexes
            test_indexes = [
                {
                    'name': 'idx_transceivers_atc_callsign_time_covering',
                    'sql': '''
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_atc_callsign_time_covering
                        ON transceivers(entity_type, callsign, timestamp)
                        INCLUDE (frequency, position_lat, position_lon)
                        WHERE entity_type = 'atc'
                    '''
                },
                {
                    'name': 'idx_transceivers_flight_time_covering',
                    'sql': '''
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_flight_time_covering
                        ON transceivers(entity_type, timestamp)
                        INCLUDE (callsign, frequency, position_lat, position_lon)
                        WHERE entity_type = 'flight'
                    '''
                },
                {
                    'name': 'idx_transceivers_frequency_time_covering',
                    'sql': '''
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_frequency_time_covering
                        ON transceivers(frequency, timestamp)
                        INCLUDE (callsign, entity_type, position_lat, position_lon)
                    '''
                },
                {
                    'name': 'idx_transceivers_atc_time_frequency',
                    'sql': '''
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_atc_time_frequency
                        ON transceivers(entity_type, timestamp, frequency)
                        WHERE entity_type = 'atc'
                    '''
                },
                {
                    'name': 'idx_transceivers_flight_time_frequency',
                    'sql': '''
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_flight_time_frequency
                        ON transceivers(entity_type, timestamp, frequency)
                        WHERE entity_type = 'flight'
                    '''
                }
            ]
            
            logger.info("Creating test indexes...")
            for index in test_indexes:
                try:
                    await session.execute(text(index['sql']))
                    logger.info(f"Created index: {index['name']}")
                except Exception as e:
                    logger.error(f"Failed to create index {index['name']}: {e}")
            
            await session.commit()
    
    async def drop_test_indexes(self):
        """Drop test indexes"""
        async with get_database_session() as session:
            test_indexes = [
                'idx_transceivers_atc_callsign_time_covering',
                'idx_transceivers_flight_time_covering', 
                'idx_transceivers_frequency_time_covering',
                'idx_transceivers_atc_time_frequency',
                'idx_transceivers_flight_time_frequency'
            ]
            
            logger.info("Dropping test indexes...")
            for index_name in test_indexes:
                try:
                    await session.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                    logger.info(f"Dropped index: {index_name}")
                except Exception as e:
                    logger.error(f"Failed to drop index {index_name}: {e}")
            
            await session.commit()
    
    async def run_query_with_explain(self, query: str, params: Dict[str, Any], test_name: str) -> Dict[str, Any]:
        """Run query with EXPLAIN ANALYZE to get performance metrics"""
        start_time = time.time()
        
        try:
            async with get_database_session() as session:
                # Get query plan
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                explain_result = await session.execute(text(explain_query), params)
                plan_data = explain_result.fetchone()[0]
                
                # Run actual query
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                return {
                    'test_name': test_name,
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
                'test_name': test_name,
                'execution_time_seconds': execution_time,
                'row_count': 0,
                'query_plan': None,
                'success': False,
                'error': str(e)
            }
    
    async def analyze_query_plan(self, plan_data: Dict) -> Dict[str, Any]:
        """Analyze query plan to extract performance metrics"""
        if not plan_data:
            return {}
        
        plan = plan_data[0] if isinstance(plan_data, list) else plan_data
        
        def extract_metrics(node):
            metrics = {
                'node_type': node.get('Node Type', 'Unknown'),
                'execution_time': node.get('Actual Total Time', 0),
                'rows': node.get('Actual Rows', 0),
                'cost': node.get('Total Cost', 0),
                'buffers': {
                    'shared_hit': node.get('Shared Hit Blocks', 0),
                    'shared_read': node.get('Shared Read Blocks', 0),
                    'shared_written': node.get('Shared Written Blocks', 0)
                }
            }
            
            # Recursively analyze child nodes
            if 'Plans' in node:
                metrics['children'] = [extract_metrics(child) for child in node['Plans']]
            
            return metrics
        
        return extract_metrics(plan)
    
    async def run_index_test(self, controller: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive index optimization test"""
        logger.info(f"Testing controller: {controller['callsign']}")
        
        # Use a 2-hour window for testing
        session_start = controller['earliest_time']
        session_end = session_start + timedelta(hours=2)
        
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
        
        # Test 1: No additional indexes (baseline)
        logger.info("Running baseline test (existing indexes only)...")
        baseline_result = await self.run_query_with_explain(query, params, "Baseline (Existing Indexes)")
        
        # Test 2: Create and test with new indexes
        logger.info("Creating optimized indexes...")
        await self.create_test_indexes()
        
        # Wait a moment for indexes to be ready
        await asyncio.sleep(2)
        
        logger.info("Running test with optimized indexes...")
        optimized_result = await self.run_query_with_explain(query, params, "With Optimized Indexes")
        
        # Analyze query plans
        baseline_plan = await self.analyze_query_plan(baseline_result.get('query_plan'))
        optimized_plan = await self.analyze_query_plan(optimized_result.get('query_plan'))
        
        # Clean up test indexes
        await self.drop_test_indexes()
        
        return {
            'controller': controller,
            'time_window': {
                'start': session_start,
                'end': session_end,
                'duration_hours': (session_end - session_start).total_seconds() / 3600
            },
            'baseline': baseline_result,
            'optimized': optimized_result,
            'baseline_plan': baseline_plan,
            'optimized_plan': optimized_plan,
            'improvement': {
                'time_saved_seconds': baseline_result['execution_time_seconds'] - optimized_result['execution_time_seconds'],
                'time_saved_percentage': ((baseline_result['execution_time_seconds'] - optimized_result['execution_time_seconds']) / baseline_result['execution_time_seconds'] * 100) if baseline_result['execution_time_seconds'] > 0 else 0,
                'rows_accuracy': baseline_result['row_count'] == optimized_result['row_count']
            }
        }
    
    async def run_performance_test(self):
        """Run the complete index optimization test"""
        logger.info("Starting Index Optimization Test")
        
        # Get current indexes
        current_indexes = await self.get_current_indexes()
        logger.info(f"Current indexes: {len(current_indexes)}")
        for idx in current_indexes:
            logger.info(f"  - {idx['name']}")
        
        # Get test controller
        controller = await self.get_test_controller()
        if not controller:
            logger.error("No suitable test controller found")
            return None
        
        logger.info(f"Using test controller: {controller['callsign']} ({controller['transceiver_count']} transceivers)")
        
        # Run index test
        result = await self.run_index_test(controller)
        
        # Log results
        logger.info(f"\n=== INDEX OPTIMIZATION RESULTS ===")
        logger.info(f"Controller: {controller['callsign']}")
        logger.info(f"Time window: {result['time_window']['duration_hours']:.1f} hours")
        
        baseline = result['baseline']
        optimized = result['optimized']
        improvement = result['improvement']
        
        logger.info(f"Baseline: {baseline['execution_time_seconds']:.2f}s, {baseline['row_count']} rows")
        logger.info(f"Optimized: {optimized['execution_time_seconds']:.2f}s, {optimized['row_count']} rows")
        
        if improvement['time_saved_percentage'] > 0:
            logger.info(f"✅ IMPROVEMENT: {improvement['time_saved_percentage']:.1f}% faster ({improvement['time_saved_seconds']:.2f}s saved)")
        else:
            logger.info(f"❌ NO IMPROVEMENT: {improvement['time_saved_percentage']:.1f}% slower")
        
        if improvement['rows_accuracy']:
            logger.info(f"✅ Data accuracy: PASSED - Same row count")
        else:
            logger.error(f"❌ Data accuracy: FAILED - Row count mismatch")
        
        return result

async def main():
    """Main test execution"""
    test = IndexOptimizationTest()
    result = await test.run_performance_test()
    
    if result:
        print("\n=== DETAILED ANALYSIS ===")
        baseline = result['baseline']
        optimized = result['optimized']
        improvement = result['improvement']
        
        print(f"Controller: {result['controller']['callsign']}")
        print(f"Time window: {result['time_window']['duration_hours']:.1f} hours")
        print(f"Baseline: {baseline['execution_time_seconds']:.2f}s, {baseline['row_count']} rows")
        print(f"Optimized: {optimized['execution_time_seconds']:.2f}s, {optimized['row_count']} rows")
        print(f"Improvement: {improvement['time_saved_percentage']:.1f}% faster")
        print(f"Data accuracy: {'PASSED' if improvement['rows_accuracy'] else 'FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())
