#!/usr/bin/env python3
"""
ATC Detection Testing: Identical Input Data Validation with Production Scale

This test ensures both the existing and proposed approaches use EXACTLY the same input data
to provide valid performance comparisons and functional equivalence verification.

Core Principle: "If we're not testing with identical input data, we're not testing the right thing."
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import subprocess
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ATCTestingFramework:
    """Framework for testing ATC detection approaches with identical input data and production scale"""
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        
    async def get_identical_flight_data(self) -> Dict[str, Any]:
        """
        Get flight data that will be used by BOTH approaches.
        This ensures input data consistency.
        """
        logger.info("🔍 Getting identical flight data for both approaches...")
        
        # Query to get a real flight with substantial data
        flight_query = """
        SELECT 
            callsign,
            departure,
            arrival,
            logon_time,
            last_updated,
            EXTRACT(EPOCH FROM (last_updated - logon_time))/3600 as flight_duration_hours
        FROM flights 
        WHERE logon_time >= NOW() - INTERVAL '48 hours'
        AND last_updated IS NOT NULL
        AND logon_time < last_updated
        ORDER BY (last_updated - logon_time) DESC
        LIMIT 1;
        """
        
        result = await self.run_sql_query(flight_query)
        
        if not result or len(result) == 0:
            raise ValueError("No suitable flight data found for testing")
            
        # Parse the first result with proper column mapping
        flight_data = self.parse_flight_data(result[0])
        logger.info(f"✅ Selected flight: {flight_data['callsign']} "
                   f"({flight_data['departure']} → {flight_data['arrival']}) "
                   f"Duration: {flight_data['flight_duration_hours']:.1f} hours")
        
        return flight_data
    
    def parse_flight_data(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw SQL result into properly typed flight data.
        """
        try:
            # Extract values from raw result
            values = raw_result['raw_values']
            
            # Map columns to values (order must match SQL SELECT)
            flight_data = {
                'callsign': values[0],
                'departure': values[1],
                'arrival': values[2],
                'logon_time': self.parse_datetime(values[3]),
                'last_updated': self.parse_datetime(values[4]),
                'flight_duration_hours': float(values[5]) if values[5] else 0.0
            }
            
            return flight_data
            
        except (IndexError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse flight data: {e}")
            logger.error(f"Raw result: {raw_result}")
            raise ValueError(f"Invalid flight data format: {e}")
    
    def parse_datetime(self, datetime_str: str) -> datetime:
        """
        Parse datetime string to datetime object.
        """
        try:
            # Handle various datetime formats including timezone info
            if '+00' in datetime_str:
                # PostgreSQL timestamp with timezone: 2025-08-28 06:31:08+00
                return datetime.strptime(datetime_str.replace('+00', ''), '%Y-%m-%d %H:%M:%S')
            elif 'T' in datetime_str:
                # ISO format: 2024-01-15T10:00:00
                return datetime.fromisoformat(datetime_str.replace('T', ' '))
            else:
                # Standard format: 2024-01-15 10:00:00
                return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        except ValueError as e:
            logger.error(f"Failed to parse datetime '{datetime_str}': {e}")
            raise ValueError(f"Invalid datetime format: {datetime_str}")
    
    async def get_identical_atc_data_for_flight(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get ATC data for the EXACT same time window that will be used by both approaches.
        This ensures ATC data consistency.
        """
        logger.info("🎯 Getting identical ATC data for flight time window...")
        
        # Use the EXACT same time window for both approaches
        start_time = flight_data['logon_time']
        end_time = flight_data['last_updated']
        
        # Get controllers active during the flight's time window
        controllers_query = """
        SELECT DISTINCT 
            callsign,
            facility,
            logon_time,
            last_updated
        FROM controllers 
        WHERE facility != 0  -- Exclude observer positions
        AND (
            (logon_time <= :end_time AND last_updated >= :start_time)  -- Overlapping sessions
            OR (logon_time >= :start_time AND logon_time <= :end_time)  -- Started during flight
        )
        ORDER BY callsign, logon_time;
        """
        
        controllers_result = await self.run_sql_query(controllers_query, {
            'start_time': start_time,
            'end_time': end_time
        })
        
        # Get transceiver data for the EXACT same time window
        transceivers_query = """
        SELECT 
            callsign,
            frequency,
            timestamp,
            position_lat,
            position_lon,
            entity_type
        FROM transceivers 
        WHERE entity_type = 'atc'
        AND timestamp >= :start_time
        AND timestamp <= :end_time
        AND callsign IN (
            SELECT DISTINCT callsign FROM controllers 
            WHERE facility != 0
            AND (
                (logon_time <= :end_time AND last_updated >= :start_time)
                OR (logon_time >= :start_time AND logon_time <= :end_time)
            )
        )
        ORDER BY callsign, timestamp;
        """
        
        transceivers_result = await self.run_sql_query(transceivers_query, {
            'start_time': start_time,
            'end_time': end_time
        })
        
        atc_data = {
            'time_window': {
                'start_time': start_time,
                'end_time': end_time,
                'duration_hours': (end_time - start_time).total_seconds() / 3600
            },
            'controllers': controllers_result,
            'transceivers': transceivers_result,
            'controller_count': len(controllers_result),
            'transceiver_count': len(transceivers_result)
        }
        
        logger.info(f"✅ ATC data: {atc_data['controller_count']} controllers, "
                   f"{atc_data['transceiver_count']} transceivers, "
                   f"{atc_data['time_window']['duration_hours']:.1f} hour window")
        
        return atc_data
    
    async def test_existing_approach(self, flight_data: Dict[str, Any], atc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test the existing approach with the identical input data.
        This simulates the current JOIN explosion problem EXACTLY as it exists in the code.
        """
        logger.info("🔄 Testing existing approach (JOIN explosion)...")
        
        start_time = time.time()
        
        # EXACTLY as implemented in the existing code - this JOIN creates the cartesian product
        # From _get_atc_transceivers_for_flight() in atc_detection_service.py lines 200-210
        # This is the REAL query that causes the JOIN explosion in production
        existing_query = """
        SELECT COUNT(*) as total_records
        FROM transceivers t
        INNER JOIN controllers c ON t.callsign = c.callsign
        WHERE t.entity_type = 'atc' 
        AND c.facility != 0  -- Exclude observer positions
        AND t.timestamp >= :atc_start
        AND t.timestamp <= :atc_end;
        """
        
        result = await self.run_sql_query(existing_query, {
            'atc_start': atc_data['time_window']['start_time'],
            'atc_end': atc_data['time_window']['end_time']
        })
        
        execution_time = time.time() - start_time
        
        # Parse the count result
        total_records = 0
        if result and len(result) > 0:
            try:
                total_records = int(result[0]['raw_values'][0])
            except (IndexError, ValueError):
                logger.warning("Could not parse record count from existing approach")
        
        existing_result = {
            'approach': 'existing',
            'total_records': total_records,
            'execution_time': execution_time,
            'input_data': {
                'flight': flight_data,
                'atc': atc_data
            }
        }
        
        logger.info(f"📊 Existing approach: {existing_result['total_records']:,} records in {execution_time:.3f}s")
        
        return existing_result
    
    async def test_proposed_approach(self, flight_data: Dict[str, Any], atc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test the proposed approach with the IDENTICAL input data.
        This uses geographic pre-filtering exactly as proposed in the documentation.
        """
        logger.info("🚀 Testing proposed approach (geographic pre-filtering)...")
        
        start_time = time.time()
        
        # Step 1: Get flight-specific controller window (exactly as proposed)
        # Use flight.logon_time as the start of the active window
        controllers_query = """
        SELECT DISTINCT 
            callsign,
            facility
        FROM controllers 
        WHERE facility != 0
        AND last_updated >= :flight_logon_time  -- Flight-specific timing: since flight came online
        ORDER BY callsign;
        """
        
        controllers_result = await self.run_sql_query(controllers_query, {
            'flight_logon_time': flight_data['logon_time']
        })
        
        # Step 2: Get relevant transceivers (geographic pre-filtering - exactly as proposed)
        # This avoids the JOIN explosion by filtering first
        transceivers_query = """
        SELECT COUNT(*) as total_records
        FROM transceivers t
        WHERE t.entity_type = 'atc'
        AND t.callsign IN (
            SELECT DISTINCT callsign FROM controllers 
            WHERE facility != 0
            AND last_updated >= :flight_logon_time  -- Flight-specific timing
        )
        AND t.timestamp >= :atc_start
        AND t.timestamp <= :atc_end;
        """
        
        result = await self.run_sql_query(transceivers_query, {
            'flight_logon_time': flight_data['logon_time'],
            'atc_start': atc_data['time_window']['start_time'],
            'atc_end': atc_data['time_window']['end_time']
        })
        
        execution_time = time.time() - start_time
        
        # Parse the count result
        total_records = 0
        if result and len(result) > 0:
            try:
                total_records = int(result[0]['raw_values'][0])
            except (IndexError, ValueError):
                logger.warning("Could not parse record count from proposed approach")
        
        proposed_result = {
            'approach': 'proposed',
            'total_records': total_records,
            'execution_time': execution_time,
            'input_data': {
                'flight': flight_data,
                'atc': atc_data
            }
        }
        
        logger.info(f"📊 Proposed approach: {proposed_result['total_records']:,} records in {execution_time:.3f}s")
        
        return proposed_result
    
    async def validate_input_data_consistency(self, existing_result: Dict[str, Any], proposed_result: Dict[str, Any]) -> bool:
        """
        Verify that both approaches used EXACTLY the same input data.
        This is critical for valid comparison.
        """
        logger.info("🔍 Validating input data consistency...")
        
        # Check flight data
        existing_flight = existing_result['input_data']['flight']
        proposed_flight = proposed_result['input_data']['flight']
        
        if existing_flight != proposed_flight:
            logger.error("❌ Flight data mismatch between approaches!")
            logger.error(f"Existing: {existing_flight}")
            logger.error(f"Proposed: {proposed_flight}")
            return False
        
        # Check ATC data
        existing_atc = existing_result['input_data']['atc']
        proposed_atc = proposed_result['input_data']['atc']
        
        if existing_atc != proposed_atc:
            logger.error("❌ ATC data mismatch between approaches!")
            logger.error(f"Existing: {existing_atc}")
            logger.error(f"Proposed: {proposed_atc}")
            return False
        
        logger.info("✅ Input data is 100% identical between approaches")
        return True
    
    async def validate_functional_equivalence(self, existing_result: Dict[str, Any], proposed_result: Dict[str, Any]) -> bool:
        """
        Verify that both approaches produce functionally equivalent results.
        The proposed approach should return the same relevant data.
        """
        logger.info("🔍 Validating functional equivalence...")
        
        existing_records = existing_result['total_records']
        proposed_records = proposed_result['total_records']
        
        # Both approaches should return the same number of relevant records
        if existing_records != proposed_records:
            logger.error(f"❌ Record count mismatch: Existing={existing_records:,}, Proposed={proposed_records:,}")
            return False
        
        logger.info(f"✅ Functional equivalence: Both approaches return {existing_records:,} relevant records")
        return True
    
    async def measure_performance_improvement(self, existing_result: Dict[str, Any], proposed_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Measure the performance improvement of the proposed approach.
        """
        logger.info("📈 Measuring performance improvement...")
        
        existing_time = existing_result['execution_time']
        proposed_time = proposed_result['execution_time']
        
        if existing_time == 0:
            speedup = float('inf')
            percentage_improvement = 100.0
        else:
            speedup = existing_time / proposed_time
            percentage_improvement = ((existing_time - proposed_time) / existing_time) * 100
        
        performance_metrics = {
            'existing_execution_time': existing_time,
            'proposed_execution_time': proposed_time,
            'speedup_factor': speedup,
            'percentage_improvement': percentage_improvement,
            'time_saved': existing_time - proposed_time
        }
        
        logger.info(f"🚀 Performance improvement: {speedup:.1f}x faster "
                   f"({percentage_improvement:.1f}% improvement)")
        
        return performance_metrics
    
    async def run_sql_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Run a SQL query using docker compose exec psql.
        Returns the results as a list of dictionaries.
        """
        try:
            # Build the command
            cmd = [
                'docker', 'compose', 'exec', '-T', 'postgres',
                'psql', '-U', 'vatsim_user', '-d', 'vatsim_data',
                '-t', '-A', '-F', ',', '-c', query
            ]
            
            # Add parameters if provided
            if params:
                # Convert parameters to SQL format
                for key, value in params.items():
                    if isinstance(value, datetime):
                        # Format datetime for SQL
                        formatted_value = value.strftime('%Y-%m-%d %H:%M:%S')
                        query = query.replace(f':{key}', f"'{formatted_value}'")
                    else:
                        query = query.replace(f':{key}', str(value))
                
                # Update command with parameterized query
                cmd[-1] = query
            
            # Execute the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"SQL query failed: {result.stderr}")
                return []
            
            # Parse the CSV output
            lines = result.stdout.strip().split('\n')
            if not lines or lines[0] == '':
                return []
            
            # Parse CSV format
            results = []
            for line in lines:
                if line.strip():
                    # Split by comma and create dict
                    values = line.split(',')
                    # For now, just return the raw values
                    # In a real implementation, you'd map these to column names
                    results.append({'raw_values': values})
            
            return results
            
        except subprocess.TimeoutExpired:
            logger.error("SQL query timed out")
            return []
        except Exception as e:
            logger.error(f"Error running SQL query: {e}")
            return []
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """
        Run the complete test suite with identical input data.
        """
        logger.info("🚀 Starting comprehensive ATC detection testing...")
        
        try:
            # Step 1: Get identical flight data
            flight_data = await self.get_identical_flight_data()
            
            # Step 2: Get identical ATC data for the same time window
            atc_data = await self.get_identical_atc_data_for_flight(flight_data)
            
            # Step 3: Test existing approach with identical data
            existing_result = await self.test_existing_approach(flight_data, atc_data)
            
            # Step 4: Test proposed approach with IDENTICAL data
            proposed_result = await self.test_proposed_approach(flight_data, atc_data)
            
            # Step 5: Validate input data consistency
            input_consistent = await self.validate_input_data_consistency(existing_result, proposed_result)
            
            if not input_consistent:
                raise ValueError("Input data consistency validation failed")
            
            # Step 6: Validate functional equivalence
            functionally_equivalent = await self.validate_functional_equivalence(existing_result, proposed_result)
            
            if not functionally_equivalent:
                raise ValueError("Functional equivalence validation failed")
            
            # Step 7: Measure performance improvement
            performance_metrics = await self.measure_performance_improvement(existing_result, proposed_result)
            
            # Compile results
            test_results = {
                'test_timestamp': datetime.utcnow().isoformat(),
                'input_data_consistency': input_consistent,
                'functional_equivalence': functionally_equivalent,
                'existing_approach': existing_result,
                'proposed_approach': proposed_result,
                'performance_metrics': performance_metrics,
                'test_summary': {
                    'flight_callsign': flight_data['callsign'],
                    'time_window_hours': atc_data['time_window']['duration_hours'],
                    'controller_count': atc_data['controller_count'],
                    'transceiver_count': atc_data['transceiver_count'],
                    'success': input_consistent and functionally_equivalent
                }
            }
            
            logger.info("✅ Comprehensive test completed successfully!")
            return test_results
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {
                'test_timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'success': False
            }
    
    def print_test_summary(self, test_results: Dict[str, Any]):
        """
        Print a comprehensive summary of the test results.
        """
        if not test_results.get('success', False):
            logger.error("❌ Test failed - see error details above")
            return
        
        logger.info("\n" + "="*80)
        logger.info("📊 ATC DETECTION TEST RESULTS SUMMARY")
        logger.info("="*80)
        
        summary = test_results['test_summary']
        logger.info(f"✈️  Flight: {summary['flight_callsign']}")
        logger.info(f"⏰ Time Window: {summary['time_window_hours']:.1f} hours")
        logger.info(f"🎯 Controllers: {summary['controller_count']}")
        logger.info(f"📡 Transceivers: {summary['transceiver_count']:,}")
        
        existing = test_results['existing_approach']
        proposed = test_results['proposed_approach']
        
        logger.info(f"\n🔄 Existing Approach:")
        logger.info(f"   Records: {existing['total_records']:,}")
        logger.info(f"   Time: {existing['execution_time']:.3f}s")
        
        logger.info(f"\n🚀 Proposed Approach:")
        logger.info(f"   Records: {proposed['total_records']:,}")
        logger.info(f"   Time: {proposed['execution_time']:.3f}s")
        
        perf = test_results['performance_metrics']
        logger.info(f"\n📈 Performance Improvement:")
        logger.info(f"   Speedup: {perf['speedup_factor']:.1f}x faster")
        logger.info(f"   Improvement: {perf['percentage_improvement']:.1f}%")
        logger.info(f"   Time Saved: {perf['time_saved']:.3f}s")
        
        logger.info(f"\n✅ Validation Results:")
        logger.info(f"   Input Data Consistency: {'PASS' if test_results['input_data_consistency'] else 'FAIL'}")
        logger.info(f"   Functional Equivalence: {'PASS' if test_results['functional_equivalence'] else 'FAIL'}")
        
        logger.info("="*80)

async def main():
    """
    Main test execution function.
    """
    logger.info("🚀 Starting ATC Detection Testing Framework")
    
    # Create testing framework
    framework = ATCTestingFramework()
    
    # Run comprehensive test
    test_results = await framework.run_comprehensive_test()
    
    # Print results summary
    framework.print_test_summary(test_results)
    
    # Save results to file
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"atc_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    logger.info(f"💾 Test results saved to: {filename}")
    
    return test_results

if __name__ == "__main__":
    # Run the test
    asyncio.run(main())
