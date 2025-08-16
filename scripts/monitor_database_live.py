#!/usr/bin/env python3
"""
Database Live Monitoring Tool

This script provides real-time monitoring of data entering the VATSIM database.
It shows live counts, recent records, and data flow statistics to help verify
if the system is working properly.

Usage:
    python scripts/monitor_database_live.py
    python scripts/monitor_database_live.py --table flights
    python scripts/monitor_database_live.py --interval 10
"""

import asyncio
import argparse
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Add the app directory to the path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from config import get_database_url
except ImportError:
    # Fallback if config import fails
    def get_database_url():
        return "postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"

class DatabaseMonitor:
    def __init__(self, database_url: str, interval: int = 30):
        self.database_url = database_url
        self.interval = interval
        self.connection = None
        self.previous_counts = {}
        self.start_time = datetime.now()
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(self.database_url)
            self.connection.autocommit = True
            print(f"✅ Connected to database successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("🔌 Database connection closed")
    
    def get_table_counts(self) -> Dict[str, int]:
        """Get current record counts for all tables"""
        counts = {}
        try:
            with self.connection.cursor() as cursor:
                # Get all table names
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get counts for each table
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    counts[table] = count
                    
        except Exception as e:
            print(f"❌ Error getting table counts: {e}")
            
        return counts
    
    def get_recent_records(self, table: str, limit: int = 5) -> List[Dict]:
        """Get recent records from a specific table"""
        records = []
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Determine timestamp column based on table
                if table == 'flights':
                    timestamp_col = 'last_updated_api'
                elif table == 'controllers':
                    timestamp_col = 'last_updated'
                elif table == 'transceivers':
                    timestamp_col = 'last_updated'
                elif table == 'flight_sector_occupancy':
                    timestamp_col = 'entry_timestamp'
                else:
                    timestamp_col = 'created_at'
                
                # Get recent records
                query = f"""
                    SELECT * FROM {table} 
                    ORDER BY {timestamp_col} DESC 
                    LIMIT {limit}
                """
                cursor.execute(query)
                records = [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"❌ Error getting recent records from {table}: {e}")
            
        return records
    
    def get_data_flow_stats(self, table: str) -> Dict:
        """Get data flow statistics for a table"""
        stats = {}
        try:
            with self.connection.cursor() as cursor:
                # Determine timestamp column
                if table == 'flights':
                    timestamp_col = 'last_updated_api'
                elif table == 'controllers':
                    timestamp_col = 'last_updated'
                elif table == 'transceivers':
                    timestamp_col = 'last_updated'
                elif table == 'flight_sector_occupancy':
                    timestamp_col = 'entry_timestamp'
                else:
                    timestamp_col = 'created_at'
                
                # Get records in last hour
                one_hour_ago = datetime.now() - timedelta(hours=1)
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {timestamp_col} >= %s
                """, (one_hour_ago,))
                last_hour = cursor.fetchone()[0]
                
                # Get records in last 10 minutes
                ten_mins_ago = datetime.now() - timedelta(minutes=10)
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {timestamp_col} >= %s
                """, (ten_mins_ago,))
                last_10_mins = cursor.fetchone()[0]
                
                # Get records in last minute
                one_min_ago = datetime.now() - timedelta(minutes=1)
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {timestamp_col} >= %s
                """, (one_min_ago,))
                last_minute = cursor.fetchone()[0]
                
                stats = {
                    'last_hour': last_hour,
                    'last_10_mins': last_10_mins,
                    'last_minute': last_minute
                }
                
        except Exception as e:
            print(f"❌ Error getting flow stats for {table}: {e}")
            
        return stats
    
    def get_sector_tracking_stats(self) -> Dict:
        """Get sector tracking specific statistics"""
        stats = {}
        try:
            with self.connection.cursor() as cursor:
                # Count open sectors (no exit timestamp)
                cursor.execute("""
                    SELECT COUNT(*) FROM flight_sector_occupancy 
                    WHERE exit_timestamp IS NULL
                """)
                open_sectors = cursor.fetchone()[0]
                
                # Count closed sectors
                cursor.execute("""
                    SELECT COUNT(*) FROM flight_sector_occupancy 
                    WHERE exit_timestamp IS NOT NULL
                """)
                closed_sectors = cursor.fetchone()[0]
                
                # Count sectors in last hour
                one_hour_ago = datetime.now() - timedelta(hours=1)
                cursor.execute("""
                    SELECT COUNT(*) FROM flight_sector_occupancy 
                    WHERE entry_timestamp >= %s
                """, (one_hour_ago,))
                sectors_last_hour = cursor.fetchone()[0]
                
                stats = {
                    'open_sectors': open_sectors,
                    'closed_sectors': closed_sectors,
                    'sectors_last_hour': sectors_last_hour
                }
                
        except Exception as e:
            print(f"❌ Error getting sector stats: {e}")
            
        return stats
    
    def display_header(self):
        """Display monitoring header"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 80)
        print("🗄️  VATSIM Database Live Monitor")
        print("=" * 80)
        print(f"📅 Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Update Interval: {self.interval} seconds")
        print(f"🕐 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()
    
    def display_table_counts(self, counts: Dict[str, int]):
        """Display current table counts with changes"""
        print("📊 TABLE RECORD COUNTS")
        print("-" * 50)
        
        for table, count in sorted(counts.items()):
            change = ""
            if table in self.previous_counts:
                diff = count - self.previous_counts[table]
                if diff > 0:
                    change = f" (+{diff})"
                elif diff < 0:
                    change = f" ({diff})"
                else:
                    change = " (no change)"
            
            print(f"{table:25} {count:8,} records{change}")
        
        print()
    
    def display_data_flow(self, counts: Dict[str, int]):
        """Display data flow statistics"""
        print("🌊 DATA FLOW STATISTICS (Last Hour/10min/1min)")
        print("-" * 60)
        
        for table in ['flights', 'controllers', 'transceivers', 'flight_sector_occupancy']:
            if table in counts:
                stats = self.get_data_flow_stats(table)
                if stats:
                    print(f"{table:25} {stats['last_hour']:4} / {stats['last_10_mins']:4} / {stats['last_minute']:4}")
        
        print()
    
    def display_sector_stats(self):
        """Display sector tracking statistics"""
        print("🚁 SECTOR TRACKING STATISTICS")
        print("-" * 40)
        
        stats = self.get_sector_tracking_stats()
        if stats:
            print(f"Open Sectors:           {stats['open_sectors']:4}")
            print(f"Closed Sectors:         {stats['closed_sectors']:4}")
            print(f"Sectors (Last Hour):    {stats['sectors_last_hour']:4}")
        
        print()
    
    def display_recent_sample(self, table: str):
        """Display sample of recent records from a table"""
        print(f"📝 RECENT {table.upper()} RECORDS (Last 3)")
        print("-" * 50)
        
        records = self.get_recent_records(table, 3)
        if records:
            for i, record in enumerate(records, 1):
                print(f"Record {i}:")
                # Show key fields based on table type
                if table == 'flights':
                    callsign = record.get('callsign', 'N/A')
                    lat = record.get('latitude', 'N/A')
                    lon = record.get('longitude', 'N/A')
                    alt = record.get('altitude', 'N/A')
                    updated = record.get('last_updated_api', 'N/A')
                    print(f"  Callsign: {callsign}, Position: {lat}, {lon}, Alt: {alt}")
                    print(f"  Updated: {updated}")
                elif table == 'controllers':
                    name = record.get('name', 'N/A')
                    facility = record.get('facility', 'N/A')
                    rating = record.get('rating', 'N/A')
                    updated = record.get('last_updated', 'N/A')
                    print(f"  Name: {name}, Facility: {facility}, Rating: {rating}")
                    print(f"  Updated: {updated}")
                elif table == 'flight_sector_occupancy':
                    callsign = record.get('callsign', 'N/A')
                    sector = record.get('sector_name', 'N/A')
                    entry = record.get('entry_timestamp', 'N/A')
                    exit_time = record.get('exit_timestamp', 'N/A')
                    print(f"  Callsign: {callsign}, Sector: {sector}")
                    print(f"  Entry: {entry}, Exit: {exit_time if exit_time else 'OPEN'}")
                else:
                    # Show first few fields for other tables
                    fields = list(record.items())[:4]
                    for key, value in fields:
                        print(f"  {key}: {value}")
                print()
        else:
            print("No recent records found")
        print()
    
    def display_status_summary(self, counts: Dict[str, int]):
        """Display overall system status summary"""
        print("📈 SYSTEM STATUS SUMMARY")
        print("-" * 40)
        
        # Check if data is flowing
        total_records = sum(counts.values())
        if total_records > 0:
            print("✅ Database has data")
            
            # Check if flights table is growing
            if 'flights' in counts and 'flights' in self.previous_counts:
                flight_diff = counts['flights'] - self.previous_counts['flights']
                if flight_diff > 0:
                    print("✅ Flight data is being added")
                elif flight_diff == 0:
                    print("⚠️  Flight data count unchanged")
                else:
                    print("❌ Flight data count decreased")
            
            # Check sector tracking
            if 'flight_sector_occupancy' in counts:
                sector_stats = self.get_sector_tracking_stats()
                if sector_stats and sector_stats['sectors_last_hour'] > 0:
                    print("✅ Sector tracking is active")
                else:
                    print("⚠️  No recent sector activity")
        else:
            print("❌ Database appears empty")
        
        print()
    
    def run_monitoring(self, focus_table: Optional[str] = None):
        """Run the main monitoring loop"""
        if not self.connect():
            return
        
        try:
            while True:
                # Get current data
                counts = self.get_table_counts()
                
                # Display information
                self.display_header()
                self.display_table_counts(counts)
                self.display_data_flow(counts)
                self.display_sector_stats()
                self.display_status_summary(counts)
                
                # Show detailed sample if focusing on a table
                if focus_table and focus_table in counts:
                    self.display_recent_sample(focus_table)
                
                # Update previous counts for next iteration
                self.previous_counts = counts.copy()
                
                # Wait for next update
                print(f"⏳ Next update in {self.interval} seconds... (Press Ctrl+C to stop)")
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
        finally:
            self.disconnect()

def main():
    parser = argparse.ArgumentParser(description='Monitor VATSIM database in real-time')
    parser.add_argument('--table', help='Focus on specific table for detailed view')
    parser.add_argument('--interval', type=int, default=30, help='Update interval in seconds (default: 30)')
    parser.add_argument('--database-url', help='Custom database URL')
    
    args = parser.parse_args()
    
    # Get database URL
    if args.database_url:
        database_url = args.database_url
    else:
        try:
            database_url = get_database_url()
        except:
            database_url = "postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
    
    print(f"🔗 Using database: {database_url}")
    
    # Create and run monitor
    monitor = DatabaseMonitor(database_url, args.interval)
    monitor.run_monitoring(args.table)

if __name__ == "__main__":
    main()
