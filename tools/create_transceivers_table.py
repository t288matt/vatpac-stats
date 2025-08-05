#!/usr/bin/env python3
"""
Create transceivers table in the database
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from database import engine, Base
from models import Transceiver

def create_transceivers_table():
    """Create the transceivers table"""
    try:
        print("Creating transceivers table...")
        Base.metadata.create_all(bind=engine, tables=[Transceiver.__table__])
        print("Transceivers table created successfully!")
        return True
    except Exception as e:
        print(f"Error creating transceivers table: {e}")
        return False

if __name__ == "__main__":
    create_transceivers_table() 