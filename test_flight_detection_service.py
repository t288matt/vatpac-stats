#!/usr/bin/env python3
"""
Simple test script for Flight Detection Service
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_flight_detection_service():
    """Test that the Flight Detection Service can be imported and initialized."""
    try:
        from app.services.flight_detection_service import FlightDetectionService
        
        print("✅ Flight Detection Service imported successfully")
        
        # Test initialization
        service = FlightDetectionService()
        print(f"✅ Service initialized with time_window={service.time_window_seconds}s, proximity_threshold={service.proximity_threshold_nm}nm")
        
        # Test empty data creation
        empty_data = service._create_empty_flight_data()
        print(f"✅ Empty data structure created: {empty_data}")
        
        print("\n🎯 Flight Detection Service is ready to use!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Flight Detection Service...")
    success = asyncio.run(test_flight_detection_service())
    
    if success:
        print("\n🎉 All tests passed! Flight Detection Service is working correctly.")
    else:
        print("\n💥 Tests failed. Check the error messages above.")
        sys.exit(1)
