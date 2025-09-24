#!/usr/bin/env python3
"""
Cleanup Invalid Controller Callsigns from Flight Summaries JSONB

This script removes invalid controller callsigns from the controller_callsigns
JSONB field in flight_summaries table, using the controller_callsigns_list.txt
file as the validation source.

Usage:
    python cleanup_invalid_controllers.py --dry-run    # Analyze only (default)
    python cleanup_invalid_controllers.py --execute    # Actually clean the data
"""

import asyncio
import argparse
import json
from datetime import datetime
from app.database import get_database_session
from sqlalchemy import text

async def load_valid_controllers():
    """Load valid controller callsigns from the config file (format: CALLSIGN, FREQUENCY)."""
    try:
        controllers = set()
        with open('airspace_sector_data/controller_callsigns_list.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    # Parse format: CALLSIGN, FREQUENCY
                    if ',' in line:
                        callsign = line.split(',')[0].strip()
                        if callsign:  # Only add if callsign is not empty
                            controllers.add(callsign)
                    else:
                        # Fallback for old format (just callsign)
                        controllers.add(line)
        print(f"✅ Loaded {len(controllers)} valid controller callsigns")
        return controllers
    except Exception as e:
        print(f"❌ Error loading controller callsigns: {e}")
        return set()

async def analyze_invalid_controllers(valid_controllers):
    """Analyze the current state of controller data."""
    async with get_database_session() as session:
        # Get all unique controller callsigns in the data
        result = await session.execute(text("""
            SELECT DISTINCT jsonb_object_keys(controller_callsigns) as controller_callsign
            FROM flight_summaries 
            WHERE enrichment_status = 'completed'
            AND controller_callsigns != '{}'::jsonb
            ORDER BY controller_callsign
        """))
        
        controllers_in_data = [row.controller_callsign for row in result.fetchall()]
        invalid_controllers = [c for c in controllers_in_data if c not in valid_controllers]
        
        print(f"\n📊 ANALYSIS RESULTS:")
        print(f"   Total unique controllers in data: {len(controllers_in_data)}")
        print(f"   Valid controllers: {len(controllers_in_data) - len(invalid_controllers)}")
        print(f"   Invalid controllers: {len(invalid_controllers)}")
        
        if invalid_controllers:
            print(f"\n🚨 INVALID CONTROLLERS FOUND:")
            for i, controller in enumerate(invalid_controllers[:20], 1):
                print(f"   {i:2d}. {controller}")
            if len(invalid_controllers) > 20:
                print(f"   ... and {len(invalid_controllers) - 20} more")
        
        return invalid_controllers

async def get_affected_flights(invalid_controllers):
    """Get flights that have invalid controllers."""
    async with get_database_session() as session:
        result = await session.execute(text("""
            SELECT 
                fs.id,
                fs.callsign,
                fs.controller_callsigns,
                (
                    SELECT COUNT(*)
                    FROM jsonb_object_keys(fs.controller_callsigns) AS t(key)
                    WHERE t.key = ANY(:invalid_controllers)
                ) as invalid_count
            FROM flight_summaries fs
            WHERE fs.enrichment_status = 'completed'
            AND fs.controller_callsigns != '{}'::jsonb
            AND EXISTS (
                SELECT 1 
                FROM jsonb_object_keys(fs.controller_callsigns) AS t(key)
                WHERE t.key = ANY(:invalid_controllers)
            )
            ORDER BY invalid_count DESC, fs.id
            LIMIT 10
        """), {"invalid_controllers": invalid_controllers})
        
        rows = result.fetchall()
        print(f"\n📋 SAMPLE AFFECTED FLIGHTS (showing first 10):")
        for row in rows:
            current_controllers = list(dict(row.controller_callsigns).keys())
            print(f"   ID {row.id}: {row.callsign} - {current_controllers} ({row.invalid_count} invalid)")
        
        return len(rows)

async def clean_invalid_controllers(valid_controllers, dry_run=True):
    """Clean invalid controllers from the JSONB data."""
    async with get_database_session() as session:
        if dry_run:
            print(f"\n🔍 DRY RUN MODE - No changes will be made")
            
            # Count affected flights
            result = await session.execute(text("""
                SELECT COUNT(*) as affected_count
                FROM flight_summaries 
                WHERE enrichment_status = 'completed'
                AND controller_callsigns != '{}'::jsonb
                AND EXISTS (
                    SELECT 1 
                    FROM jsonb_object_keys(controller_callsigns) AS t(key)
                    WHERE t.key NOT IN (SELECT unnest(:valid_controllers))
                )
            """), {"valid_controllers": list(valid_controllers)})
            
            affected_count = result.scalar()
            print(f"   Would affect {affected_count} flights")
            
        else:
            print(f"\n🧹 EXECUTING CLEANUP - Removing invalid controllers...")
            
            # Update the JSONB data
            result = await session.execute(text("""
                UPDATE flight_summaries 
                SET 
                    controller_callsigns = (
                        SELECT jsonb_object_agg(key, value)
                        FROM jsonb_each(controller_callsigns) AS t(key, value)
                        WHERE t.key = ANY(:valid_controllers)
                    ),
                    enrichment_completed_at = now()
                WHERE enrichment_status = 'completed'
                AND controller_callsigns != '{}'::jsonb
                AND EXISTS (
                    SELECT 1 
                    FROM jsonb_object_keys(controller_callsigns) AS t(key)
                    WHERE t.key NOT IN (SELECT unnest(:valid_controllers))
                )
            """), {"valid_controllers": list(valid_controllers)})
            
            print(f"   ✅ Updated {result.rowcount} flights")
            await session.commit()

async def verify_cleanup(valid_controllers):
    """Verify the cleanup was successful."""
    async with get_database_session() as session:
        # Check for any remaining invalid controllers
        result = await session.execute(text("""
            SELECT DISTINCT jsonb_object_keys(controller_callsigns) as controller_callsign
            FROM flight_summaries 
            WHERE enrichment_status = 'completed'
            AND controller_callsigns != '{}'::jsonb
        """))
        
        remaining_controllers = [row.controller_callsign for row in result.fetchall()]
        invalid_remaining = [c for c in remaining_controllers if c not in valid_controllers]
        
        print(f"\n✅ VERIFICATION RESULTS:")
        print(f"   Total controllers remaining: {len(remaining_controllers)}")
        print(f"   Invalid controllers remaining: {len(invalid_remaining)}")
        
        if invalid_remaining:
            print(f"   ⚠️  Still invalid: {invalid_remaining}")
        else:
            print(f"   🎉 All remaining controllers are valid!")

async def main():
    parser = argparse.ArgumentParser(description='Cleanup invalid controller callsigns from flight summaries')
    parser.add_argument('--dry-run', action='store_true', default=True, 
                       help='Analyze only, do not make changes (default)')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually execute the cleanup')
    
    args = parser.parse_args()
    dry_run = args.dry_run and not args.execute
    
    print("=" * 80)
    print("🧹 CLEANUP INVALID CONTROLLER CALLSIGNS FROM FLIGHT SUMMARIES")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Load valid controllers
    valid_controllers = await load_valid_controllers()
    if not valid_controllers:
        print("❌ Cannot proceed without valid controller list")
        return
    
    # Analyze current state
    invalid_controllers = await analyze_invalid_controllers(valid_controllers)
    
    if not invalid_controllers:
        print("\n🎉 No invalid controllers found! Data is already clean.")
        return
    
    # Show affected flights
    await get_affected_flights(invalid_controllers)
    
    # Clean the data
    await clean_invalid_controllers(valid_controllers, dry_run)
    
    # Verify results
    await verify_cleanup(valid_controllers)
    
    print("\n" + "=" * 80)
    print("✅ CLEANUP COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())




