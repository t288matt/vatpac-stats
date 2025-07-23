#!/usr/bin/env python3
"""
PostgreSQL Migration Script for VATSIM Data Collection System

This script migrates the existing SQLite database to PostgreSQL with optimized
schema design, partitioning, and performance improvements.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PostgreSQLMigrator:
    """Handles migration from SQLite to PostgreSQL"""
    
    def __init__(self, sqlite_path: str, pg_connection_string: str):
        self.sqlite_path = sqlite_path
        self.pg_connection_string = pg_connection_string
        self.sqlite_conn = None
        self.pg_conn = None
        self.pg_engine = None
        
    def connect_databases(self):
        """Connect to both SQLite and PostgreSQL databases"""
        try:
            # Connect to SQLite
            self.sqlite_conn = sqlite3.connect(self.sqlite_path)
            self.sqlite_conn.row_factory = sqlite3.Row
            
            # Connect to PostgreSQL
            self.pg_conn = psycopg2.connect(self.pg_connection_string)
            self.pg_conn.autocommit = False
            
            # Create SQLAlchemy engine for PostgreSQL
            self.pg_engine = create_engine(
                self.pg_connection_string,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True
            )
            
            logger.info("Successfully connected to both databases")
            
        except Exception as e:
            logger.error(f"Failed to connect to databases: {e}")
            raise
    
    def create_postgresql_schema(self):
        """Create optimized PostgreSQL schema with partitioning"""
        
        schema_sql = """
        -- Enable UUID extension
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        
        -- Controllers table
        CREATE TABLE IF NOT EXISTS controllers (
            id SERIAL PRIMARY KEY,
            callsign VARCHAR(50) UNIQUE NOT NULL,
            facility VARCHAR(50) NOT NULL,
            position VARCHAR(50),
            status VARCHAR(20) DEFAULT 'offline',
            frequency VARCHAR(20),
            last_seen TIMESTAMPTZ DEFAULT NOW(),
            workload_score FLOAT DEFAULT 0.0,
            preferences JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Create index on callsign for fast lookups
        CREATE INDEX IF NOT EXISTS idx_controllers_callsign ON controllers(callsign);
        CREATE INDEX IF NOT EXISTS idx_controllers_facility ON controllers(facility);
        CREATE INDEX IF NOT EXISTS idx_controllers_status ON controllers(status);
        
        -- Sectors table
        CREATE TABLE IF NOT EXISTS sectors (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            facility VARCHAR(50) NOT NULL,
            controller_id INTEGER REFERENCES controllers(id),
            traffic_density INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'unmanned',
            priority_level INTEGER DEFAULT 1,
            boundaries JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_sectors_facility ON sectors(facility);
        CREATE INDEX IF NOT EXISTS idx_sectors_controller_id ON sectors(controller_id);
        
        -- Flights table with partitioning
        CREATE TABLE IF NOT EXISTS flights (
            id SERIAL,
            callsign VARCHAR(20) NOT NULL,
            pilot_name VARCHAR(100),
            aircraft_type VARCHAR(10),
            departure VARCHAR(10),
            arrival VARCHAR(10),
            route TEXT,
            altitude SMALLINT,
            speed SMALLINT,
            position_lat INTEGER,
            position_lng INTEGER,
            controller_id INTEGER REFERENCES controllers(id),
            sector_id INTEGER REFERENCES sectors(id),
            last_updated TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (id, last_updated)
        ) PARTITION BY RANGE (last_updated);
        
        -- Create indexes on partitioned table
        CREATE INDEX IF NOT EXISTS idx_flights_callsign ON flights(callsign);
        CREATE INDEX IF NOT EXISTS idx_flights_last_updated ON flights(last_updated);
        CREATE INDEX IF NOT EXISTS idx_flights_controller_id ON flights(controller_id);
        CREATE INDEX IF NOT EXISTS idx_flights_sector_id ON flights(sector_id);
        
        -- Traffic movements table with partitioning
        CREATE TABLE IF NOT EXISTS traffic_movements (
            id SERIAL,
            callsign VARCHAR(20) NOT NULL,
            airport_icao VARCHAR(10) NOT NULL,
            movement_type VARCHAR(10) NOT NULL,
            aircraft_type VARCHAR(10),
            pilot_name VARCHAR(100),
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            confidence_score FLOAT DEFAULT 1.0,
            detection_method VARCHAR(50),
            flight_id INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);
        
        CREATE INDEX IF NOT EXISTS idx_traffic_movements_callsign ON traffic_movements(callsign);
        CREATE INDEX IF NOT EXISTS idx_traffic_movements_airport ON traffic_movements(airport_icao);
        CREATE INDEX IF NOT EXISTS idx_traffic_movements_timestamp ON traffic_movements(timestamp);
        
        -- Flight summaries table
        CREATE TABLE IF NOT EXISTS flight_summaries (
            id SERIAL PRIMARY KEY,
            callsign VARCHAR(20) NOT NULL,
            aircraft_type VARCHAR(10),
            departure VARCHAR(10),
            arrival VARCHAR(10),
            route TEXT,
            max_altitude SMALLINT,
            duration_minutes SMALLINT,
            controller_id INTEGER REFERENCES controllers(id),
            sector_id INTEGER REFERENCES sectors(id),
            completed_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign ON flight_summaries(callsign);
        CREATE INDEX IF NOT EXISTS idx_flight_summaries_completed_at ON flight_summaries(completed_at);
        
        -- Movement summaries table
        CREATE TABLE IF NOT EXISTS movement_summaries (
            id SERIAL PRIMARY KEY,
            airport_icao VARCHAR(10) NOT NULL,
            movement_type VARCHAR(10) NOT NULL,
            aircraft_type VARCHAR(10),
            date DATE NOT NULL,
            hour SMALLINT NOT NULL,
            count SMALLINT DEFAULT 1,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_movement_summaries_airport ON movement_summaries(airport_icao);
        CREATE INDEX IF NOT EXISTS idx_movement_summaries_date ON movement_summaries(date);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_movement_summaries_unique 
            ON movement_summaries(airport_icao, movement_type, date, hour);
        
        -- Airport configuration table
        CREATE TABLE IF NOT EXISTS airport_config (
            id SERIAL PRIMARY KEY,
            icao_code VARCHAR(10) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            detection_radius_nm FLOAT DEFAULT 10.0,
            departure_altitude_threshold INTEGER DEFAULT 1000,
            arrival_altitude_threshold INTEGER DEFAULT 3000,
            departure_speed_threshold INTEGER DEFAULT 50,
            arrival_speed_threshold INTEGER DEFAULT 150,
            is_active BOOLEAN DEFAULT TRUE,
            region VARCHAR(50),
            last_updated TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_airport_config_icao ON airport_config(icao_code);
        CREATE INDEX IF NOT EXISTS idx_airport_config_region ON airport_config(region);
        
        -- Movement detection config table
        CREATE TABLE IF NOT EXISTS movement_detection_config (
            id SERIAL PRIMARY KEY,
            config_key VARCHAR(100) UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            last_updated TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- System configuration table
        CREATE TABLE IF NOT EXISTS system_config (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT,
            last_updated TIMESTAMPTZ DEFAULT NOW(),
            environment VARCHAR(20) DEFAULT 'development',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Events table
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            start_time TIMESTAMPTZ NOT NULL,
            end_time TIMESTAMPTZ NOT NULL,
            expected_traffic INTEGER DEFAULT 0,
            required_controllers INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'scheduled',
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_events_start_time ON events(start_time);
        CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
        
        -- Create monthly partitions for flights table
        """
        
        try:
            with self.pg_conn.cursor() as cursor:
                cursor.execute(schema_sql)
                
                # Create monthly partitions for the next 12 months
                current_date = datetime.now()
                for i in range(12):
                    partition_date = current_date + timedelta(days=30*i)
                    partition_name = f"flights_{partition_date.strftime('%Y_%m')}"
                    start_date = partition_date.replace(day=1)
                    end_date = (start_date + timedelta(days=32)).replace(day=1)
                    
                    partition_sql = f"""
                    CREATE TABLE IF NOT EXISTS {partition_name} 
                    PARTITION OF flights 
                    FOR VALUES FROM ('{start_date.isoformat()}') 
                    TO ('{end_date.isoformat()}');
                    """
                    
                    cursor.execute(partition_sql)
                
                # Create monthly partitions for traffic_movements table
                for i in range(12):
                    partition_date = current_date + timedelta(days=30*i)
                    partition_name = f"traffic_movements_{partition_date.strftime('%Y_%m')}"
                    start_date = partition_date.replace(day=1)
                    end_date = (start_date + timedelta(days=32)).replace(day=1)
                    
                    partition_sql = f"""
                    CREATE TABLE IF NOT EXISTS {partition_name} 
                    PARTITION OF traffic_movements 
                    FOR VALUES FROM ('{start_date.isoformat()}') 
                    TO ('{end_date.isoformat()}');
                    """
                    
                    cursor.execute(partition_sql)
                
                self.pg_conn.commit()
                logger.info("PostgreSQL schema created successfully")
                
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"Failed to create PostgreSQL schema: {e}")
            raise
    
    def migrate_controllers(self):
        """Migrate controllers data from SQLite to PostgreSQL"""
        try:
            # Get controllers from SQLite
            sqlite_cursor = self.sqlite_conn.execute("SELECT * FROM controllers")
            controllers = sqlite_cursor.fetchall()
            
            if not controllers:
                logger.info("No controllers to migrate")
                return
            
            # Insert into PostgreSQL
            with self.pg_conn.cursor() as cursor:
                for controller in controllers:
                    cursor.execute("""
                        INSERT INTO controllers (
                            callsign, facility, position, status, frequency, 
                            last_seen, workload_score, preferences
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (callsign) DO UPDATE SET
                            facility = EXCLUDED.facility,
                            position = EXCLUDED.position,
                            status = EXCLUDED.status,
                            frequency = EXCLUDED.frequency,
                            last_seen = EXCLUDED.last_seen,
                            workload_score = EXCLUDED.workload_score,
                            preferences = EXCLUDED.preferences,
                            updated_at = NOW()
                    """, (
                        controller['callsign'],
                        controller['facility'],
                        controller['position'],
                        controller['status'],
                        controller['frequency'],
                        controller['last_seen'],
                        controller['workload_score'],
                        controller['preferences']
                    ))
            
            self.pg_conn.commit()
            logger.info(f"Migrated {len(controllers)} controllers")
            
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"Failed to migrate controllers: {e}")
            raise
    
    def migrate_sectors(self):
        """Migrate sectors data from SQLite to PostgreSQL"""
        try:
            # Get sectors from SQLite
            sqlite_cursor = self.sqlite_conn.execute("SELECT * FROM sectors")
            sectors = sqlite_cursor.fetchall()
            
            if not sectors:
                logger.info("No sectors to migrate")
                return
            
            # Insert into PostgreSQL
            with self.pg_conn.cursor() as cursor:
                for sector in sectors:
                    cursor.execute("""
                        INSERT INTO sectors (
                            name, facility, controller_id, traffic_density,
                            status, priority_level, boundaries
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            facility = EXCLUDED.facility,
                            controller_id = EXCLUDED.controller_id,
                            traffic_density = EXCLUDED.traffic_density,
                            status = EXCLUDED.status,
                            priority_level = EXCLUDED.priority_level,
                            boundaries = EXCLUDED.boundaries,
                            updated_at = NOW()
                    """, (
                        sector['name'],
                        sector['facility'],
                        sector['controller_id'],
                        sector['traffic_density'],
                        sector['status'],
                        sector['priority_level'],
                        sector['boundaries']
                    ))
            
            self.pg_conn.commit()
            logger.info(f"Migrated {len(sectors)} sectors")
            
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"Failed to migrate sectors: {e}")
            raise
    
    def migrate_flights(self):
        """Migrate flights data from SQLite to PostgreSQL"""
        try:
            # Get flights from SQLite
            sqlite_cursor = self.sqlite_conn.execute("SELECT * FROM flights")
            flights = sqlite_cursor.fetchall()
            
            if not flights:
                logger.info("No flights to migrate")
                return
            
            # Insert into PostgreSQL
            with self.pg_conn.cursor() as cursor:
                for flight in flights:
                    cursor.execute("""
                        INSERT INTO flights (
                            callsign, pilot_name, aircraft_type, departure, arrival,
                            route, altitude, speed, position_lat, position_lng,
                            controller_id, sector_id, last_updated
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        flight['callsign'],
                        flight['pilot_name'],
                        flight['aircraft_type'],
                        flight['departure'],
                        flight['arrival'],
                        flight['route'],
                        flight['altitude'],
                        flight['speed'],
                        flight['position_lat'],
                        flight['position_lng'],
                        flight['controller_id'],
                        flight['sector_id'],
                        flight['last_updated']
                    ))
            
            self.pg_conn.commit()
            logger.info(f"Migrated {len(flights)} flights")
            
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"Failed to migrate flights: {e}")
            raise
    
    def migrate_traffic_movements(self):
        """Migrate traffic movements data from SQLite to PostgreSQL"""
        try:
            # Get traffic movements from SQLite
            sqlite_cursor = self.sqlite_conn.execute("SELECT * FROM traffic_movements")
            movements = sqlite_cursor.fetchall()
            
            if not movements:
                logger.info("No traffic movements to migrate")
                return
            
            # Insert into PostgreSQL
            with self.pg_conn.cursor() as cursor:
                for movement in movements:
                    cursor.execute("""
                        INSERT INTO traffic_movements (
                            callsign, airport_icao, movement_type, aircraft_type,
                            pilot_name, timestamp, confidence_score, detection_method, flight_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        movement['callsign'],
                        movement['airport_icao'],
                        movement['movement_type'],
                        movement['aircraft_type'],
                        movement['pilot_name'],
                        movement['timestamp'],
                        movement['confidence_score'],
                        movement['detection_method'],
                        movement['flight_id']
                    ))
            
            self.pg_conn.commit()
            logger.info(f"Migrated {len(movements)} traffic movements")
            
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"Failed to migrate traffic movements: {e}")
            raise
    
    def migrate_other_tables(self):
        """Migrate other tables (flight_summaries, movement_summaries, etc.)"""
        tables = [
            'flight_summaries',
            'movement_summaries', 
            'airport_config',
            'movement_detection_config',
            'system_config',
            'events'
        ]
        
        for table in tables:
            try:
                # Check if table exists in SQLite
                sqlite_cursor = self.sqlite_conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not sqlite_cursor.fetchone():
                    logger.info(f"Table {table} does not exist in SQLite, skipping")
                    continue
                
                # Get data from SQLite
                sqlite_cursor = self.sqlite_conn.execute(f"SELECT * FROM {table}")
                rows = sqlite_cursor.fetchall()
                
                if not rows:
                    logger.info(f"No data in {table} to migrate")
                    continue
                
                # Get column names
                columns = [description[0] for description in sqlite_cursor.description]
                
                # Insert into PostgreSQL
                with self.pg_conn.cursor() as cursor:
                    for row in rows:
                        # Create placeholders for SQL
                        placeholders = ', '.join(['%s'] * len(columns))
                        column_names = ', '.join(columns)
                        
                        # Create values tuple
                        values = tuple(row[column] for column in columns)
                        
                        cursor.execute(f"""
                            INSERT INTO {table} ({column_names})
                            VALUES ({placeholders})
                        """, values)
                
                self.pg_conn.commit()
                logger.info(f"Migrated {len(rows)} rows from {table}")
                
            except Exception as e:
                self.pg_conn.rollback()
                logger.error(f"Failed to migrate {table}: {e}")
                continue
    
    def verify_migration(self):
        """Verify that migration was successful"""
        try:
            # Check record counts
            tables = ['controllers', 'sectors', 'flights', 'traffic_movements']
            
            for table in tables:
                # Count in SQLite
                sqlite_cursor = self.sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                # Count in PostgreSQL
                with self.pg_conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    pg_count = cursor.fetchone()[0]
                
                logger.info(f"{table}: SQLite={sqlite_count}, PostgreSQL={pg_count}")
                
                if sqlite_count != pg_count:
                    logger.warning(f"Count mismatch for {table}: SQLite={sqlite_count}, PostgreSQL={pg_count}")
            
            logger.info("Migration verification completed")
            
        except Exception as e:
            logger.error(f"Failed to verify migration: {e}")
            raise
    
    def close_connections(self):
        """Close database connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.pg_conn:
            self.pg_conn.close()
        if self.pg_engine:
            self.pg_engine.dispose()
    
    def run_migration(self):
        """Run the complete migration process"""
        try:
            logger.info("Starting PostgreSQL migration...")
            
            # Connect to databases
            self.connect_databases()
            
            # Create PostgreSQL schema
            self.create_postgresql_schema()
            
            # Migrate data
            self.migrate_controllers()
            self.migrate_sectors()
            self.migrate_flights()
            self.migrate_traffic_movements()
            self.migrate_other_tables()
            
            # Verify migration
            self.verify_migration()
            
            logger.info("PostgreSQL migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            self.close_connections()

def main():
    """Main migration function"""
    
    # Configuration
    sqlite_path = "atc_optimization.db"
    pg_connection_string = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:password@localhost:5432/vatsim_data"
    )
    
    # Check if SQLite database exists
    if not os.path.exists(sqlite_path):
        logger.error(f"SQLite database not found: {sqlite_path}")
        sys.exit(1)
    
    # Create migrator and run migration
    migrator = PostgreSQLMigrator(sqlite_path, pg_connection_string)
    migrator.run_migration()

if __name__ == "__main__":
    main() 