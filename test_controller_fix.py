#!/usr/bin/env python3
"""
Test Controller Summary Processing Fix
"""

import asyncio

async def test_controller_fix():
    """Test the fixed controller summary processing."""
    try:
        from app.services.data_service import get_data_service
        
        print("🔧 Testing fixed controller summary processing...")
        
        # Get the data service
        service = await get_data_service()
        print("✅ Got data service")
        
        # Trigger controller summary processing
        result = await service.trigger_controller_summary_processing()
        print(f"✅ Controller processing result: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_controller_fix())
