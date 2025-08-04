#!/usr/bin/env python3
"""
Create Airports Table
=====================

This script creates the airports table in the database.
Run this before populating the airports table.

Usage:
    python tools/create_airports_table.py
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.models import Airports, Base
from app.config import get_config
from sqlalchemy import create_engine


def create_airports_table():
    """Create the airports table in the database"""
    try:
        config = get_config()
        engine = create_engine(config.database.url)
        
        # Create the airports table
        Base.metadata.create_all(engine, tables=[Airports.__table__])
        
        print("Successfully created airports table")
        
    except Exception as e:
        print(f"Error creating airports table: {e}")
        raise


def main():
    """Main function to create airports table"""
    print("Creating airports table...")
    create_airports_table()
    print("Airports table creation completed!")


if __name__ == "__main__":
    main() 