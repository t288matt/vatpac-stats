#!/usr/bin/env python3
"""
Data Integrity Test for VATSIM Data Collection System

This script performs comprehensive data integrity checks on the database
to ensure all data is properly stored, relationships are maintained,
and data quality standards are met.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataIntegrityTester:
    """Comprehensive data integrity testing for VATSIM database"""
    
    def __init__(self, db_path: str = "atc_optimization.db"):
        self.db_path = db_path
        self.conn = None
        self.engine = None
        self.session = None
        
    def connect_database(self):
        """Connect to the database"""
        try:
            # SQLite connection
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            
            # SQLAlchemy engine
            self.engine = create_engine(f"sqlite:///{self.db_path}")
            SessionLocal = sessionmaker(bind=self.engine)
            self.session = SessionLocal()
            
            logger.info("Successfully connected to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def test_table_structure(self):
        """Test database table structure and schema"""
        try:
            cursor = self.conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"Found {len(tables)} tables: {tables}")
            
            # Check required tables exist
            required_tables = [
                'controllers', 'sectors', 'flights', 'traffic_movements',
                'flight_summaries', 'movement_summaries', 'airport_config',
                'movement_detection_config', 'system_config', 'events'
            ]
            
            missing_tables = []
            for table in required_tables:
                if table not in tables:
                    missing_tables.append(table)
            
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
                return False
            else:
                logger.info("✓ All required tables exist")
            
            # Check table schemas
            for table in required_tables:
                if table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    logger.info(f"Table {table}: {len(columns)} columns")
                    
                    # Log column names for verification
                    column_names = [col[1] for col in columns]
                    logger.info(f"  Columns: {column_names}")
            
            return True
            
        except Exception as e:
            logger.error(f"Table structure test failed: {e}")
            return False
    
    def test_data_counts(self):
        """Test record counts and data volume"""
        try:
            cursor = self.conn.cursor()
            
            tables = ['controllers', 'sectors', 'flights', 'traffic_movements']
            counts = {}
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                counts[table] = count
                logger.info(f"Table {table}: {count} records")
            
            # Check for reasonable data volumes
            if counts.get('controllers', 0) > 0:
                logger.info("✓ Controllers data present")
            else:
                logger.warning("⚠ No controllers data found")
            
            if counts.get('flights', 0) > 0:
                logger.info("✓ Flights data present")
            else:
                logger.warning("⚠ No flights data found")
            
            return True
            
        except Exception as e:
            logger.error(f"Data counts test failed: {e}")
            return False
    
    def test_data_quality(self):
        """Test data quality and consistency"""
        try:
            cursor = self.conn.cursor()
            
            # Test controllers data quality
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN callsign IS NOT NULL AND callsign != '' THEN 1 END) as valid_callsigns,
                    COUNT(CASE WHEN facility IS NOT NULL AND facility != '' THEN 1 END) as valid_facilities,
                    COUNT(CASE WHEN last_seen IS NOT NULL THEN 1 END) as valid_timestamps
                FROM controllers
            """)
            controller_stats = cursor.fetchone()
            
            if controller_stats:
                total, valid_callsigns, valid_facilities, valid_timestamps = controller_stats
                if total > 0:
                    callsign_quality = (valid_callsigns / total) * 100
                    facility_quality = (valid_facilities / total) * 100
                    timestamp_quality = (valid_timestamps / total) * 100
                    
                    logger.info(f"Controller data quality:")
                    logger.info(f"  Callsigns: {callsign_quality:.1f}% valid")
                    logger.info(f"  Facilities: {facility_quality:.1f}% valid")
                    logger.info(f"  Timestamps: {timestamp_quality:.1f}% valid")
                    
                    if callsign_quality > 90 and facility_quality > 90:
                        logger.info("✓ Controller data quality is good")
                    else:
                        logger.warning("⚠ Controller data quality issues detected")
            
            # Test flights data quality
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN callsign IS NOT NULL AND callsign != '' THEN 1 END) as valid_callsigns,
                    COUNT(CASE WHEN aircraft_type IS NOT NULL AND aircraft_type != '' THEN 1 END) as valid_aircraft,
                    COUNT(CASE WHEN position_lat IS NOT NULL AND position_lng IS NOT NULL THEN 1 END) as valid_positions,
                    COUNT(CASE WHEN last_updated IS NOT NULL THEN 1 END) as valid_timestamps
                FROM flights
            """)
            flight_stats = cursor.fetchone()
            
            if flight_stats:
                total, valid_callsigns, valid_aircraft, valid_positions, valid_timestamps = flight_stats
                if total > 0:
                    callsign_quality = (valid_callsigns / total) * 100
                    aircraft_quality = (valid_aircraft / total) * 100
                    position_quality = (valid_positions / total) * 100
                    timestamp_quality = (valid_timestamps / total) * 100
                    
                    logger.info(f"Flight data quality:")
                    logger.info(f"  Callsigns: {callsign_quality:.1f}% valid")
                    logger.info(f"  Aircraft types: {aircraft_quality:.1f}% valid")
                    logger.info(f"  Positions: {position_quality:.1f}% valid")
                    logger.info(f"  Timestamps: {timestamp_quality:.1f}% valid")
                    
                    if callsign_quality > 90 and timestamp_quality > 90:
                        logger.info("✓ Flight data quality is good")
                    else:
                        logger.warning("⚠ Flight data quality issues detected")
            
            return True
            
        except Exception as e:
            logger.error(f"Data quality test failed: {e}")
            return False
    
    def test_data_freshness(self):
        """Test data freshness and update frequency"""
        try:
            cursor = self.conn.cursor()
            
            # Check most recent data timestamps
            cursor.execute("""
                SELECT 
                    MAX(last_seen) as latest_controller,
                    MAX(last_updated) as latest_flight
                FROM controllers, flights
            """)
            latest_data = cursor.fetchone()
            
            if latest_data:
                latest_controller, latest_flight = latest_data
                
                if latest_controller:
                    controller_age = datetime.now() - datetime.fromisoformat(latest_controller.replace('Z', '+00:00'))
                    logger.info(f"Latest controller data: {controller_age.total_seconds():.0f} seconds ago")
                    
                    if controller_age.total_seconds() < 300:  # 5 minutes
                        logger.info("✓ Controller data is fresh")
                    else:
                        logger.warning("⚠ Controller data may be stale")
                
                if latest_flight:
                    flight_age = datetime.now() - datetime.fromisoformat(latest_flight.replace('Z', '+00:00'))
                    logger.info(f"Latest flight data: {flight_age.total_seconds():.0f} seconds ago")
                    
                    if flight_age.total_seconds() < 300:  # 5 minutes
                        logger.info("✓ Flight data is fresh")
                    else:
                        logger.warning("⚠ Flight data may be stale")
            
            # Check data update frequency
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_updates,
                    COUNT(CASE WHEN last_seen > datetime('now', '-1 hour') THEN 1 END) as recent_updates
                FROM controllers
            """)
            update_stats = cursor.fetchone()
            
            if update_stats:
                total, recent = update_stats
                if total > 0:
                    update_frequency = (recent / total) * 100
                    logger.info(f"Data update frequency: {update_frequency:.1f}% in last hour")
                    
                    if update_frequency > 50:
                        logger.info("✓ Data is being updated regularly")
                    else:
                        logger.warning("⚠ Data update frequency is low")
            
            return True
            
        except Exception as e:
            logger.error(f"Data freshness test failed: {e}")
            return False
    
    def test_data_relationships(self):
        """Test foreign key relationships and data consistency"""
        try:
            cursor = self.conn.cursor()
            
            # Test controller-flight relationships
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_flights,
                    COUNT(CASE WHEN controller_id IS NOT NULL THEN 1 END) as flights_with_controllers,
                    COUNT(DISTINCT controller_id) as unique_controllers
                FROM flights
            """)
            flight_controller_stats = cursor.fetchone()
            
            if flight_controller_stats:
                total_flights, flights_with_controllers, unique_controllers = flight_controller_stats
                if total_flights > 0:
                    relationship_quality = (flights_with_controllers / total_flights) * 100
                    logger.info(f"Flight-controller relationships: {relationship_quality:.1f}% complete")
                    logger.info(f"Flights assigned to {unique_controllers} unique controllers")
                    
                    if relationship_quality > 50:
                        logger.info("✓ Flight-controller relationships are good")
                    else:
                        logger.warning("⚠ Many flights lack controller assignments")
            
            # Test sector relationships
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_sectors,
                    COUNT(CASE WHEN controller_id IS NOT NULL THEN 1 END) as sectors_with_controllers
                FROM sectors
            """)
            sector_stats = cursor.fetchone()
            
            if sector_stats:
                total_sectors, sectors_with_controllers = sector_stats
                if total_sectors > 0:
                    sector_quality = (sectors_with_controllers / total_sectors) * 100
                    logger.info(f"Sector-controller relationships: {sector_quality:.1f}% complete")
                    
                    if sector_quality > 0:
                        logger.info("✓ Sector-controller relationships exist")
                    else:
                        logger.warning("⚠ No sector-controller relationships found")
            
            return True
            
        except Exception as e:
            logger.error(f"Data relationships test failed: {e}")
            return False
    
    def test_data_consistency(self):
        """Test data consistency and logical integrity"""
        try:
            cursor = self.conn.cursor()
            
            # Test for duplicate callsigns
            cursor.execute("""
                SELECT callsign, COUNT(*) as count
                FROM controllers
                GROUP BY callsign
                HAVING COUNT(*) > 1
            """)
            duplicate_controllers = cursor.fetchall()
            
            if duplicate_controllers:
                logger.warning(f"⚠ Found {len(duplicate_controllers)} duplicate controller callsigns")
                for dup in duplicate_controllers[:5]:  # Show first 5
                    logger.warning(f"  Duplicate: {dup[0]} ({dup[1]} times)")
            else:
                logger.info("✓ No duplicate controller callsigns")
            
            # Test for invalid altitude values
            cursor.execute("""
                SELECT COUNT(*) as invalid_altitudes
                FROM flights
                WHERE altitude IS NOT NULL AND (altitude < 0 OR altitude > 60000)
            """)
            invalid_altitudes = cursor.fetchone()[0]
            
            if invalid_altitudes > 0:
                logger.warning(f"⚠ Found {invalid_altitudes} flights with invalid altitudes")
            else:
                logger.info("✓ All flight altitudes are within valid range")
            
            # Test for invalid speed values
            cursor.execute("""
                SELECT COUNT(*) as invalid_speeds
                FROM flights
                WHERE speed IS NOT NULL AND (speed < 0 OR speed > 1000)
            """)
            invalid_speeds = cursor.fetchone()[0]
            
            if invalid_speeds > 0:
                logger.warning(f"⚠ Found {invalid_speeds} flights with invalid speeds")
            else:
                logger.info("✓ All flight speeds are within valid range")
            
            # Test for future timestamps
            cursor.execute("""
                SELECT COUNT(*) as future_timestamps
                FROM flights
                WHERE last_updated > datetime('now', '+1 hour')
            """)
            future_timestamps = cursor.fetchone()[0]
            
            if future_timestamps > 0:
                logger.warning(f"⚠ Found {future_timestamps} flights with future timestamps")
            else:
                logger.info("✓ All timestamps are in the past")
            
            return True
            
        except Exception as e:
            logger.error(f"Data consistency test failed: {e}")
            return False
    
    def test_database_performance(self):
        """Test database performance and query efficiency"""
        try:
            cursor = self.conn.cursor()
            
            # Test query performance
            start_time = datetime.now()
            cursor.execute("SELECT COUNT(*) FROM flights")
            flight_count = cursor.fetchone()[0]
            query_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Flight count query: {query_time:.3f} seconds for {flight_count} records")
            
            if query_time < 1.0:
                logger.info("✓ Query performance is good")
            else:
                logger.warning("⚠ Query performance is slow")
            
            # Test index usage
            cursor.execute("PRAGMA index_list(flights)")
            indexes = cursor.fetchall()
            logger.info(f"Flights table has {len(indexes)} indexes")
            
            # Test database size
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            db_size_mb = (page_count * page_size) / (1024 * 1024)
            logger.info(f"Database size: {db_size_mb:.2f} MB")
            
            if db_size_mb < 100:
                logger.info("✓ Database size is reasonable")
            else:
                logger.warning("⚠ Database size is large, consider optimization")
            
            return True
            
        except Exception as e:
            logger.error(f"Database performance test failed: {e}")
            return False
    
    def generate_integrity_report(self):
        """Generate a comprehensive integrity report"""
        try:
            cursor = self.conn.cursor()
            
            # Get overall statistics
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM controllers) as controller_count,
                    (SELECT COUNT(*) FROM flights) as flight_count,
                    (SELECT COUNT(*) FROM sectors) as sector_count,
                    (SELECT COUNT(*) FROM traffic_movements) as movement_count
            """)
            stats = cursor.fetchone()
            
            # Get data age information
            cursor.execute("""
                SELECT 
                    MAX(last_seen) as latest_controller,
                    MAX(last_updated) as latest_flight
                FROM controllers, flights
            """)
            latest = cursor.fetchone()
            
            # Generate report
            report = {
                "timestamp": datetime.now().isoformat(),
                "database_path": self.db_path,
                "overall_stats": {
                    "controllers": stats[0] if stats else 0,
                    "flights": stats[1] if stats else 0,
                    "sectors": stats[2] if stats else 0,
                    "traffic_movements": stats[3] if stats else 0
                },
                "data_freshness": {
                    "latest_controller": latest[0] if latest else None,
                    "latest_flight": latest[1] if latest else None
                },
                "integrity_score": 0  # Will be calculated
            }
            
            # Calculate integrity score based on various factors
            score = 0
            max_score = 100
            
            # Data presence (20 points)
            if report["overall_stats"]["controllers"] > 0:
                score += 10
            if report["overall_stats"]["flights"] > 0:
                score += 10
            
            # Data freshness (30 points)
            if latest and latest[0]:
                controller_age = datetime.now() - datetime.fromisoformat(latest[0].replace('Z', '+00:00'))
                if controller_age.total_seconds() < 300:  # 5 minutes
                    score += 15
                elif controller_age.total_seconds() < 3600:  # 1 hour
                    score += 10
                else:
                    score += 5
            
            if latest and latest[1]:
                flight_age = datetime.now() - datetime.fromisoformat(latest[1].replace('Z', '+00:00'))
                if flight_age.total_seconds() < 300:  # 5 minutes
                    score += 15
                elif flight_age.total_seconds() < 3600:  # 1 hour
                    score += 10
                else:
                    score += 5
            
            # Data quality (50 points)
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN callsign IS NOT NULL AND callsign != '' THEN 1 END) * 100.0 / COUNT(*) as callsign_quality
                FROM controllers
            """)
            callsign_quality = cursor.fetchone()[0] or 0
            score += (callsign_quality / 100) * 25
            
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN callsign IS NOT NULL AND callsign != '' THEN 1 END) * 100.0 / COUNT(*) as flight_quality
                FROM flights
            """)
            flight_quality = cursor.fetchone()[0] or 0
            score += (flight_quality / 100) * 25
            
            report["integrity_score"] = min(score, max_score)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate integrity report: {e}")
            return None
    
    def run_all_tests(self):
        """Run all data integrity tests"""
        logger.info("Starting comprehensive data integrity tests...")
        
        if not self.connect_database():
            return False
        
        tests = [
            ("Table Structure", self.test_table_structure),
            ("Data Counts", self.test_data_counts),
            ("Data Quality", self.test_data_quality),
            ("Data Freshness", self.test_data_freshness),
            ("Data Relationships", self.test_data_relationships),
            ("Data Consistency", self.test_data_consistency),
            ("Database Performance", self.test_database_performance)
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\n--- Testing {test_name} ---")
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    logger.info(f"✓ {test_name} test passed")
                else:
                    logger.error(f"✗ {test_name} test failed")
            except Exception as e:
                logger.error(f"✗ {test_name} test failed with exception: {e}")
                results.append((test_name, False))
        
        # Generate integrity report
        logger.info("\n--- Generating Integrity Report ---")
        report = self.generate_integrity_report()
        
        if report:
            logger.info(f"Database Integrity Score: {report['integrity_score']:.1f}/100")
            logger.info(f"Controllers: {report['overall_stats']['controllers']}")
            logger.info(f"Flights: {report['overall_stats']['flights']}")
            logger.info(f"Sectors: {report['overall_stats']['sectors']}")
            logger.info(f"Traffic Movements: {report['overall_stats']['traffic_movements']}")
            
            if report['integrity_score'] >= 80:
                logger.info("🎉 Database integrity is excellent!")
            elif report['integrity_score'] >= 60:
                logger.info("✅ Database integrity is good")
            elif report['integrity_score'] >= 40:
                logger.info("⚠️ Database integrity needs attention")
            else:
                logger.error("❌ Database integrity is poor")
        
        # Summary
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        logger.info(f"\n{'='*50}")
        logger.info("DATA INTEGRITY TEST SUMMARY")
        logger.info(f"{'='*50}")
        
        for test_name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"{status}: {test_name}")
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All data integrity tests passed!")
        else:
            logger.warning("⚠️ Some data integrity issues detected")
        
        return passed == total

def main():
    """Main function to run data integrity tests"""
    
    # Check if database exists
    db_path = "atc_optimization.db"
    if not os.path.exists(db_path):
        logger.error(f"Database not found: {db_path}")
        logger.info("Please ensure the application is running and collecting data")
        sys.exit(1)
    
    # Run integrity tests
    tester = DataIntegrityTester(db_path)
    success = tester.run_all_tests()
    
    if success:
        logger.info("\n✅ Data integrity verification completed successfully")
        logger.info("Your database is healthy and ready for PostgreSQL migration")
    else:
        logger.error("\n❌ Data integrity issues detected")
        logger.info("Please address any issues before proceeding with migration")
        sys.exit(1)

if __name__ == "__main__":
    main() 