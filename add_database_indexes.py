#!/usr/bin/env python3
"""
Add Database Indexes for Faster Read Operations

This script adds optimized indexes to the VATSIM database for faster query performance.
Can be run outside of Docker by connecting directly to PostgreSQL.
"""

import os
import sys
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseIndexer:
    """Add indexes to improve database read performance"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None
        self.cursor = None
        
    def connect_database(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            self.cursor = self.conn.cursor()
            logger.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def close_database(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def get_existing_indexes(self):
        """Get list of existing indexes"""
        try:
            self.cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname;
            """)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting existing indexes: {e}")
            return []
    
    def add_performance_indexes(self):
        """Add performance-optimized indexes"""
        
        # Define indexes for faster read operations
        indexes = [
            # Controllers table indexes
            {
                'name': 'idx_controllers_status_last_seen',
                'table': 'controllers',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_controllers_status_last_seen ON controllers(status, last_seen DESC)',
                'description': 'Index for active controllers by status and last seen time'
            },
            {
                'name': 'idx_controllers_facility_workload',
                'table': 'controllers',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_controllers_facility_workload ON controllers(facility, workload_score DESC)',
                'description': 'Index for controllers by facility and workload'
            },
            {
                'name': 'idx_controllers_callsign',
                'table': 'controllers',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_controllers_callsign ON controllers(callsign)',
                'description': 'Index for controller callsign lookups'
            },
            
            # Flights table indexes
            {
                'name': 'idx_flights_status_last_updated',
                'table': 'flights',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_flights_status_last_updated ON flights(status, last_updated DESC)',
                'description': 'Index for active flights by status and update time'
            },
            {
                'name': 'idx_flights_aircraft_type',
                'table': 'flights',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_flights_aircraft_type ON flights(aircraft_type)',
                'description': 'Index for flights by aircraft type'
            },
            {
                'name': 'idx_flights_departure_arrival',
                'table': 'flights',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_flights_departure_arrival ON flights(departure, arrival)',
                'description': 'Index for flights by departure and arrival airports'
            },
            {
                'name': 'idx_flights_callsign',
                'table': 'flights',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_flights_callsign ON flights(callsign)',
                'description': 'Index for flight callsign lookups'
            },
            {
                'name': 'idx_flights_altitude_speed',
                'table': 'flights',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_flights_altitude_speed ON flights(altitude, speed)',
                'description': 'Index for flights by altitude and speed'
            },
            
            # Traffic movements table indexes
            {
                'name': 'idx_traffic_movements_timestamp',
                'table': 'traffic_movements',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_traffic_movements_timestamp ON traffic_movements(timestamp DESC)',
                'description': 'Index for traffic movements by timestamp'
            },
            {
                'name': 'idx_traffic_movements_airport_type',
                'table': 'traffic_movements',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_traffic_movements_airport_type ON traffic_movements(airport_code, movement_type)',
                'description': 'Index for traffic movements by airport and type'
            },
            {
                'name': 'idx_traffic_movements_aircraft',
                'table': 'traffic_movements',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_traffic_movements_aircraft ON traffic_movements(aircraft_callsign)',
                'description': 'Index for traffic movements by aircraft callsign'
            },
            
            # Sectors table indexes
            {
                'name': 'idx_sectors_facility_status',
                'table': 'sectors',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_sectors_facility_status ON sectors(facility, status)',
                'description': 'Index for sectors by facility and status'
            },
            {
                'name': 'idx_sectors_controller_id',
                'table': 'sectors',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_sectors_controller_id ON sectors(controller_id)',
                'description': 'Index for sectors by controller ID'
            },
            
            # Flight summaries table indexes
            {
                'name': 'idx_flight_summaries_completed_at',
                'table': 'flight_summaries',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_flight_summaries_completed_at ON flight_summaries(completed_at DESC)',
                'description': 'Index for flight summaries by completion time'
            },
            {
                'name': 'idx_flight_summaries_callsign',
                'table': 'flight_summaries',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign ON flight_summaries(callsign)',
                'description': 'Index for flight summaries by callsign'
            },
            
            # Movement summaries table indexes
            {
                'name': 'idx_movement_summaries_airport_date',
                'table': 'movement_summaries',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_movement_summaries_airport_date ON movement_summaries(airport_icao, date)',
                'description': 'Index for movement summaries by airport and date'
            },
            {
                'name': 'idx_movement_summaries_type_hour',
                'table': 'movement_summaries',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_movement_summaries_type_hour ON movement_summaries(movement_type, hour)',
                'description': 'Index for movement summaries by type and hour'
            }
        ]
        
        created_indexes = []
        failed_indexes = []
        
        logger.info("Adding performance indexes...")
        
        for index in indexes:
            try:
                logger.info(f"Creating index: {index['name']} - {index['description']}")
                self.cursor.execute(index['sql'])
                created_indexes.append(index['name'])
                logger.info(f"✅ Created index: {index['name']}")
            except Exception as e:
                logger.error(f"❌ Failed to create index {index['name']}: {e}")
                failed_indexes.append(index['name'])
        
        # Commit changes
        self.conn.commit()
        
        logger.info(f"\nIndex creation summary:")
        logger.info(f"✅ Created: {len(created_indexes)} indexes")
        logger.info(f"❌ Failed: {len(failed_indexes)} indexes")
        
        if created_indexes:
            logger.info(f"Created indexes: {', '.join(created_indexes)}")
        
        if failed_indexes:
            logger.info(f"Failed indexes: {', '.join(failed_indexes)}")
        
        return {
            'created': created_indexes,
            'failed': failed_indexes,
            'total': len(indexes)
        }
    
    def analyze_table_statistics(self):
        """Analyze table statistics for query optimization"""
        try:
            logger.info("Analyzing table statistics...")
            
            tables = ['controllers', 'flights', 'traffic_movements', 'sectors', 'flight_summaries', 'movement_summaries']
            
            for table in tables:
                try:
                    self.cursor.execute(f"ANALYZE {table}")
                    logger.info(f"✅ Analyzed table: {table}")
                except Exception as e:
                    logger.error(f"❌ Failed to analyze {table}: {e}")
            
            logger.info("Table analysis completed")
            
        except Exception as e:
            logger.error(f"Error analyzing tables: {e}")
    
    def get_index_performance_stats(self):
        """Get index usage statistics"""
        try:
            self.cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC;
            """)
            
            stats = self.cursor.fetchall()
            
            logger.info("\nIndex Performance Statistics:")
            logger.info("=" * 80)
            
            for stat in stats:
                logger.info(f"Table: {stat[1]}, Index: {stat[2]}")
                logger.info(f"  Scans: {stat[3]}, Tuples Read: {stat[4]}, Tuples Fetched: {stat[5]}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return []
    
    def optimize_database_settings(self):
        """Optimize database settings for read performance"""
        try:
            logger.info("Optimizing database settings...")
            
            # Set work_mem for better query performance
            self.cursor.execute("SET work_mem = '256MB'")
            
            # Set effective_cache_size
            self.cursor.execute("SET effective_cache_size = '1GB'")
            
            # Set random_page_cost for SSD
            self.cursor.execute("SET random_page_cost = 1.1")
            
            # Set seq_page_cost
            self.cursor.execute("SET seq_page_cost = 1.0")
            
            logger.info("✅ Database settings optimized")
            
        except Exception as e:
            logger.error(f"Error optimizing settings: {e}")

def main():
    """Main function"""
    
    # Database connection string
    # You can modify these values based on your setup
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "vatsim_data")
    DB_USER = os.getenv("DB_USER", "vatsim_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "vatsim_password")
    
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    logger.info("🗄️ Database Index Optimization Tool")
    logger.info("=" * 50)
    logger.info(f"Connecting to: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    # Initialize indexer
    indexer = DatabaseIndexer(connection_string)
    
    if not indexer.connect_database():
        logger.error("Failed to connect to database. Exiting.")
        sys.exit(1)
    
    try:
        # Show existing indexes
        logger.info("\n📊 Existing Indexes:")
        existing_indexes = indexer.get_existing_indexes()
        for index in existing_indexes:
            logger.info(f"  {index[1]}.{index[2]}")
        
        # Add performance indexes
        logger.info("\n🚀 Adding Performance Indexes:")
        result = indexer.add_performance_indexes()
        
        # Analyze table statistics
        logger.info("\n📈 Analyzing Table Statistics:")
        indexer.analyze_table_statistics()
        
        # Optimize database settings
        logger.info("\n⚙️ Optimizing Database Settings:")
        indexer.optimize_database_settings()
        
        # Show performance stats
        logger.info("\n📊 Index Performance Statistics:")
        indexer.get_index_performance_stats()
        
        logger.info("\n✅ Database optimization completed!")
        logger.info(f"Created {len(result['created'])} new indexes")
        
    except Exception as e:
        logger.error(f"Error during optimization: {e}")
    
    finally:
        indexer.close_database()

if __name__ == "__main__":
    main() 