#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.session_selector import select_canonical_sessions

async def test_session_selector():
    sessions = await select_canonical_sessions(completion_hours=8, gap_minutes=30)
    
    # Look for JST458
    jst458_sessions = [s for s in sessions if s.get('callsign') == 'JST458']
    
    print(f"Total sessions found: {len(sessions)}")
    print(f"JST458 sessions found: {len(jst458_sessions)}")
    
    if jst458_sessions:
        session = jst458_sessions[0]
        print(f"JST458 session fields: {list(session.keys())}")
        print(f"JST458 full session: {session}")
        print(f"JST458 aircraft_type: {session.get('latest_aircraft_type')}")
        print(f"JST458 aircraft_faa: {session.get('latest_aircraft_faa')}")
        print(f"JST458 aircraft_short: {session.get('latest_aircraft_short')}")
    else:
        print("JST458 not found in session selector results")

if __name__ == "__main__":
    asyncio.run(test_session_selector())
