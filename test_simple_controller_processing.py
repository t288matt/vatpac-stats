#!/usr/bin/env python3
import asyncio
import sys
import os

print("DEBUG: Script started")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
print("DEBUG: Added app to sys.path")

async def test_simple_controller_processing():
    try:
        print("DEBUG: About to import get_data_service_sync")
        from app.services.data_service import get_data_service_sync
        print("DEBUG: Successfully imported get_data_service_sync")
        
        print("DEBUG: About to import get_database_session")
        from app.database import get_database_session
        print("DEBUG: Successfully imported get_database_session")
        
        print("DEBUG: About to import text")
        from sqlalchemy import text
        print("DEBUG: Successfully imported text")
        
        print("DEBUG: About to import datetime")
        from datetime import datetime, timezone, timedelta
        print("DEBUG: Successfully imported datetime")
        
        print("Getting data service in test mode...")
        data_service = get_data_service_sync()  # Use sync version with _test_mode
        print("DEBUG: Successfully got data service in test mode")
        
        print("Testing simple controller identification...")
        
        # Test just the identification logic without ATC detection
        print("DEBUG: About to get database session")
        async with get_database_session() as session:
            print("DEBUG: Got database session")
            
            # Get configuration
            completion_minutes = 30
            completion_threshold = datetime.now(timezone.utc) - timedelta(minutes=completion_minutes)
            
            print(f"Looking for controllers inactive since: {completion_threshold}")
            
            # Test the same query that _identify_completed_controllers uses
            query = """
                SELECT DISTINCT callsign, cid, logon_time, MAX(last_updated) as session_end_time
                FROM controllers 
                WHERE (callsign, cid) NOT IN (
                    SELECT DISTINCT callsign, cid FROM controller_summaries
                )
                GROUP BY callsign, cid, logon_time
                HAVING MAX(last_updated) < :completion_threshold
            """
            
            print("DEBUG: About to execute query")
            result = await session.execute(text(query), {"completion_threshold": completion_threshold})
            print("DEBUG: Query executed successfully")
            
            completed_controllers = result.fetchall()
            print("DEBUG: Fetched results")
            
            print(f"Found {len(completed_controllers)} completed controllers")
            
            if completed_controllers:
                print("Sample controllers:")
                for i, controller in enumerate(completed_controllers[:5]):
                    callsign, cid, logon_time, session_end_time = controller
                    duration = (session_end_time - logon_time).total_seconds() / 60
                    print(f"  {callsign} (CID: {cid}): {duration:.1f} minutes")
            
            return {
                "status": "success",
                "completed_controllers_found": len(completed_controllers),
                "completion_threshold": completion_threshold.isoformat()
            }
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("DEBUG: About to run async function")
    result = asyncio.run(test_simple_controller_processing())
    print(f"Final result: {result}")
