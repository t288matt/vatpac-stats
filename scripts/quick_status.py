#!/usr/bin/env python3
"""
Quick Database Status Check
Simple script to show current database status without interactive waiting
"""

import psycopg2
from datetime import datetime, timedelta

def get_database_status():
    """Get current database status"""
    try:
        # Connect to database
        conn = psycopg2.connect('postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data')
        cur = conn.cursor()
        
        print("🗄️  VATSIM Database Status")
        print("=" * 50)
        print(f"📅 Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print()
        
        # Get table counts
        print("📊 TABLE RECORD COUNTS")
        print("-" * 30)
        
        # Flights
        cur.execute("SELECT COUNT(*) FROM flights")
        total_flights = cur.fetchone()[0]
        print(f"Flights:           {total_flights:6,}")
        
        # Controllers
        cur.execute("SELECT COUNT(*) FROM controllers")
        total_controllers = cur.fetchone()[0]
        print(f"Controllers:       {total_controllers:6,}")
        
        # Transceivers
        cur.execute("SELECT COUNT(*) FROM transceivers")
        total_transceivers = cur.fetchone()[0]
        print(f"Transceivers:      {total_transceivers:6,}")
        
        # Sector entries
        cur.execute("SELECT COUNT(*) FROM flight_sector_occupancy")
        total_sectors = cur.fetchone()[0]
        print(f"Sector Entries:    {total_sectors:6,}")
        
        print()
        
        # Get recent activity
        print("🌊 RECENT ACTIVITY (Last 10 minutes)")
        print("-" * 40)
        
        # Recent flights
        cur.execute("SELECT COUNT(*) FROM flights WHERE last_updated_api >= NOW() - INTERVAL '10 minutes'")
        recent_flights = cur.fetchone()[0]
        print(f"Flights updated:   {recent_flights:6,}")
        
        # Recent sectors
        cur.execute("SELECT COUNT(*) FROM flight_sector_occupancy WHERE entry_timestamp >= NOW() - INTERVAL '10 minutes'")
        recent_sectors = cur.fetchone()[0]
        print(f"Sector entries:    {recent_sectors:6,}")
        
        print()
        
        # Get sector status
        print("🚁 SECTOR TRACKING STATUS")
        print("-" * 30)
        
        # Open sectors
        cur.execute("SELECT COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NULL")
        open_sectors = cur.fetchone()[0]
        print(f"Open sectors:      {open_sectors:6,}")
        
        # Closed sectors
        cur.execute("SELECT COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL")
        closed_sectors = cur.fetchone()[0]
        print(f"Closed sectors:    {closed_sectors:6,}")
        
        print()
        
        # Get last update times
        print("🕐 LAST UPDATE TIMES")
        print("-" * 25)
        
        # Last flight update
        cur.execute("SELECT MAX(last_updated_api) FROM flights")
        last_flight = cur.fetchone()[0]
        if last_flight:
            minutes_ago = int((datetime.now() - last_flight.replace(tzinfo=None)).total_seconds() / 60)
            print(f"Flights:           {minutes_ago:2} minutes ago")
        
        # Last sector entry
        cur.execute("SELECT MAX(entry_timestamp) FROM flight_sector_occupancy")
        last_sector = cur.fetchone()[0]
        if last_sector:
            minutes_ago = int((datetime.now() - last_sector.replace(tzinfo=None)).total_seconds() / 60)
            print(f"Sector entries:    {minutes_ago:2} minutes ago")
        
        print()
        
        # System health summary
        print("📈 SYSTEM HEALTH SUMMARY")
        print("-" * 30)
        
        if recent_flights > 0:
            print("✅ Flight data is being updated")
        else:
            print("❌ No recent flight updates")
            
        if recent_sectors > 0:
            print("✅ Sector tracking is active")
        else:
            print("⚠️  No recent sector activity")
            
        if open_sectors > 0:
            print("✅ Sectors are being tracked")
        else:
            print("⚠️  No open sectors")
        
        print()
        
        # Show sample of recent flights
        print("📝 RECENT FLIGHTS SAMPLE (Last 3)")
        print("-" * 40)
        
        cur.execute("""
            SELECT callsign, latitude, longitude, altitude, last_updated_api
            FROM flights 
            WHERE last_updated_api >= NOW() - INTERVAL '10 minutes'
            ORDER BY last_updated_api DESC 
            LIMIT 3
        """)
        
        recent_flight_data = cur.fetchall()
        if recent_flight_data:
            for i, (callsign, lat, lon, alt, updated) in enumerate(recent_flight_data, 1):
                minutes_ago = int((datetime.now() - updated.replace(tzinfo=None)).total_seconds() / 60)
                print(f"{i}. {callsign:8} | {lat:7.4f}, {lon:7.4f} | Alt: {alt:5} | {minutes_ago:2}m ago")
        else:
            print("No recent flights found")
        
        print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")

if __name__ == "__main__":
    get_database_status()
