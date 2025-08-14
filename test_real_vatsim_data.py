#!/usr/bin/env python3
"""
Test Script: Real VATSIM Data with Sector Tracking

This script fetches real VATSIM data and processes it through the sector tracking
system to demonstrate real-world functionality.

Run with: python test_real_vatsim_data.py
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_real_vatsim_data():
    """Test sector tracking with real VATSIM data"""
    print("🚀 Testing Sector Tracking with Real VATSIM Data\n")
    
    try:
        from app.services.vatsim_service import VATSIMService
        from app.utils.sector_loader import SectorLoader
        
        # Initialize sector loader
        print("📂 Initializing Sector Loader...")
        sector_loader = SectorLoader()
        if not sector_loader.load_sectors():
            print("❌ Failed to load sectors")
            return False
        
        print(f"✅ Sector loader ready: {sector_loader.get_sector_count()} sectors loaded")
        
        # Initialize VATSIM service
        print("\n🌐 Initializing VATSIM Service...")
        vatsim_service = VATSIMService()
        await vatsim_service.initialize()
        
        # Fetch current VATSIM data
        print("📡 Fetching current VATSIM data...")
        vatsim_data = await vatsim_service.get_current_data()
        
        if not vatsim_data:
            print("❌ No VATSIM data received")
            return False
        
        # Extract flights data
        flights = vatsim_data.get("flights", [])
        controllers = vatsim_data.get("controllers", [])
        
        print(f"📊 VATSIM Data Received:")
        print(f"  Flights: {len(flights)}")
        print(f"  Controllers: {len(controllers)}")
        
        if not flights:
            print("⚠️  No flights in current VATSIM data")
            return False
        
        # Process flights for sector tracking
        print(f"\n✈️  Processing {len(flights)} flights for sector tracking...")
        
        flights_in_sectors = 0
        flights_outside_sectors = 0
        sector_distribution = {}
        
        for flight in flights:
            try:
                # Extract flight position data
                callsign = flight.get('callsign', 'UNKNOWN')
                latitude = flight.get('latitude')
                longitude = flight.get('longitude')
                altitude = flight.get('altitude', 0)
                aircraft_type = flight.get('aircraft_type', 'UNKNOWN')
                departure = flight.get('departure', 'UNKNOWN')
                arrival = flight.get('arrival', 'UNKNOWN')
                
                # Skip flights without position data
                if latitude is None or longitude is None:
                    continue
                
                # Detect which sector this flight is in
                current_sector = sector_loader.get_sector_for_point(latitude, longitude)
                
                if current_sector:
                    flights_in_sectors += 1
                    sector_distribution[current_sector] = sector_distribution.get(current_sector, 0) + 1
                    
                    # Get sector metadata
                    metadata = sector_loader.get_sector_metadata(current_sector)
                    
                    print(f"  ✅ {callsign}: {aircraft_type} {departure}→{arrival}")
                    print(f"      📍 Position: ({latitude:.4f}, {longitude:.4f}) at FL{altitude//1000:02d}")
                    print(f"      🎯 Sector: {current_sector} ({metadata['full_name']})")
                    print(f"      📻 Frequency: {metadata['frequency']}")
                    
                else:
                    flights_outside_sectors += 1
                    print(f"  ❌ {callsign}: {aircraft_type} {departure}→{arrival}")
                    print(f"      📍 Position: ({latitude:.4f}, {longitude:.4f}) at FL{altitude//1000:02d}")
                    print(f"      🚫 Outside all sectors")
                
                print()  # Empty line for readability
                
            except Exception as e:
                print(f"⚠️  Error processing flight {flight.get('callsign', 'UNKNOWN')}: {e}")
                continue
        
        # Summary statistics
        print("="*60)
        print("📊 SECTOR TRACKING RESULTS")
        print("="*60)
        print(f"Total flights processed: {flights_in_sectors + flights_outside_sectors}")
        print(f"Flights in sectors: {flights_in_sectors}")
        print(f"Flights outside sectors: {flights_outside_sectors}")
        
        if flights_in_sectors > 0:
            print(f"\n🎯 Sector Distribution:")
            for sector, count in sorted(sector_distribution.items(), key=lambda x: x[1], reverse=True):
                metadata = sector_loader.get_sector_metadata(sector)
                print(f"  {sector} ({metadata['full_name']}): {count} flights")
        
        # Test specific sectors with real data
        print(f"\n🔍 Testing Specific Sectors with Real Data...")
        test_sectors = ["WOL", "ASP", "KEN"]  # Popular sectors
        
        for sector_name in test_sectors:
            if sector_name in sector_distribution:
                flights_in_sector = sector_distribution[sector_name]
                metadata = sector_loader.get_sector_metadata(sector_name)
                print(f"  ✅ {sector_name} ({metadata['full_name']}): {flights_in_sector} flights")
                
                # Show some example flights in this sector
                sector_flights = [f for f in flights if sector_loader.get_sector_for_point(f.get('latitude'), f.get('longitude')) == sector_name]
                for flight in sector_flights[:3]:  # Show first 3 flights
                    callsign = flight.get('callsign', 'UNKNOWN')
                    lat = flight.get('latitude')
                    lon = flight.get('longitude')
                    alt = flight.get('altitude', 0)
                    print(f"    - {callsign}: ({lat:.4f}, {lon:.4f}) at FL{alt//1000:02d}")
            else:
                metadata = sector_loader.get_sector_metadata(sector_name)
                print(f"  ❌ {sector_name} ({metadata['full_name']}): No flights")
        
        # Cleanup
        await vatsim_service.cleanup()
        
        print(f"\n🎉 Real VATSIM data test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing with real VATSIM data: {e}")
        return False

async def main():
    """Main test function"""
    try:
        success = await test_real_vatsim_data()
        if success:
            print("\n🎯 Sector tracking is working with real VATSIM data!")
        else:
            print("\n💥 Sector tracking test with real data failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
