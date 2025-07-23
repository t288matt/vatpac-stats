#!/usr/bin/env python3
"""
Database Analysis for VATSIM Data Collection System

This script provides detailed analysis of the database structure,
data patterns, and quality metrics.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_database():
    """Comprehensive database analysis"""
    try:
        conn = sqlite3.connect("atc_optimization.db")
        cursor = conn.cursor()
        
        logger.info("🔬 Database Analysis Report")
        logger.info("=" * 60)
        
        # 1. Database Overview
        logger.info("\n📊 DATABASE OVERVIEW")
        logger.info("-" * 30)
        
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        logger.info(f"Total tables: {table_count}")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Tables: {', '.join(tables)}")
        
        # 2. Record Counts Analysis
        logger.info("\n📈 RECORD COUNTS")
        logger.info("-" * 30)
        
        for table in ['controllers', 'flights', 'traffic_movements', 'sectors']:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"{table.capitalize()}: {count:,} records")
        
        # 3. Data Freshness Analysis
        logger.info("\n⏰ DATA FRESHNESS")
        logger.info("-" * 30)
        
        # Controllers
        cursor.execute("SELECT MAX(last_seen), MIN(last_seen) FROM controllers")
        controller_times = cursor.fetchone()
        if controller_times[0]:
            latest_controller = datetime.fromisoformat(controller_times[0].replace('Z', '+00:00'))
            earliest_controller = datetime.fromisoformat(controller_times[1].replace('Z', '+00:00'))
            controller_span = latest_controller - earliest_controller
            logger.info(f"Controllers: {earliest_controller.strftime('%Y-%m-%d %H:%M')} to {latest_controller.strftime('%Y-%m-%d %H:%M')}")
            logger.info(f"Time span: {controller_span}")
        
        # Flights
        cursor.execute("SELECT MAX(last_updated), MIN(last_updated) FROM flights")
        flight_times = cursor.fetchone()
        if flight_times[0]:
            latest_flight = datetime.fromisoformat(flight_times[0].replace('Z', '+00:00'))
            earliest_flight = datetime.fromisoformat(flight_times[1].replace('Z', '+00:00'))
            flight_span = latest_flight - earliest_flight
            logger.info(f"Flights: {earliest_flight.strftime('%Y-%m-%d %H:%M')} to {latest_flight.strftime('%Y-%m-%d %H:%M')}")
            logger.info(f"Time span: {flight_span}")
        
        # 4. Data Quality Analysis
        logger.info("\n🔍 DATA QUALITY ANALYSIS")
        logger.info("-" * 30)
        
        # Controllers quality
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN callsign IS NOT NULL AND callsign != '' THEN 1 END) as valid_callsigns,
                COUNT(CASE WHEN facility IS NOT NULL AND facility != '' THEN 1 END) as valid_facilities,
                COUNT(CASE WHEN status IS NOT NULL THEN 1 END) as valid_status,
                COUNT(CASE WHEN last_seen IS NOT NULL THEN 1 END) as valid_timestamps
            FROM controllers
        """)
        controller_quality = cursor.fetchone()
        
        if controller_quality[0] > 0:
            total = controller_quality[0]
            logger.info(f"Controller Quality Metrics:")
            logger.info(f"  Callsigns: {controller_quality[1]}/{total} ({controller_quality[1]/total*100:.1f}%)")
            logger.info(f"  Facilities: {controller_quality[2]}/{total} ({controller_quality[2]/total*100:.1f}%)")
            logger.info(f"  Status: {controller_quality[3]}/{total} ({controller_quality[3]/total*100:.1f}%)")
            logger.info(f"  Timestamps: {controller_quality[4]}/{total} ({controller_quality[4]/total*100:.1f}%)")
        
        # Flights quality
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN callsign IS NOT NULL AND callsign != '' THEN 1 END) as valid_callsigns,
                COUNT(CASE WHEN aircraft_type IS NOT NULL AND aircraft_type != '' THEN 1 END) as valid_aircraft,
                COUNT(CASE WHEN position_lat IS NOT NULL AND position_lng IS NOT NULL THEN 1 END) as valid_positions,
                COUNT(CASE WHEN altitude IS NOT NULL THEN 1 END) as valid_altitude,
                COUNT(CASE WHEN speed IS NOT NULL THEN 1 END) as valid_speed,
                COUNT(CASE WHEN last_updated IS NOT NULL THEN 1 END) as valid_timestamps
            FROM flights
        """)
        flight_quality = cursor.fetchone()
        
        if flight_quality[0] > 0:
            total = flight_quality[0]
            logger.info(f"Flight Quality Metrics:")
            logger.info(f"  Callsigns: {flight_quality[1]}/{total} ({flight_quality[1]/total*100:.1f}%)")
            logger.info(f"  Aircraft types: {flight_quality[2]}/{total} ({flight_quality[2]/total*100:.1f}%)")
            logger.info(f"  Positions: {flight_quality[3]}/{total} ({flight_quality[3]/total*100:.1f}%)")
            logger.info(f"  Altitude: {flight_quality[4]}/{total} ({flight_quality[4]/total*100:.1f}%)")
            logger.info(f"  Speed: {flight_quality[5]}/{total} ({flight_quality[5]/total*100:.1f}%)")
            logger.info(f"  Timestamps: {flight_quality[6]}/{total} ({flight_quality[6]/total*100:.1f}%)")
        
        # 5. Data Patterns Analysis
        logger.info("\n📊 DATA PATTERNS")
        logger.info("-" * 30)
        
        # Top facilities
        cursor.execute("""
            SELECT facility, COUNT(*) as count
            FROM controllers
            WHERE facility IS NOT NULL AND facility != ''
            GROUP BY facility
            ORDER BY count DESC
            LIMIT 10
        """)
        top_facilities = cursor.fetchall()
        logger.info("Top Controller Facilities:")
        for facility, count in top_facilities:
            logger.info(f"  {facility}: {count} controllers")
        
        # Top aircraft types
        cursor.execute("""
            SELECT aircraft_type, COUNT(*) as count
            FROM flights
            WHERE aircraft_type IS NOT NULL AND aircraft_type != ''
            GROUP BY aircraft_type
            ORDER BY count DESC
            LIMIT 10
        """)
        top_aircraft = cursor.fetchall()
        logger.info("Top Aircraft Types:")
        for aircraft, count in top_aircraft:
            logger.info(f"  {aircraft}: {count} flights")
        
        # Altitude distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN altitude < 1000 THEN 'Ground'
                    WHEN altitude < 10000 THEN 'Low'
                    WHEN altitude < 25000 THEN 'Medium'
                    WHEN altitude < 45000 THEN 'High'
                    ELSE 'Very High'
                END as altitude_range,
                COUNT(*) as count
            FROM flights
            WHERE altitude IS NOT NULL
            GROUP BY altitude_range
            ORDER BY count DESC
        """)
        altitude_dist = cursor.fetchall()
        logger.info("Altitude Distribution:")
        for range_name, count in altitude_dist:
            logger.info(f"  {range_name}: {count} flights")
        
        # 6. Performance Analysis
        logger.info("\n⚡ PERFORMANCE ANALYSIS")
        logger.info("-" * 30)
        
        # Database size
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        db_size_mb = (page_count * page_size) / (1024 * 1024)
        logger.info(f"Database size: {db_size_mb:.2f} MB")
        
        # Table sizes
        for table in ['controllers', 'flights', 'traffic_movements']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            estimated_size_kb = count * 0.5  # Rough estimate
            logger.info(f"{table.capitalize()} table: {count:,} records (~{estimated_size_kb:.1f} KB)")
        
        # 7. Data Relationships
        logger.info("\n🔗 DATA RELATIONSHIPS")
        logger.info("-" * 30)
        
        # Controller-flight relationships
        cursor.execute("""
            SELECT 
                COUNT(*) as total_flights,
                COUNT(CASE WHEN controller_id IS NOT NULL THEN 1 END) as flights_with_controllers,
                COUNT(DISTINCT controller_id) as unique_controllers
            FROM flights
        """)
        flight_controller_stats = cursor.fetchone()
        if flight_controller_stats[0] > 0:
            relationship_percent = (flight_controller_stats[1] / flight_controller_stats[0]) * 100
            logger.info(f"Flights with controller assignments: {relationship_percent:.1f}%")
            logger.info(f"Flights assigned to {flight_controller_stats[2]} unique controllers")
        
        # 8. Migration Readiness Assessment
        logger.info("\n🚀 MIGRATION READINESS")
        logger.info("-" * 30)
        
        readiness_score = 0
        max_score = 100
        
        # Data presence (25 points)
        if flight_controller_stats[0] > 0:
            readiness_score += 25
        
        # Data quality (25 points)
        if flight_quality and flight_quality[0] > 0:
            quality_score = (flight_quality[1] / flight_quality[0]) * 100
            if quality_score > 90:
                readiness_score += 25
            elif quality_score > 70:
                readiness_score += 20
            elif quality_score > 50:
                readiness_score += 15
        
        # Data freshness (25 points)
        if latest_flight:
            time_diff = datetime.now() - latest_flight
            if time_diff.total_seconds() < 300:  # 5 minutes
                readiness_score += 25
            elif time_diff.total_seconds() < 3600:  # 1 hour
                readiness_score += 20
            elif time_diff.total_seconds() < 86400:  # 1 day
                readiness_score += 10
        
        # Database health (25 points)
        if db_size_mb < 100:  # Reasonable size
            readiness_score += 25
        elif db_size_mb < 500:
            readiness_score += 20
        elif db_size_mb < 1000:
            readiness_score += 15
        
        logger.info(f"Migration Readiness Score: {readiness_score}/{max_score} ({readiness_score/max_score*100:.1f}%)")
        
        if readiness_score >= 80:
            logger.info("🎉 EXCELLENT - Ready for PostgreSQL migration")
        elif readiness_score >= 60:
            logger.info("✅ GOOD - Ready for migration with minor considerations")
        elif readiness_score >= 40:
            logger.info("⚠️ FAIR - Migration possible but needs attention")
        else:
            logger.error("❌ POOR - Fix issues before migration")
        
        # 9. Recommendations
        logger.info("\n📋 RECOMMENDATIONS")
        logger.info("-" * 30)
        
        if readiness_score >= 60:
            logger.info("✅ Database is ready for PostgreSQL migration")
            logger.info("✅ Data quality is excellent")
            logger.info("✅ Data freshness is good")
            logger.info("✅ Database size is optimal")
        else:
            if flight_controller_stats[0] == 0:
                logger.info("⚠️ Start the application to collect data")
            if flight_quality and flight_quality[1]/flight_quality[0] < 0.9:
                logger.info("⚠️ Data quality needs improvement")
            if latest_flight and (datetime.now() - latest_flight).total_seconds() > 3600:
                logger.info("⚠️ Data is stale, restart the application")
            if db_size_mb > 100:
                logger.info("⚠️ Consider database optimization")
        
        conn.close()
        return readiness_score >= 60
        
    except Exception as e:
        logger.error(f"❌ Database analysis failed: {e}")
        return False

if __name__ == "__main__":
    success = analyze_database()
    if success:
        logger.info("\n✅ Database analysis completed successfully")
    else:
        logger.error("\n❌ Database analysis found issues") 