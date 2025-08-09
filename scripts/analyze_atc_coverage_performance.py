#!/usr/bin/env python3
"""
ATC Coverage Query Performance Analysis

This script analyzes the performance of the ATC Service Coverage queries
used in the Grafana dashboard and provides recommendations for index optimization.

Usage:
    python scripts/analyze_atc_coverage_performance.py
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
import json

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from config import get_database_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_database_connection():
    """Create database connection"""
    try:
        database_url = get_database_url()
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

def analyze_table_stats(conn):
    """Analyze table statistics for key tables"""
    logger.info("Analyzing table statistics...")
    
    query = """
    SELECT 
        schemaname,
        tablename,
        n_tup_ins as inserts,
        n_tup_upd as updates,
        n_tup_del as deletes,
        n_live_tup as live_rows,
        n_dead_tup as dead_rows,
        last_vacuum,
        last_autovacuum,
        last_analyze,
        last_autoanalyze
    FROM pg_stat_user_tables 
    WHERE tablename IN ('transceivers', 'controllers', 'flights')
    ORDER BY live_rows DESC;
    """
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            results = cur.fetchall()
            
            print("\n" + "="*80)
            print("TABLE STATISTICS ANALYSIS")
            print("="*80)
            
            for row in results:
                print(f"\nTable: {row['tablename']}")
                print(f"  Live Rows: {row['live_rows']:,}")
                print(f"  Dead Rows: {row['dead_rows']:,}")
                print(f"  Inserts: {row['inserts']:,}")
                print(f"  Updates: {row['updates']:,}")
                print(f"  Last Analyze: {row['last_analyze']}")
                
            return results
    except Exception as e:
        logger.error(f"Failed to analyze table stats: {e}")
        return []

def analyze_existing_indexes(conn):
    """Analyze existing indexes and their usage"""
    logger.info("Analyzing existing indexes...")
    
    query = """
    SELECT 
        t.tablename,
        i.indexname,
        i.indexdef,
        s.idx_scan,
        s.idx_tup_read,
        s.idx_tup_fetch,
        pg_size_pretty(pg_relation_size(i.indexname::regclass)) as index_size
    FROM pg_indexes i
    JOIN pg_stat_user_indexes s ON i.indexname = s.indexname
    JOIN pg_tables t ON i.tablename = t.tablename
    WHERE t.schemaname = 'public' 
        AND i.tablename IN ('transceivers', 'controllers', 'flights')
    ORDER BY s.idx_scan DESC, t.tablename;
    """
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            results = cur.fetchall()
            
            print("\n" + "="*80)
            print("EXISTING INDEX ANALYSIS")
            print("="*80)
            
            for row in results:
                print(f"\nTable: {row['tablename']}")
                print(f"  Index: {row['indexname']}")
                print(f"  Scans: {row['idx_scan']:,}")
                print(f"  Tuples Read: {row['idx_tup_read']:,}")
                print(f"  Size: {row['index_size']}")
                
            return results
    except Exception as e:
        logger.error(f"Failed to analyze indexes: {e}")
        return []

def test_query_performance(conn):
    """Test the performance of key ATC coverage queries"""
    logger.info("Testing query performance...")
    
    # Simplified version of the main ATC coverage query for performance testing
    test_query = """
    EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
    WITH flight_transceivers AS (
        SELECT t.callsign, t.frequency, t.timestamp, t.position_lat, t.position_lon 
        FROM transceivers t 
        WHERE t.entity_type = 'flight'
        LIMIT 1000  -- Limit for testing
    ),
    atc_transceivers AS (
        SELECT t.callsign, t.frequency, t.timestamp, t.position_lat, t.position_lon 
        FROM transceivers t 
        WHERE t.entity_type = 'atc' 
        AND t.callsign IN (SELECT DISTINCT c.callsign FROM controllers c WHERE c.facility != 'OBS')
        LIMIT 1000  -- Limit for testing
    )
    SELECT COUNT(*) as matches
    FROM flight_transceivers ft 
    JOIN atc_transceivers at ON ft.frequency = at.frequency 
    AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= 180
    WHERE (SQRT(POWER(ft.position_lat - at.position_lat, 2) + POWER(ft.position_lon - at.position_lon, 2))) <= 300;
    """
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(test_query)
            result = cur.fetchone()
            
            execution_plan = result[0][0]  # Get the JSON execution plan
            
            print("\n" + "="*80)
            print("QUERY PERFORMANCE ANALYSIS")
            print("="*80)
            
            # Extract key metrics from execution plan
            total_cost = execution_plan.get('Total Cost', 0)
            execution_time = execution_plan.get('Execution Time', 0)
            planning_time = execution_plan.get('Planning Time', 0)
            
            print(f"Planning Time: {planning_time:.2f} ms")
            print(f"Execution Time: {execution_time:.2f} ms")
            print(f"Total Cost: {total_cost:.2f}")
            
            # Look for sequential scans in the plan
            def find_seq_scans(node, depth=0):
                indent = "  " * depth
                node_type = node.get('Node Type', '')
                
                if 'Seq Scan' in node_type:
                    relation_name = node.get('Relation Name', 'Unknown')
                    cost = node.get('Total Cost', 0)
                    rows = node.get('Actual Rows', 0)
                    print(f"{indent}⚠️  Sequential Scan on {relation_name} (Cost: {cost:.2f}, Rows: {rows})")
                elif 'Index' in node_type:
                    index_name = node.get('Index Name', 'Unknown')
                    cost = node.get('Total Cost', 0)
                    rows = node.get('Actual Rows', 0)
                    print(f"{indent}✅ Index Scan on {index_name} (Cost: {cost:.2f}, Rows: {rows})")
                
                # Recursively check child nodes
                for child in node.get('Plans', []):
                    find_seq_scans(child, depth + 1)
            
            print("\nExecution Plan Analysis:")
            find_seq_scans(execution_plan.get('Plan', {}))
            
            return execution_plan
            
    except Exception as e:
        logger.error(f"Failed to test query performance: {e}")
        return None

def check_missing_indexes(conn):
    """Check for missing indexes based on query patterns"""
    logger.info("Checking for missing indexes...")
    
    missing_indexes = []
    
    # Check for entity_type index on transceivers
    check_query = """
    SELECT COUNT(*) 
    FROM pg_indexes 
    WHERE tablename = 'transceivers' 
    AND indexdef LIKE '%entity_type%';
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(check_query)
            count = cur.fetchone()[0]
            
            if count == 0:
                missing_indexes.append({
                    'table': 'transceivers',
                    'column': 'entity_type',
                    'reason': 'Primary filter in ATC coverage queries',
                    'priority': 'HIGH'
                })
            
            # Check for frequency + timestamp composite index
            check_query = """
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE tablename = 'transceivers' 
            AND (indexdef LIKE '%frequency%' AND indexdef LIKE '%timestamp%');
            """
            
            cur.execute(check_query)
            count = cur.fetchone()[0]
            
            if count == 0:
                missing_indexes.append({
                    'table': 'transceivers',
                    'columns': 'frequency, timestamp',
                    'reason': 'Critical JOIN condition in frequency matching',
                    'priority': 'CRITICAL'
                })
            
            # Check for facility filter index on controllers
            check_query = """
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE tablename = 'controllers' 
            AND indexdef LIKE '%facility%';
            """
            
            cur.execute(check_query)
            count = cur.fetchone()[0]
            
            if count == 0:
                missing_indexes.append({
                    'table': 'controllers',
                    'column': 'facility',
                    'reason': 'Filter for excluding observers (facility != OBS)',
                    'priority': 'HIGH'
                })
            
            print("\n" + "="*80)
            print("MISSING INDEX ANALYSIS")
            print("="*80)
            
            if missing_indexes:
                for idx in missing_indexes:
                    print(f"\n❌ Missing Index:")
                    print(f"   Table: {idx['table']}")
                    print(f"   Column(s): {idx.get('column', idx.get('columns', 'N/A'))}")
                    print(f"   Priority: {idx['priority']}")
                    print(f"   Reason: {idx['reason']}")
            else:
                print("\n✅ All critical indexes appear to be present")
                
            return missing_indexes
            
    except Exception as e:
        logger.error(f"Failed to check missing indexes: {e}")
        return []

