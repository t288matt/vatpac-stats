#!/usr/bin/env python3
import asyncio
from app.services.data_service import DataService

async def test_controller_processing():
    print("Testing controller processing...")
    
    # Create data service
    ds = DataService()
    await ds.initialize()
    
    # Test data
    test_controllers = [
        {
            'callsign': 'TEST456',
            'frequency': '123.45',
            'cid': 12345,
            'name': 'Test Controller',
            'rating': 5,
            'facility': 1,
            'server': 'TEST'
        }
    ]
    
    print(f"Processing {len(test_controllers)} test controllers...")
    
    try:
        result = await ds._process_controllers(test_controllers)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_controller_processing())
