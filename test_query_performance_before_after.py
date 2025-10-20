#!/usr/bin/env python3
"""
ATC Detection Query Performance Test - Before vs After
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
    
    def validate_data_accuracy(self, current_result: Dict[str, Any], optimized_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that both queries return identical data - PRIMARY VALIDATION"""
        
        # Check if both queries succeeded
        if not current_result['success'] or not optimized_result['success']:
            return {
                'accurate': False,
                'reason': f"Query execution failed - Current: {current_result['success']}, Optimized: {optimized_result['success']}",
                'details': {
                    'current_error': current_result.get('error'),
                    'optimized_error': optimized_result.get('error')
                }
            }
        
        current_data = current_result['row_data']
        optimized_data = optimized_result['row_data']
        
        # 1. Row count must match
        if len(current_data) != len(optimized_data):
            return {
                'accurate': False,
                'reason': f"Row count mismatch - Current: {len(current_data)}, Optimized: {len(optimized_data)}",
                'details': {
                    'current_count': len(current_data),
                    'optimized_count': len(optimized_data)
                }
            }
        
        # 2. Sort both datasets for comparison (same ORDER BY)
        current_sorted = sorted(current_data, key=lambda x: (x['flight_time'], x['controller_time']))
        optimized_sorted = sorted(optimized_data, key=lambda x: (x['flight_time'], x['controller_time']))
        
        # 3. Compare each row
        differences = []
        for i, (current_row, optimized_row) in enumerate(zip(current_sorted, optimized_sorted)):
            row_diff = self.compare_rows(current_row, optimized_row, i)
            if row_diff:
                differences.append(row_diff)
        
        if differences:
            return {
                'accurate': False,
                'reason': f"Data differences found in {len(differences)} rows",
                'details': {
                    'differences': differences[:10],  # Show first 10 differences
                    'total_differences': len(differences)
                }
            }
        
        return {
            'accurate': True,
            'reason': "All data matches exactly",
            'details': {
                'rows_compared': len(current_data),
                'exact_match': True
            }
        }
    
    def compare_rows(self, current_row: Dict, optimized_row: Dict, row_index: int) -> Dict[str, Any]:
        """Compare two rows and return differences if any"""
        differences = {}
        
        # Compare each field with tolerance for floating point
        fields_to_compare = [
            'controller_callsign', 'flight_callsign', 'frequency_mhz', 
            'controller_time', 'flight_time', 'controller_lat', 'controller_lon',
            'flight_lat', 'flight_lon', 'time_diff_seconds'
        ]
        
        for field in fields_to_compare:
            current_val = current_row.get(field)
            optimized_val = optimized_row.get(field)
            
            if field in ['frequency_mhz', 'controller_lat', 'controller_lon', 'flight_lat', 'flight_lon', 'time_diff_seconds']:
                # Floating point comparison with tolerance
                if current_val is None and optimized_val is None:
                    continue
                if current_val is None or optimized_val is None:
                    differences[field] = {'current': current_val, 'optimized': optimized_val}
                elif abs(float(current_val) - float(optimized_val)) > 0.0001:  # Small tolerance for floating point
                    differences[field] = {'current': current_val, 'optimized': optimized_val}
            else:
                # Exact comparison for strings and timestamps
                if current_val != optimized_val:
                    differences[field] = {'current': current_val, 'optimized': optimized_val}
        
        if differences:
            return {
                'row_index': row_index,
                'differences': differences
            }
        
        return None
    
    async def get_test_controllers(self) -> List[Dict[str, Any]]:
        """Get sample controllers for testing - including largest datasets"""
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
                HAVING COUNT(*) > 500  -- Focus on larger datasets
                ORDER BY COUNT(*) DESC
                LIMIT 3
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
    
    def create_current_query(self) -> str:
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
    
    def create_optimized_query(self) -> str:
        """Create optimized query with bounding box pre-filtering"""
        return """
            WITH controller_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'atc' 
                AND t.callsign = :controller_callsign
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            -- Get controller bounding box for fast pre-filtering
            controller_bounds AS (
                SELECT 
                    MIN(position_lat) - (:proximity_threshold_nm / 60.0) as min_lat,
                    MAX(position_lat) + (:proximity_threshold_nm / 60.0) as max_lat,
                    MIN(position_lon) - (:proximity_threshold_nm / 60.0) as min_lon,
                    MAX(position_lon) + (:proximity_threshold_nm / 60.0) as max_lon
                FROM controller_transceivers
                WHERE position_lat IS NOT NULL AND position_lon IS NOT NULL
            ),
            -- Pre-filter flights by bounding box (fast)
            flight_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                CROSS JOIN controller_bounds cb
                WHERE t.entity_type = 'flight' 
                AND t.timestamp BETWEEN :session_start AND :session_end
                AND t.position_lat BETWEEN cb.min_lat AND cb.max_lat
                AND t.position_lon BETWEEN cb.min_lon AND cb.max_lon
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
                -- Haversine formula for distance in nautical miles (only on pre-filtered results)
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
    
    def create_chunked_query(self) -> str:
        """Create optimized query with time-based chunking"""
        return """
            WITH controller_transceivers AS (
                SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                FROM transceivers t 
                WHERE t.entity_type = 'atc' 
                AND t.callsign = :controller_callsign
                AND t.timestamp BETWEEN :session_start AND :session_end
            ),
            -- Process controller transceivers with limited flight window
            chunked_results AS (
                SELECT 
                    ct.callsign as controller_callsign, 
                    ct.frequency_mhz, 
                    ct.timestamp as controller_time,
                    ft.callsign as flight_callsign, 
                    ft.timestamp as flight_time,
                    ct.position_lat as controller_lat, 
                    ct.position_lon as controller_lon,
                    ft.position_lat as flight_lat, 
                    ft.position_lon as flight_lon,
                    ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) as time_diff_seconds
                FROM controller_transceivers ct 
                JOIN transceivers ft ON (
                    ft.entity_type = 'flight' 
                    AND ft.timestamp BETWEEN ct.timestamp - '1 hour'::interval 
                    AND ct.timestamp + '1 hour'::interval
                    AND ABS(ct.frequency_mhz - (ft.frequency/1000000.0)) <= 0.005
                    AND ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) <= :time_window
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
                time_diff_seconds
            FROM chunked_results
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
    
    async def run_query_test(self, query: str, params: Dict[str, Any], query_name: str) -> Dict[str, Any]:
        """Run a single query test and measure performance - NO TIMEOUT"""
        start_time = time.time()
        
        try:
            async with get_database_session() as session:
                logger.info(f"Running {query_name}...")
                
                # Run actual query first to get data - NO TIMEOUT
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                
                logger.info(f"{query_name} returned {len(rows)} rows")
                
                # Convert rows to comparable format for accuracy testing
                row_data = []
                for row in rows:
                    row_data.append({
                        'controller_callsign': row.controller_callsign,
                        'flight_callsign': row.flight_callsign,
                        'frequency_mhz': float(row.frequency_mhz) if row.frequency_mhz else None,
                        'controller_time': row.controller_time,
                        'flight_time': row.flight_time,
                        'controller_lat': float(row.controller_lat) if row.controller_lat else None,
                        'controller_lon': float(row.controller_lon) if row.controller_lon else None,
                        'flight_lat': float(row.flight_lat) if row.flight_lat else None,
                        'flight_lon': float(row.flight_lon) if row.flight_lon else None,
                        'time_diff_seconds': float(row.time_diff_seconds) if row.time_diff_seconds else None
                    })
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                logger.info(f"{query_name} completed in {execution_time:.2f} seconds")
                
                return {
                    'query_name': query_name,
                    'execution_time_seconds': execution_time,
                    'row_count': len(rows),
                    'row_data': row_data,
                    'success': True,
                    'error': None
                }
                
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            logger.error(f"{query_name} failed after {execution_time:.2f} seconds: {e}")
            
            return {
                'query_name': query_name,
                'execution_time_seconds': execution_time,
                'row_count': 0,
                'row_data': [],
                'success': False,
                'error': str(e)
            }
    
    async def test_controller(self, controller: Dict[str, Any]) -> Dict[str, Any]:
        """Test both queries on a single controller"""
        logger.info(f"Testing controller: {controller['callsign']}")
        
        # Use larger time windows to test production-like scenarios
        session_start = controller['earliest_time']
        
        # For controllers with long sessions, use 4-hour windows
        # For controllers with short sessions, use full session
        session_duration = controller['latest_time'] - controller['earliest_time']
        if session_duration.total_seconds() > 4 * 3600:  # More than 4 hours
            session_end = session_start + timedelta(hours=4)
            logger.info(f"Using 4-hour window for large dataset")
        else:
            session_end = controller['latest_time']
            logger.info(f"Using full session ({session_duration.total_seconds()/3600:.1f} hours)")
        
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
        current_query = self.create_current_query()
        current_result = await self.run_query_test(current_query, params, "Current Query")
        
        # Test optimized query
        optimized_query = self.create_optimized_query()
        optimized_result = await self.run_query_test(optimized_query, params, "Bounding Box Optimization")
        
        # Test chunked optimization
        chunked_query = self.create_chunked_query()
        chunked_result = await self.run_query_test(chunked_query, params, "Chunked Processing")
        
        # Data accuracy validation - PRIMARY CONCERN
        accuracy_result_bb = self.validate_data_accuracy(current_result, optimized_result)
        accuracy_result_chunked = self.validate_data_accuracy(current_result, chunked_result)
        
        return {
            'controller': controller,
            'time_window': {
                'start': session_start,
                'end': session_end,
                'duration_hours': (session_end - session_start).total_seconds() / 3600
            },
            'current_query': current_result,
            'optimized_query': optimized_result,
            'chunked_query': chunked_result,
            'accuracy_validation_bb': accuracy_result_bb,
            'accuracy_validation_chunked': accuracy_result_chunked,
            'improvements': {
                'bounding_box': {
                    'time_saved_seconds': current_result['execution_time_seconds'] - optimized_result['execution_time_seconds'],
                    'time_saved_percentage': ((current_result['execution_time_seconds'] - optimized_result['execution_time_seconds']) / current_result['execution_time_seconds'] * 100) if current_result['execution_time_seconds'] > 0 else 0,
                    'rows_reduction': current_result['row_count'] - optimized_result['row_count']
                },
                'chunked': {
                    'time_saved_seconds': current_result['execution_time_seconds'] - chunked_result['execution_time_seconds'],
                    'time_saved_percentage': ((current_result['execution_time_seconds'] - chunked_result['execution_time_seconds']) / current_result['execution_time_seconds'] * 100) if current_result['execution_time_seconds'] > 0 else 0,
                    'rows_reduction': current_result['row_count'] - chunked_result['row_count']
                }
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
                
                # Log results for this controller - DATA ACCURACY FIRST
                logger.info(f"Controller {controller['callsign']}:")
                
                # PRIMARY: Data accuracy validation
                accuracy_bb = result['accuracy_validation_bb']
                accuracy_chunked = result['accuracy_validation_chunked']
                
                if accuracy_bb['accurate'] and accuracy_chunked['accurate']:
                    logger.info(f"  ✅ DATA ACCURACY: PASSED - Both optimizations match current query")
                    # SECONDARY: Performance metrics
                    logger.info(f"  Current query: {result['current_query']['execution_time_seconds']:.2f}s, {result['current_query']['row_count']} rows")
                    logger.info(f"  Bounding Box: {result['optimized_query']['execution_time_seconds']:.2f}s, {result['optimized_query']['row_count']} rows ({result['improvements']['bounding_box']['time_saved_percentage']:.1f}% faster)")
                    logger.info(f"  Chunked: {result['chunked_query']['execution_time_seconds']:.2f}s, {result['chunked_query']['row_count']} rows ({result['improvements']['chunked']['time_saved_percentage']:.1f}% faster)")
                else:
                    logger.error(f"  ❌ DATA ACCURACY: FAILED")
                    if not accuracy_bb['accurate']:
                        logger.error(f"    Bounding Box: {accuracy_bb['reason']}")
                    if not accuracy_chunked['accurate']:
                        logger.error(f"    Chunked: {accuracy_chunked['reason']}")
                
            except Exception as e:
                logger.error(f"Error testing controller {controller['callsign']}: {e}")
                continue
        
        # Summary - DATA ACCURACY FIRST
        logger.info("\n=== TEST SUMMARY ===")
        
        # PRIMARY: Data accuracy summary
        accurate_results = [r for r in results if r['accuracy_validation_bb']['accurate'] and r['accuracy_validation_chunked']['accurate']]
        failed_results = [r for r in results if not (r['accuracy_validation_bb']['accurate'] and r['accuracy_validation_chunked']['accurate'])]
        
        logger.info(f"DATA ACCURACY: {len(accurate_results)}/{len(results)} tests PASSED")
        if failed_results:
            logger.error(f"FAILED controllers: {[r['controller']['callsign'] for r in failed_results]}")
        
        # SECONDARY: Performance summary (only for accurate results)
        total_current_time = 0
        total_bb_time = 0
        total_chunked_time = 0
        if accurate_results:
            total_current_time = sum(r['current_query']['execution_time_seconds'] for r in accurate_results)
            total_bb_time = sum(r['optimized_query']['execution_time_seconds'] for r in accurate_results)
            total_chunked_time = sum(r['chunked_query']['execution_time_seconds'] for r in accurate_results)
            
            bb_improvement = ((total_current_time - total_bb_time) / total_current_time * 100) if total_current_time > 0 else 0
            chunked_improvement = ((total_current_time - total_chunked_time) / total_current_time * 100) if total_current_time > 0 else 0
            
            logger.info(f"PERFORMANCE (accurate results only):")
            logger.info(f"  Total execution time - Current: {total_current_time:.2f}s")
            logger.info(f"  Bounding Box: {total_bb_time:.2f}s ({bb_improvement:.1f}% faster)")
            logger.info(f"  Chunked: {total_chunked_time:.2f}s ({chunked_improvement:.1f}% faster)")
        else:
            logger.error("No accurate results to analyze performance")
        
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
        chunked = result['chunked_query']
        
        accuracy_bb = result['accuracy_validation_bb']
        accuracy_chunked = result['accuracy_validation_chunked']
        
        print(f"\nController: {controller['callsign']}")
        print(f"  Time window: {result['time_window']['duration_hours']:.1f} hours")
        
        # PRIMARY: Data accuracy
        if accuracy_bb['accurate'] and accuracy_chunked['accurate']:
            print(f"  ✅ DATA ACCURACY: PASSED - Both optimizations match current query")
            # SECONDARY: Performance
            print(f"  Current query: {current['execution_time_seconds']:.2f}s, {current['row_count']} rows")
            print(f"  Bounding Box: {optimized['execution_time_seconds']:.2f}s, {optimized['row_count']} rows ({result['improvements']['bounding_box']['time_saved_percentage']:.1f}% faster)")
            print(f"  Chunked: {chunked['execution_time_seconds']:.2f}s, {chunked['row_count']} rows ({result['improvements']['chunked']['time_saved_percentage']:.1f}% faster)")
        else:
            print(f"  ❌ DATA ACCURACY: FAILED")
            if not accuracy_bb['accurate']:
                print(f"    Bounding Box: {accuracy_bb['reason']}")
            if not accuracy_chunked['accurate']:
                print(f"    Chunked: {accuracy_chunked['reason']}")
        
        if current['error']:
            print(f"  Current query error: {current['error']}")
        if optimized['error']:
            print(f"  Bounding Box error: {optimized['error']}")
        if chunked['error']:
            print(f"  Chunked error: {chunked['error']}")

if __name__ == "__main__":
    asyncio.run(main())
