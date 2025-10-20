#!/usr/bin/env python3
"""
Simple Index Optimization Test
Tests existing indexes and suggests new ones without creating them
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

class SimpleIndexTest:
    """Simple index analysis and optimization suggestions"""
    
    def __init__(self):
        pass
    
    async def get_current_indexes(self) -> List[Dict[str, Any]]:
        """Get current indexes on transceivers table with usage stats"""
        async with get_database_session() as session:
            query = """
                SELECT 
                    i.indexname,
                    i.indexdef,
                    s.idx_tup_read,
                    s.idx_tup_fetch,
                    s.idx_scan,
                    s.idx_tup_read / NULLIF(s.idx_scan, 0) as avg_tuples_per_scan
                FROM pg_indexes i
                LEFT JOIN pg_stat_user_indexes s ON i.indexname = s.indexrelname
                WHERE i.tablename = 'transceivers'
                ORDER BY s.idx_scan DESC NULLS LAST
            """
            result = await session.execute(text(query))
            indexes = []
            for row in result.fetchall():
                indexes.append({
                    'name': row.indexname,
                    'definition': row.indexdef,
                    'scans': row.idx_scan or 0,
                    'tuples_read': row.idx_tup_read or 0,
                    'tuples_fetched': row.idx_tup_fetch or 0,
                    'avg_tuples_per_scan': row.avg_tuples_per_scan or 0
                })
            return indexes
    
    async def analyze_query_plan(self, controller_callsign: str, session_start: datetime, session_end: datetime) -> Dict[str, Any]:
        """Analyze the query execution plan for the ATC detection query"""
        query = """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
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
                AND ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) <= 180
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
                )) <= 50.0
            )
            ORDER BY flight_time, controller_time
        """
        
        params = {
            'controller_callsign': controller_callsign,
            'session_start': session_start,
            'session_end': session_end
        }
        
        async with get_database_session() as session:
            result = await session.execute(text(query), params)
            plan_data = result.fetchone()[0]
            return plan_data
    
    def analyze_plan_for_optimization(self, plan_data: Dict) -> Dict[str, Any]:
        """Analyze query plan to identify optimization opportunities"""
        if not plan_data:
            return {'error': 'No plan data available'}
        
        plan = plan_data[0] if isinstance(plan_data, list) else plan_data
        
        def find_slow_nodes(node, path=""):
            slow_nodes = []
            
            # Check if this node is slow (taking more than 10% of total time)
            node_time = node.get('Actual Total Time', 0)
            if node_time > 1000:  # More than 1 second
                slow_nodes.append({
                    'path': path,
                    'node_type': node.get('Node Type', 'Unknown'),
                    'execution_time': node_time,
                    'rows': node.get('Actual Rows', 0),
                    'cost': node.get('Total Cost', 0),
                    'relation_name': node.get('Relation Name'),
                    'index_name': node.get('Index Name'),
                    'filter': node.get('Filter'),
                    'join_type': node.get('Join Type'),
                    'buffers': {
                        'shared_hit': node.get('Shared Hit Blocks', 0),
                        'shared_read': node.get('Shared Read Blocks', 0),
                        'shared_written': node.get('Shared Written Blocks', 0)
                    }
                })
            
            # Recursively check child nodes
            if 'Plans' in node:
                for i, child in enumerate(node['Plans']):
                    child_path = f"{path}.{i}" if path else str(i)
                    slow_nodes.extend(find_slow_nodes(child, child_path))
            
            return slow_nodes
        
        slow_nodes = find_slow_nodes(plan)
        
        # Analyze for specific optimization opportunities
        optimizations = []
        
        for node in slow_nodes:
            if node['node_type'] == 'Seq Scan':
                optimizations.append({
                    'type': 'missing_index',
                    'table': node['relation_name'],
                    'suggestion': f"Consider adding an index on {node['relation_name']} for the scan conditions",
                    'impact': 'high',
                    'execution_time': node['execution_time']
                })
            
            elif node['node_type'] == 'Nested Loop':
                optimizations.append({
                    'type': 'join_optimization',
                    'suggestion': f"Consider optimizing the nested loop join - {node['execution_time']:.0f}ms",
                    'impact': 'medium',
                    'execution_time': node['execution_time']
                })
            
            elif node['node_type'] == 'Hash Join':
                optimizations.append({
                    'type': 'hash_join_optimization', 
                    'suggestion': f"Hash join taking {node['execution_time']:.0f}ms - consider index optimization",
                    'impact': 'medium',
                    'execution_time': node['execution_time']
                })
        
        return {
            'total_execution_time': plan.get('Actual Total Time', 0),
            'slow_nodes': slow_nodes,
            'optimizations': optimizations,
            'total_cost': plan.get('Total Cost', 0)
        }
    
    def suggest_indexes(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Suggest specific indexes based on analysis"""
        suggestions = []
        
        # Look for sequential scans that could benefit from indexes
        for node in analysis.get('slow_nodes', []):
            if node['node_type'] == 'Seq Scan' and node['relation_name'] == 'transceivers':
                suggestions.append({
                    'name': 'idx_transceivers_atc_callsign_time_covering',
                    'sql': '''
                        CREATE INDEX CONCURRENTLY idx_transceivers_atc_callsign_time_covering
                        ON transceivers(entity_type, callsign, timestamp)
                        INCLUDE (frequency, position_lat, position_lon)
                        WHERE entity_type = 'atc';
                    ''',
                    'purpose': 'Optimize ATC transceiver lookups with covering index',
                    'expected_impact': 'High - eliminates table lookups for ATC data'
                })
                
                suggestions.append({
                    'name': 'idx_transceivers_flight_time_covering',
                    'sql': '''
                        CREATE INDEX CONCURRENTLY idx_transceivers_flight_time_covering
                        ON transceivers(entity_type, timestamp)
                        INCLUDE (callsign, frequency, position_lat, position_lon)
                        WHERE entity_type = 'flight';
                    ''',
                    'purpose': 'Optimize flight transceiver lookups with covering index',
                    'expected_impact': 'High - eliminates table lookups for flight data'
                })
        
        # Add frequency-based optimization
        suggestions.append({
            'name': 'idx_transceivers_frequency_time_optimized',
            'sql': '''
                CREATE INDEX CONCURRENTLY idx_transceivers_frequency_time_optimized
                ON transceivers(frequency, timestamp)
                INCLUDE (callsign, entity_type, position_lat, position_lon);
            ''',
            'purpose': 'Optimize frequency-based joins and time filtering',
            'expected_impact': 'Medium - improves frequency matching performance'
        })
        
        return suggestions
    
    async def run_analysis(self):
        """Run comprehensive index analysis"""
        logger.info("Starting Index Analysis")
        
        # Get current indexes
        current_indexes = await self.get_current_indexes()
        logger.info(f"\nCurrent indexes on transceivers table:")
        for idx in current_indexes:
            logger.info(f"  {idx['name']}: {idx['scans']} scans, {idx['avg_tuples_per_scan']:.1f} avg tuples/scan")
        
        # Get a test controller
        async with get_database_session() as session:
            result = await session.execute(text("""
                SELECT callsign, MIN(timestamp) as earliest_time, MAX(timestamp) as latest_time
                FROM transceivers 
                WHERE entity_type = 'atc' 
                AND timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY callsign
                HAVING COUNT(*) > 1000
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """))
            row = result.fetchone()
            
            if not row:
                logger.error("No suitable test controller found")
                return
            
            controller_callsign = row.callsign
            session_start = row.earliest_time
            session_end = session_start + timedelta(hours=2)
            
            logger.info(f"\nAnalyzing query plan for controller: {controller_callsign}")
            logger.info(f"Time window: {session_start} to {session_end}")
        
        # Analyze query plan
        start_time = time.time()
        plan_data = await self.analyze_query_plan(controller_callsign, session_start, session_end)
        analysis_time = time.time() - start_time
        
        logger.info(f"Query plan analysis completed in {analysis_time:.2f} seconds")
        
        # Analyze for optimizations
        analysis = self.analyze_plan_for_optimization(plan_data)
        
        logger.info(f"\n=== QUERY PLAN ANALYSIS ===")
        logger.info(f"Total execution time: {analysis['total_execution_time']:.2f}ms")
        logger.info(f"Total cost: {analysis['total_cost']:.0f}")
        
        if analysis['slow_nodes']:
            logger.info(f"\nSlow nodes identified:")
            for node in analysis['slow_nodes']:
                logger.info(f"  {node['node_type']}: {node['execution_time']:.2f}ms ({node['rows']} rows)")
                if node['index_name']:
                    logger.info(f"    Using index: {node['index_name']}")
                if node['relation_name']:
                    logger.info(f"    Table: {node['relation_name']}")
        
        # Suggest optimizations
        suggestions = self.suggest_indexes(analysis)
        
        logger.info(f"\n=== INDEX OPTIMIZATION SUGGESTIONS ===")
        for i, suggestion in enumerate(suggestions, 1):
            logger.info(f"\n{i}. {suggestion['name']}")
            logger.info(f"   Purpose: {suggestion['purpose']}")
            logger.info(f"   Expected Impact: {suggestion['expected_impact']}")
            logger.info(f"   SQL: {suggestion['sql'].strip()}")
        
        return {
            'current_indexes': current_indexes,
            'query_analysis': analysis,
            'optimization_suggestions': suggestions
        }

async def main():
    """Main analysis execution"""
    test = SimpleIndexTest()
    result = await test.run_analysis()
    
    if result:
        print("\n=== SUMMARY ===")
        print(f"Current indexes: {len(result['current_indexes'])}")
        print(f"Query execution time: {result['query_analysis']['total_execution_time']:.2f}ms")
        print(f"Optimization suggestions: {len(result['optimization_suggestions'])}")
        
        # Show the most impactful suggestions
        if result['optimization_suggestions']:
            print("\nTop optimization suggestions:")
            for suggestion in result['optimization_suggestions'][:3]:
                print(f"  - {suggestion['name']}: {suggestion['expected_impact']}")

if __name__ == "__main__":
    asyncio.run(main())
