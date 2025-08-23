#!/usr/bin/env python3
"""
Script to manually trigger flight summary processing.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.data_service import DataService
from app.config import get_config

async def trigger_summary_processing():
    """Trigger flight summary processing manually."""
    try:
        print("🚀 Triggering flight summary processing...")
        
        # Initialize the data service
        data_service = DataService()
        
        # Trigger the processing
        result = await data_service.trigger_flight_summary_processing()
        
        print("✅ Summary processing completed!")
        print(f"📊 Results: {result}")
        
        # Check the summaries table
        if result.get('summaries_created', 0) > 0:
            print(f"🎉 Created {result['summaries_created']} flight summaries!")
        else:
            print("⚠️ No summaries were created")
            
        return result
        
    except Exception as e:
        print(f"❌ Error triggering summary processing: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🔧 Manual Flight Summary Processing Trigger")
    print("=" * 50)
    print()
    
    result = asyncio.run(trigger_summary_processing())
    
    if result:
        print(f"\n✅ Processing completed successfully!")
    else:
        print(f"\n❌ Processing failed!")
