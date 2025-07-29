#!/usr/bin/env python3
"""
Quick Data Integrity Test for VATSIM Database
"""

import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def quick_data_test():
    """Quick test of database integrity"""
    try:
        # Connect to database
        conn = sqlite3.connect("atc_optimization.db")
        cursor = conn.cursor()
        
        logger.info("🔍 Quick Data Integrity Test")
        logger.info("=" * 50)
        
        # Test 1: Check if database exists and is accessible
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        logger.info(f"✓ Database accessible - {table_count} tables found")
        
        # Test 2: Check record counts
        tables = ['atc_positions', 'flights', 'traffic_movements', 'sectors']
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"✓ Table {table}: {count} records")
            except Exception as e:
                logger.warning(f"⚠ Table {table}: Error - {e}")
        
        # Test 3: Check data freshness
        cursor.execute("SELECT MAX(last_seen) FROM atc_positions")
        latest_atc_position = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(last_updated) FROM flights")
        latest_flight = cursor.fetchone()[0]
        
        if latest_atc_position:
            logger.info(f"✓ Latest ATC position data: {latest_atc_position}")
        else:
            logger.warning("⚠ No ATC position data found")
            
        if latest_flight:
            logger.info(f"✓ Latest flight data: {latest_flight}")
        else:
            logger.warning("⚠ No flight data found")
        
        # Test 4: Check data quality
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN callsign IS NOT NULL AND callsign != '' THEN 1 END) as valid_callsigns
            FROM atc_positions
        """)
        atc_position_quality = cursor.fetchone()
        
        if atc_position_quality and atc_position_quality[0] > 0:
            quality_percent = (atc_position_quality[1] / atc_position_quality[0]) * 100
            logger.info(f"✓ ATC position data quality: {quality_percent:.1f}% valid callsigns")
        else:
            logger.warning("⚠ No ATC position data to check quality")
        
        # Test 5: Check for recent activity
        cursor.execute("""
            SELECT COUNT(*) FROM atc_positions 
            WHERE last_seen > datetime('now', '-1 hour')
        """)
        recent_atc_positions = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM flights 
            WHERE last_updated > datetime('now', '-1 hour')
        """)
        recent_flights = cursor.fetchone()[0]
        
        logger.info(f"✓ Recent activity: {recent_atc_positions} ATC positions, {recent_flights} flights in last hour")
        
        # Test 6: Database size
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        
        db_size_mb = (page_count * page_size) / (1024 * 1024)
        logger.info(f"✓ Database size: {db_size_mb:.2f} MB")
        
        # Overall assessment
        logger.info("=" * 50)
        logger.info("📊 DATA INTEGRITY ASSESSMENT")
        logger.info("=" * 50)
        
        # Calculate integrity score
        score = 0
        max_score = 100
        
        # Database accessibility (20 points)
        score += 20
        
        # Data presence (30 points)
        if recent_atc_positions > 0:
            score += 15
        if recent_flights > 0:
            score += 15
        
        # Data freshness (30 points)
        if latest_atc_position and latest_flight:
            score += 30
        elif latest_atc_position or latest_flight:
            score += 15
        
        # Data quality (20 points)
        if atc_position_quality and atc_position_quality[0] > 0:
            quality_percent = (atc_position_quality[1] / atc_position_quality[0]) * 100
            if quality_percent > 90:
                score += 20
            elif quality_percent > 70:
                score += 15
            elif quality_percent > 50:
                score += 10
        
        logger.info(f"🎯 Integrity Score: {score}/{max_score} ({score/max_score*100:.1f}%)")
        
        if score >= 80:
            logger.info("🎉 EXCELLENT - Database is healthy and ready for migration")
        elif score >= 60:
            logger.info("✅ GOOD - Database is functional with minor issues")
        elif score >= 40:
            logger.info("⚠️ FAIR - Database has some issues that need attention")
        else:
            logger.error("❌ POOR - Database has significant issues")
        
        # Recommendations
        logger.info("\n📋 RECOMMENDATIONS:")
        if recent_atc_positions == 0:
            logger.info("  • Start the application to collect ATC position data")
        if recent_flights == 0:
            logger.info("  • Start the application to collect flight data")
        if db_size_mb > 100:
            logger.info("  • Consider database optimization for large size")
        if score >= 60:
            logger.info("  • Database is ready for PostgreSQL migration")
        else:
            logger.info("  • Fix data issues before migration")
        
        conn.close()
        return score >= 60
        
    except Exception as e:
        logger.error(f"❌ Data integrity test failed: {e}")
        return False

if __name__ == "__main__":
    success = quick_data_test()
    if success:
        logger.info("\n✅ Quick test completed successfully")
    else:
        logger.error("\n❌ Quick test found issues") 