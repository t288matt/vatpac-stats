#!/usr/bin/env python3
"""
Check for specific columns in the flight_summaries table
"""

import sys
import psycopg2
import os

def check_columns():
    """Check if total_controller_time_minutes and interactions_detected exist in flight_summaries table"""
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "postgres"),
            database=os.environ.get("DB_NAME", "vatsim_data"),
            user=os.environ.get("DB_USER", "vatsim_user"),
            password=os.environ.get("DB_PASSWORD", "vatsim_password")
        )
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Query the information_schema for columns
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'flight_summaries' 
            AND column_name IN ('total_controller_time_minutes', 'interactions_detected')
            ORDER BY column_name
        """)
        
        # Fetch the results
        columns = cursor.fetchall()
        
        if not columns:
            print("The columns 'total_controller_time_minutes' and 'interactions_detected' DO NOT exist in flight_summaries table")
        else:
            print("Found columns in flight_summaries table:")
            for column in columns:
                print(f"  {column[0]}: {column[1]}")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error checking columns: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(check_columns())

