#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_controller_processing():
    try:
        from app.services.data_service import get_data_service
        
        print("Getting data service...")
        data_service = await get_data_service()
        
        print("Triggering controller summary processing...")
        result = await data_service.trigger_controller_summary_processing()
        
        print(f"Result: {result}")
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_controller_processing())
    print(f"Final result: {result}")