def generate_recommendations(table_stats, index_stats, missing_indexes, query_performance):
    """Generate optimization recommendations"""
    
    print("\n" + "="*80)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("="*80)
    
    recommendations = []
    
    # Analyze table sizes for index impact
    for stat in table_stats:
        if stat['live_rows'] > 100000:  # Large table
            recommendations.append({
                'type': 'INDEX',
                'priority': 'HIGH',
                'table': stat['tablename'],
                'recommendation': f"Table {stat['tablename']} has {stat['live_rows']:,} rows - indexes are critical for performance"
            })
    
    # Check for unused indexes
    for idx in index_stats:
        if idx['idx_scan'] == 0:
            recommendations.append({
                'type': 'CLEANUP',
                'priority': 'MEDIUM',
                'table': idx['tablename'],
                'recommendation': f"Index {idx['indexname']} is unused - consider dropping"
            })
    
    # Missing index recommendations
    for idx in missing_indexes:
        priority = 'CRITICAL' if idx['priority'] == 'CRITICAL' else 'HIGH'
        recommendations.append({
            'type': 'CREATE_INDEX',
            'priority': priority,
            'table': idx['table'],
            'recommendation': f"Create index on {idx.get('column', idx.get('columns', 'N/A'))} - {idx['reason']}"
        })
    
    # Sort by priority
    priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    recommendations.sort(key=lambda x: priority_order.get(x['priority'], 4))
    
    for i, rec in enumerate(recommendations, 1):
        priority_icon = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(rec['priority'], '⚪')
        print(f"\n{i}. {priority_icon} {rec['priority']} - {rec['type']}")
        print(f"   Table: {rec['table']}")
        print(f"   Action: {rec['recommendation']}")
    
    return recommendations

def main():
    """Main analysis function"""
    logger.info("Starting ATC Coverage Performance Analysis...")
    
    conn = get_database_connection()
    
    try:
        # Run all analyses
        table_stats = analyze_table_stats(conn)
        index_stats = analyze_existing_indexes(conn)
        query_performance = test_query_performance(conn)
        missing_indexes = check_missing_indexes(conn)
        
        # Generate recommendations
        recommendations = generate_recommendations(table_stats, index_stats, missing_indexes, query_performance)
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        print(f"Generated {len(recommendations)} recommendations")
        print("Review the database/013_optimize_atc_coverage_indexes.sql file for proposed index optimizations")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
