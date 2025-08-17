#!/usr/bin/env python3
"""
Simple Controller Stats Materialized View Refresh Script

This script refreshes the controller_weekly_stats materialized view
using direct database connection from the host machine.

Usage:
    python scripts/refresh_controller_stats_simple.py
"""

import subprocess
import sys
from pathlib import Path


def run_sql_command(sql_command: str) -> str:
    """Run a SQL command using docker exec and psql"""
    try:
        result = subprocess.run([
            'docker', 'exec', 'vatsim_postgres', 'psql', 
            '-U', 'vatsim_user', '-d', 'vatsim_data', '-t', '-c', sql_command
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Database error: {e}")
        print(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def main():
    """Main function"""
    print("🚀 Simple Controller Stats Materialized View Refresh Tool")
    print("=" * 60)
    
    # Step 1: Refresh the materialized view
    print("📊 Refreshing materialized view...")
    result = run_sql_command("SELECT refresh_controller_stats();")
    
    if result is None:
        print("💥 Refresh failed!")
        sys.exit(1)
    
    print("✅ Refresh completed successfully!")
    
    # Step 2: Show current view status
    print("\n📈 Current View Status:")
    print("-" * 30)
    
    # Count rows in the view
    row_count_result = run_sql_command("SELECT COUNT(*) FROM controller_weekly_stats;")
    if row_count_result:
        try:
            row_count = int(row_count_result)
            print(f"Total controller records: {row_count}")
            
            # Show sample data if available
            if row_count > 0:
                print("\n📋 Sample Data:")
                print("-" * 20)
                sample_data = run_sql_command("""
                    SELECT controller_callsign, unique_flights_handled, total_interactions, last_flight_time
                    FROM controller_weekly_stats 
                    ORDER BY unique_flights_handled DESC 
                    LIMIT 5;
                """)
                if sample_data:
                    print(sample_data)
            else:
                print("  No data in view yet (flight_summaries table may be empty)")
        except ValueError:
            print(f"  Could not parse row count: {row_count_result}")
    
    # Step 3: Show when view was last updated
    from datetime import datetime
    print(f"\n🕒 View last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n🎉 Refresh completed successfully!")
    print("\n💡 Next steps:")
    print("  - The view is now ready for fast queries")
    print("  - Run this script periodically to keep data fresh")
    print("  - Use the optimized query with LEFT JOIN to controller_weekly_stats")


if __name__ == "__main__":
    main()
