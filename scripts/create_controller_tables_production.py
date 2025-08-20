#!/usr/bin/env python3
"""
Script to create controller_summaries and controllers_archive tables in production
This script executes the SQL creation script using Docker Compose
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, check=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e}")
        return e

def check_docker():
    """Check if Docker is running"""
    print("🔍 Checking Docker status...")
    result = run_command("docker info", check=False)
    if result.returncode != 0:
        print("❌ Error: Docker is not running. Please start Docker Desktop first.")
        return False
    print("✅ Docker is running")
    return True

def check_files():
    """Check if required files exist"""
    print("🔍 Checking required files...")
    
    if not Path("docker-compose.yml").exists():
        print("❌ Error: docker-compose.yml not found. Please run this script from the project root directory.")
        return False
    
    sql_script = Path("scripts/create_production_controller_tables.sql")
    if not sql_script.exists():
        print("❌ Error: SQL script not found at scripts/create_production_controller_tables.sql")
        return False
    
    print("✅ Required files found")
    return True

def create_tables():
    """Create the controller tables"""
    print("🚀 Creating controller tables in production database...")
    
    # Copy the SQL script to the postgres container
    print("📋 Copying SQL script to postgres container...")
    copy_result = run_command("docker cp scripts/create_production_controller_tables.sql vatsim_postgres:/tmp/")
    
    if copy_result.returncode != 0:
        print("❌ Error: Failed to copy SQL script to container")
        print(f"Error output: {copy_result.stderr}")
        return False
    
    print("✅ SQL script copied successfully")
    
    # Execute the SQL script
    print("⚡ Executing SQL script...")
    sql_result = run_command("docker-compose exec -T postgres psql -U vatsim_user -d vatsim_data -f /tmp/create_production_controller_tables.sql")
    
    if sql_result.returncode != 0:
        print("❌ Error: Failed to create controller tables")
        print(f"Error output: {sql_result.stderr}")
        return False
    
    print("✅ Successfully created controller tables!")
    print("")
    print("📊 Tables created:")
    print("  - controller_summaries")
    print("  - controllers_archive")
    print("")
    print("🔧 Indexes and triggers have also been created for optimal performance.")
    
    return True

def main():
    """Main function"""
    print("🚁 VATSIM Data Collection System - Controller Tables Creation")
    print("=" * 60)
    
    # Check prerequisites
    if not check_docker():
        sys.exit(1)
    
    if not check_files():
        sys.exit(1)
    
    # Create tables
    if not create_tables():
        sys.exit(1)
    
    print("")
    print("🔍 Verification: You can now check the tables exist by running:")
    print("  docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c \"\\dt controller*\"")
    print("")
    print("✅ Script execution completed successfully!")

if __name__ == "__main__":
    main()
