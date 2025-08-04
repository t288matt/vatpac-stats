#!/usr/bin/env python3
"""
Migrate from SQLite to PostgreSQL
================================

This script migrates the VATSIM data collection system from SQLite to PostgreSQL.
It creates the new airports table and migrates all data to PostgreSQL.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.config import get_config
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import pandas as pd


def create_postgresql_airports_table():
    """Create the airports table in PostgreSQL"""
    try:
        # Connect to PostgreSQL
        postgres_url = "postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
        postgres_engine = create_engine(postgres_url)
        
        # Create airports table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS airports (
            id SERIAL PRIMARY KEY,
            icao_code VARCHAR(10) UNIQUE NOT NULL,
            name VARCHAR(200),
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            elevation INTEGER,
            country VARCHAR(100),
            region VARCHAR(100),
            timezone VARCHAR(50),
            facility_type VARCHAR(50),
            runways TEXT,
            frequencies TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_airports_icao_code ON airports(icao_code);
        CREATE INDEX IF NOT EXISTS idx_airports_country ON airports(country);
        CREATE INDEX IF NOT EXISTS idx_airports_region ON airports(region);
        """
        
        with postgres_engine.begin() as conn:
            conn.execute(text(create_table_sql))
        
        print("✅ Created airports table in PostgreSQL")
        
        # Create the Australian airports view
        create_views_sql = """
        -- Drop existing views if they exist
        DROP VIEW IF EXISTS australian_airports CASCADE;
        DROP VIEW IF EXISTS australian_flights CASCADE;
        
        -- Create Australian airports view
        CREATE VIEW australian_airports AS
        SELECT 
            icao_code,
            name,
            latitude,
            longitude,
            country,
            region
        FROM airports 
        WHERE icao_code LIKE 'Y%' AND is_active = true;
        
        -- Create Australian flights view
        CREATE VIEW australian_flights AS
        SELECT 
            f.*,
            CASE 
                WHEN f.departure IN (SELECT icao_code FROM australian_airports) 
                     AND f.arrival NOT IN (SELECT icao_code FROM australian_airports) 
                THEN 'International Outbound'
                WHEN f.arrival IN (SELECT icao_code FROM australian_airports) 
                     AND f.departure NOT IN (SELECT icao_code FROM australian_airports) 
                THEN 'International Inbound'
                WHEN f.departure IN (SELECT icao_code FROM australian_airports) 
                     AND f.arrival IN (SELECT icao_code FROM australian_airports) 
                THEN 'Domestic'
                ELSE 'Other'
            END as route_type
        FROM flights f
        WHERE f.departure IN (SELECT icao_code FROM australian_airports)
           OR f.arrival IN (SELECT icao_code FROM australian_airports);
        """
        
        with postgres_engine.begin() as conn:
            conn.execute(text(create_views_sql))
        
        print("✅ Created Australian airports and flights views in PostgreSQL")
        
        return postgres_engine
        
    except Exception as e:
        print(f"❌ Error creating PostgreSQL tables: {e}")
        raise


def migrate_airports_data():
    """Migrate airports data from SQLite to PostgreSQL"""
    try:
        # Connect to SQLite
        sqlite_url = "sqlite:///atc_optimization.db"
        sqlite_engine = create_engine(sqlite_url)
        
        # Connect to PostgreSQL
        postgres_url = "postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
        postgres_engine = create_engine(postgres_url)
        
        # Read airports data from SQLite
        with sqlite_engine.connect() as conn:
            airports_df = pd.read_sql("SELECT * FROM airports", conn)
        
        print(f"📊 Found {len(airports_df)} airports in SQLite")
        
        # Convert SQLite integer booleans to PostgreSQL boolean values
        if 'is_active' in airports_df.columns:
            airports_df['is_active'] = airports_df['is_active'].astype(bool)
        
        # Clear existing airports in PostgreSQL
        with postgres_engine.begin() as conn:
            conn.execute(text("DELETE FROM airports"))
        
        # Insert airports into PostgreSQL
        airports_df.to_sql('airports', postgres_engine, if_exists='append', index=False)
        
        print(f"✅ Migrated {len(airports_df)} airports to PostgreSQL")
        
        # Verify the migration
        with postgres_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM airports"))
            count = result.scalar()
            print(f"✅ PostgreSQL now contains {count} airports")
            
            # Check Australian airports
            result = conn.execute(text("SELECT COUNT(*) FROM australian_airports"))
            australian_count = result.scalar()
            print(f"✅ Australian airports view contains {australian_count} airports")
        
    except Exception as e:
        print(f"❌ Error migrating airports data: {e}")
        raise


def update_application_config():
    """Update the application to use PostgreSQL"""
    try:
        # Set environment variable for PostgreSQL
        os.environ['DATABASE_URL'] = "postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
        
        print("✅ Updated DATABASE_URL to use PostgreSQL")
        
        # Test the new configuration
        config = get_config()
        print(f"✅ Application now configured to use: {config.database.url}")
        
    except Exception as e:
        print(f"❌ Error updating application config: {e}")
        raise


def test_postgresql_connection():
    """Test the PostgreSQL connection and data"""
    try:
        # Test connection
        postgres_url = "postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
        engine = create_engine(postgres_url)
        
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT COUNT(*) FROM airports"))
            airports_count = result.scalar()
            print(f"✅ PostgreSQL connection test: {airports_count} airports found")
            
            # Test Australian airports view
            result = conn.execute(text("SELECT COUNT(*) FROM australian_airports"))
            australian_count = result.scalar()
            print(f"✅ Australian airports view test: {australian_count} airports found")
            
            # Test sample data
            result = conn.execute(text("SELECT icao_code, name, country FROM australian_airports LIMIT 3"))
            sample_airports = result.fetchall()
            print("✅ Sample Australian airports:")
            for airport in sample_airports:
                print(f"  - {airport[0]}: {airport[1]} ({airport[2]})")
        
    except Exception as e:
        print(f"❌ Error testing PostgreSQL connection: {e}")
        raise


def main():
    """Main migration function"""
    print("🚀 Starting migration from SQLite to PostgreSQL...")
    
    try:
        # Step 1: Create PostgreSQL tables and views
        print("\n📋 Step 1: Creating PostgreSQL tables and views...")
        create_postgresql_airports_table()
        
        # Step 2: Migrate airports data
        print("\n📋 Step 2: Migrating airports data...")
        migrate_airports_data()
        
        # Step 3: Update application configuration
        print("\n📋 Step 3: Updating application configuration...")
        update_application_config()
        
        # Step 4: Test the migration
        print("\n📋 Step 4: Testing PostgreSQL connection...")
        test_postgresql_connection()
        
        print("\n🎉 Migration completed successfully!")
        print("\n📝 Next steps:")
        print("1. Restart your application to use PostgreSQL")
        print("2. Update Grafana datasource if needed")
        print("3. Test Grafana dashboards with PostgreSQL data")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    main() 