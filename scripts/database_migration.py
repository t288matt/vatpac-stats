#!/usr/bin/env python3
"""
Database Migration Script - VATSIM Data Optimization
Implements storage optimizations while preserving data quality
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigration:
    def __init__(self, db_path: str = "atc_optimization.db"):
        self.db_path = db_path
        self.backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def backup_database(self):
        """Create backup before migration"""
        try:
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"Database backed up to: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False
    
    def optimize_flights_table(self):
        """Optimize flights table for storage efficiency"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Step 1: Add new optimized columns
            logger.info("Adding optimized columns to flights table...")
            
            # Add compressed position columns
            cursor.execute("""
                ALTER TABLE flights ADD COLUMN position_lat INTEGER;
            """)
            
            cursor.execute("""
                ALTER TABLE flights ADD COLUMN position_lng INTEGER;
            """)
            
            # Add optimized data type columns
            cursor.execute("""
                ALTER TABLE flights ADD COLUMN altitude_small SMALLINT;
            """)
            
            cursor.execute("""
                ALTER TABLE flights ADD COLUMN speed_small SMALLINT;
            """)
            
            # Step 2: Migrate existing data
            logger.info("Migrating existing flight data...")
            
            # Update position data (compress coordinates)
            cursor.execute("""
                UPDATE flights 
                SET position_lat = CAST(JSON_EXTRACT(position, '$.lat') * 1000000 AS INTEGER),
                    position_lng = CAST(JSON_EXTRACT(position, '$.lng') * 1000000 AS INTEGER)
                WHERE position IS NOT NULL AND position != '';
            """)
            
            # Update altitude and speed (convert to SMALLINT)
            cursor.execute("""
                UPDATE flights 
                SET altitude_small = CAST(altitude AS SMALLINT)
                WHERE altitude IS NOT NULL AND altitude <= 65535;
            """)
            
            cursor.execute("""
                UPDATE flights 
                SET speed_small = CAST(speed AS SMALLINT)
                WHERE speed IS NOT NULL AND speed <= 65535;
            """)
            
            # Step 3: Create indexes for performance
            logger.info("Creating optimized indexes...")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_flights_position_compressed 
                ON flights(position_lat, position_lng);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_flights_altitude_small 
                ON flights(altitude_small);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_flights_speed_small 
                ON flights(speed_small);
            """)
            
            conn.commit()
            logger.info("Flights table optimization completed successfully!")
            
        except Exception as e:
            logger.error(f"Failed to optimize flights table: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_summary_tables(self):
        """Create summary tables for historical data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create flight summaries table
            logger.info("Creating flight_summaries table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flight_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    callsign VARCHAR(20) NOT NULL,
                    aircraft_type VARCHAR(10),
                    departure VARCHAR(10),
                    arrival VARCHAR(10),
                    route TEXT,
                    max_altitude SMALLINT,
                    duration_minutes SMALLINT,
                    controller_id INTEGER,
                    sector_id INTEGER,
                    completed_at DATETIME NOT NULL,
                    FOREIGN KEY (controller_id) REFERENCES controllers(id),
                    FOREIGN KEY (sector_id) REFERENCES sectors(id)
                );
            """)
            
            # Create movement summaries table
            logger.info("Creating movement_summaries table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movement_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    airport_icao VARCHAR(10) NOT NULL,
                    movement_type VARCHAR(10) NOT NULL,
                    aircraft_type VARCHAR(10),
                    date DATE NOT NULL,
                    hour SMALLINT NOT NULL,
                    count SMALLINT DEFAULT 1,
                    UNIQUE(airport_icao, movement_type, aircraft_type, date, hour)
                );
            """)
            
            # Create indexes for summary tables
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign 
                ON flight_summaries(callsign);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_flight_summaries_completed 
                ON flight_summaries(completed_at);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_movement_summaries_airport 
                ON movement_summaries(airport_icao, date);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_movement_summaries_type 
                ON movement_summaries(movement_type, date);
            """)
            
            conn.commit()
            logger.info("Summary tables created successfully!")
            
        except Exception as e:
            logger.error(f"Failed to create summary tables: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def optimize_database_settings(self):
        """Apply database optimization settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            logger.info("Applying database optimization settings...")
            
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode = WAL;")
            
            # Set cache size to 64MB
            cursor.execute("PRAGMA cache_size = -64000;")
            
            # Enable memory-mapped I/O
            cursor.execute("PRAGMA mmap_size = 268435456;")
            
            # Set page size for better compression
            cursor.execute("PRAGMA page_size = 4096;")
            
            # Enable auto-vacuum for automatic cleanup
            cursor.execute("PRAGMA auto_vacuum = INCREMENTAL;")
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # Set synchronous mode for balance of safety and speed
            cursor.execute("PRAGMA synchronous = NORMAL;")
            
            conn.commit()
            logger.info("Database optimization settings applied successfully!")
            
        except Exception as e:
            logger.error(f"Failed to apply database settings: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_optimization_stats(self) -> Dict[str, any]:
        """Get optimization statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get table sizes
            cursor.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND name IN ('flights', 'controllers', 'traffic_movements', 'flight_summaries', 'movement_summaries');
            """)
            tables = cursor.fetchall()
            
            # Get record counts
            stats = {}
            for table_name in ['flights', 'controllers', 'traffic_movements', 'flight_summaries', 'movement_summaries']:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    count = cursor.fetchone()[0]
                    stats[f"{table_name}_count"] = count
                except:
                    stats[f"{table_name}_count"] = 0
            
            # Get database file size
            file_size = os.path.getsize(self.db_path)
            stats['database_size_mb'] = file_size / (1024 * 1024)
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get optimization stats: {e}")
            return {}
    
    def run_full_migration(self):
        """Run complete database migration"""
        logger.info("Starting database migration for storage optimization...")
        
        try:
            # Step 1: Backup database
            if not self.backup_database():
                raise Exception("Failed to backup database")
            
            # Step 2: Create summary tables
            self.create_summary_tables()
            
            # Step 3: Optimize flights table
            self.optimize_flights_table()
            
            # Step 4: Apply database settings
            self.optimize_database_settings()
            
            # Step 5: Get optimization stats
            stats = self.get_optimization_stats()
            
            logger.info("Database migration completed successfully!")
            logger.info(f"Migration stats: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            logger.info(f"Restore from backup: {self.backup_path}")
            raise

if __name__ == "__main__":
    migration = DatabaseMigration()
    migration.run_full_migration() 