#!/usr/bin/env python3
"""
All Aircraft ATC Communication Analysis Script

This script analyzes all aircraft in the database to determine what percentage
of their flight records occurred during ATC communication periods.

Usage:
    python scripts/analyze_all_aircraft_atc.py
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
import pandas as pd

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

def run_individual_aircraft_analysis(conn):
    """Run analysis for all individual aircraft"""
    query = """
    WITH flight_transceivers AS (
        SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
        FROM transceivers t 
        WHERE t.entity_type = 'flight'
    ),
    atc_transceivers AS (
        SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
        FROM transceivers t 
        WHERE t.entity_type = 'atc' 
        AND t.callsign IN (SELECT DISTINCT c.callsign FROM controllers c WHERE c.facility != 'OBS')
    ),
    frequency_matches AS (
        SELECT ft.callsign as flight_callsign, ft.frequency_mhz, ft.timestamp as flight_time
        FROM flight_transceivers ft 
        JOIN atc_transceivers at ON ft.frequency_mhz = at.frequency_mhz 
        AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= 180
        WHERE (SQRT(POWER(ft.position_lat - at.position_lat, 2) + POWER(ft.position_lon - at.position_lon, 2))) <= 300
    ),
    flight_records_with_atc AS (
        SELECT f.callsign, COUNT(*) as records_with_atc
        FROM flights f 
        WHERE EXISTS (
            SELECT 1 FROM frequency_matches fm 
            WHERE fm.flight_callsign = f.callsign 
            AND ABS(EXTRACT(EPOCH FROM (f.last_updated - fm.flight_time))) <= 180
        )
        GROUP BY f.callsign
    ),
    flight_records_total AS (
        SELECT callsign, COUNT(*) as total_records 
        FROM flights 
        GROUP BY callsign
    )
    SELECT 
        fr.callsign,
        fr.total_records,
        COALESCE(fa.records_with_atc, 0) as records_with_atc,
        ROUND((COALESCE(fa.records_with_atc, 0)::numeric / fr.total_records::numeric * 100), 2) as percentage_with_atc
    FROM flight_records_total fr
    LEFT JOIN flight_records_with_atc fa ON fr.callsign = fa.callsign
    ORDER BY percentage_with_atc DESC, fr.total_records DESC;
    """
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            return results
    except Exception as e:
        logger.error(f"Failed to run individual aircraft analysis: {e}")
        return []

def run_overall_statistics(conn):
    """Run overall statistics analysis"""
    query = """
    WITH flight_transceivers AS (
        SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
        FROM transceivers t 
        WHERE t.entity_type = 'flight'
    ),
    atc_transceivers AS (
        SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
        FROM transceivers t 
        WHERE t.entity_type = 'atc' 
        AND t.callsign IN (SELECT DISTINCT c.callsign FROM controllers c WHERE c.facility != 'OBS')
    ),
    frequency_matches AS (
        SELECT ft.callsign as flight_callsign, ft.frequency_mhz, ft.timestamp as flight_time
        FROM flight_transceivers ft 
        JOIN atc_transceivers at ON ft.frequency_mhz = at.frequency_mhz 
        AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= 180
        WHERE (SQRT(POWER(ft.position_lat - at.position_lat, 2) + POWER(ft.position_lon - at.position_lon, 2))) <= 300
    ),
    flight_records_with_atc AS (
        SELECT f.callsign, COUNT(*) as records_with_atc
        FROM flights f 
        WHERE EXISTS (
            SELECT 1 FROM frequency_matches fm 
            WHERE fm.flight_callsign = f.callsign 
            AND ABS(EXTRACT(EPOCH FROM (f.last_updated - fm.flight_time))) <= 180
        )
        GROUP BY f.callsign
    ),
    flight_records_total AS (
        SELECT callsign, COUNT(*) as total_records 
        FROM flights 
        GROUP BY callsign
    )
    SELECT 
        COUNT(*) as total_flights,
        SUM(fr.total_records) as total_flight_records,
        SUM(COALESCE(fa.records_with_atc, 0)) as total_records_with_atc,
        ROUND((SUM(COALESCE(fa.records_with_atc, 0))::numeric / SUM(fr.total_records)::numeric * 100), 2) as overall_percentage_with_atc
    FROM flight_records_total fr
    LEFT JOIN flight_records_with_atc fa ON fr.callsign = fa.callsign;
    """
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            result = cursor.fetchone()
            return result
    except Exception as e:
        logger.error(f"Failed to run overall statistics: {e}")
        return None

def save_results_to_file(individual_results, overall_stats, output_file):
    """Save results to a CSV file"""
    try:
        # Convert to DataFrame
        df = pd.DataFrame(individual_results)
        
        # Save individual aircraft results
        df.to_csv(output_file, index=False)
        
        # Save overall statistics to a separate file
        stats_file = output_file.replace('.csv', '_overall_stats.txt')
        with open(stats_file, 'w') as f:
            f.write("OVERALL ATC COMMUNICATION STATISTICS\n")
            f.write("=" * 50 + "\n")
            f.write(f"Total flights analyzed: {overall_stats['total_flights']:,}\n")
            f.write(f"Total flight records: {overall_stats['total_flight_records']:,}\n")
            f.write(f"Total records with ATC: {overall_stats['total_records_with_atc']:,}\n")
            f.write(f"Overall percentage with ATC: {overall_stats['overall_percentage_with_atc']}%\n")
            f.write(f"\nAnalysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        logger.info(f"Results saved to {output_file}")
        logger.info(f"Overall statistics saved to {stats_file}")
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")

def main():
    """Main function"""
    print("All Aircraft ATC Communication Analysis")
    print("=" * 50)
    
    # Connect to database
    conn = get_database_connection()
    
    try:
        logger.info("Running individual aircraft analysis...")
        individual_results = run_individual_aircraft_analysis(conn)
        
        logger.info("Running overall statistics...")
        overall_stats = run_overall_statistics(conn)
        
        if not individual_results:
            logger.error("No results returned from analysis")
            return
        
        # Display summary
        print(f"\nAnalysis Results:")
        print(f"Total aircraft analyzed: {len(individual_results)}")
        
        if overall_stats:
            print(f"Overall percentage with ATC: {overall_stats['overall_percentage_with_atc']}%")
            print(f"Total flight records: {overall_stats['total_flight_records']:,}")
            print(f"Records with ATC: {overall_stats['total_records_with_atc']:,}")
        
        # Show top 10 aircraft by ATC percentage
        print(f"\nTop 10 aircraft by ATC communication percentage:")
        for i, result in enumerate(individual_results[:10]):
            print(f"{i+1:2d}. {result['callsign']:15s} - {result['percentage_with_atc']:5.2f}% ({result['records_with_atc']:4d}/{result['total_records']:4d} records)")
        
        # Save results
        output_file = f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        save_results_to_file(individual_results, overall_stats, output_file)
        
        print(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
