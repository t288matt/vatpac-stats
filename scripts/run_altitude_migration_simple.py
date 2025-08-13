#!/usr/bin/env python3
"""
Simple Migration Script: Add altitude fields to flight_sector_occupancy table

This script adds entry_altitude and exit_altitude fields to track
flight altitudes when entering and exiting sectors.

Prerequisites:
1. Docker Desktop must be running
2. Run: docker-compose up -d postgres
3. Then run this script

Usage:
python scripts/run_altitude_migration_simple.py
"""

import subprocess
import sys
import time

def run_migration():
    """Run the altitude fields migration using Docker"""
    print("🚀 Starting altitude fields migration...")
    
    # Check if Docker is running
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker is not running. Please start Docker Desktop first.")
            return False
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker Desktop.")
        return False
    
    # Check if postgres container is running
    try:
        result = subprocess.run(['docker-compose', 'ps', 'postgres'], capture_output=True, text=True)
        if 'Up' not in result.stdout:
            print("📦 Starting PostgreSQL container...")
            subprocess.run(['docker-compose', 'up', '-d', 'postgres'], check=True)
            print("⏳ Waiting for PostgreSQL to start...")
            time.sleep(10)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start PostgreSQL: {e}")
        return False
    
    # Copy migration file to container
    print("📋 Copying migration file to container...")
    try:
        subprocess.run([
            'docker', 'cp', 
            'scripts/add_altitude_fields_migration.sql',
            'vatsimdata_postgres_1:/tmp/add_altitude_fields_migration.sql'
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to copy migration file: {e}")
        return False
    
    # Run the migration
    print("🔧 Executing migration...")
    try:
        result = subprocess.run([
            'docker-compose', 'exec', '-T', 'postgres',
            'psql', '-U', 'postgres', '-d', 'vatsim_data',
            '-f', '/tmp/add_altitude_fields_migration.sql'
        ], capture_output=True, text=True, check=True)
        
        print("✅ Migration completed successfully!")
        print("\nMigration output:")
        print(result.stdout)
        
        if result.stderr:
            print("\nWarnings/Info:")
            print(result.stderr)
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\n🎉 Altitude fields added successfully!")
        print("New fields: entry_altitude, exit_altitude")
    else:
        print("\n💥 Migration failed. Check the errors above.")
        sys.exit(1)
