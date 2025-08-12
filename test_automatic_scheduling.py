#!/usr/bin/env python3
"""
Test the automatic flight summary scheduling functionality
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append('/app')

from app.services.data_service import get_data_service

async def test_automatic_scheduling():
    """Test the automatic scheduling functionality"""
    try:
        print("🔌 Testing automatic flight summary scheduling...")
        
        # Get data service (this will start the scheduled processing)
        data_service = await get_data_service()
        print("✅ Data service initialized with automatic scheduling")
        
        # Test manual trigger
        print("🔧 Testing manual trigger...")
        result = await data_service.trigger_flight_summary_processing()
        print(f"✅ Manual trigger result: {result}")
        
        # Wait a bit to see scheduled processing start
        print("⏳ Waiting 30 seconds to see scheduled processing start...")
        await asyncio.sleep(30)
        
        print("🎉 Automatic scheduling test completed!")
        print("📝 Check Docker logs for scheduled processing messages:")
        print("   docker logs vatsim_app | grep 'Scheduled flight summary'")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_automatic_scheduling())
