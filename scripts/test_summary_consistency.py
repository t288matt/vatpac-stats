#!/usr/bin/env python3
"""
Test Summary Consistency Script

This script identifies inconsistencies between controller_summaries and flight_summaries tables
by checking if the bidirectional relationship between callsigns and JSONB interaction data
is properly maintained.

The script validates:
1. If a controller shows interaction with a flight in aircraft_details, 
   the flight should show that controller in controller_callsigns
2. If a flight shows interaction with a controller in controller_callsigns,
   the controller should show that flight in aircraft_details

Usage:
    python scripts/test_summary_consistency.py
    docker-compose exec app python scripts/test_summary_consistency.py
"""

import json
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple, Any

# Add the app directory to the Python path for container environment
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

try:
    from database import get_database_session
    from sqlalchemy import text
except ImportError as e:
    print(f"Error importing database modules: {e}")
    print("Make sure you're running this from the project root or inside the Docker container")
    sys.exit(1)


class SummaryConsistencyTester:
    """Test class for checking consistency between summary tables."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.inconsistencies = []
        self.stats = {
            'total_controllers': 0,
            'total_flights': 0,
            'controllers_with_interactions': 0,
            'flights_with_interactions': 0,
            'bidirectional_matches': 0,
            'missing_flight_to_controller': 0,
            'missing_controller_to_flight': 0,
            'orphaned_controller_interactions': 0,
            'orphaned_flight_interactions': 0
        }
    
    def _setup_logging(self):
        """Set up basic logging."""
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    async def run_consistency_check(self):
        """Run the complete consistency check."""
        self.logger.info("Starting summary table consistency check...")
        
        try:
            async with get_database_session() as session:
                # Get all controller summaries with aircraft interactions
                controller_data = await self._get_controller_summaries(session)
                
                # Get all flight summaries with controller interactions
                flight_data = await self._get_flight_summaries(session)
                
                # Analyze bidirectional relationships
                await self._analyze_bidirectional_relationships(controller_data, flight_data)
                
                # Generate detailed inconsistency report
                self._generate_inconsistency_report()
                
                # Generate summary statistics
                self._generate_summary_statistics()
                
        except Exception as e:
            self.logger.error(f"Error during consistency check: {e}")
            raise
    
    async def _get_controller_summaries(self, session) -> Dict[str, Dict[str, Any]]:
        """Get all controller summaries with aircraft interaction data."""
        self.logger.info("Fetching controller summaries...")
        
        query = """
            SELECT 
                callsign,
                aircraft_details,
                total_aircraft_handled,
                session_start_time,
                session_end_time
            FROM controller_summaries 
            WHERE aircraft_details IS NOT NULL 
            AND aircraft_details != '[]'
            AND aircraft_details != '{}'
            ORDER BY callsign
        """
        
        result = await session.execute(text(query))
        controllers = {}
        
        for row in result.fetchall():
            try:
                # Handle both JSON strings and direct Python objects
                aircraft_details = row.aircraft_details
                if isinstance(aircraft_details, str):
                    aircraft_details = json.loads(aircraft_details) if aircraft_details else []
                elif not isinstance(aircraft_details, (list, dict)):
                    continue
                
                if isinstance(aircraft_details, list) and aircraft_details:
                    controllers[row.callsign] = {
                        'aircraft_details': aircraft_details,
                        'total_aircraft': row.total_aircraft_handled,
                        'session_start': row.session_start_time,
                        'session_end': row.session_end_time,
                        'flight_callsigns': {item['callsign'] for item in aircraft_details if 'callsign' in item}
                    }
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self.logger.warning(f"Error parsing aircraft_details for {row.callsign}: {e}")
                continue
        
        self.stats['total_controllers'] = len(controllers)
        self.stats['controllers_with_interactions'] = len(controllers)
        
        self.logger.info(f"Found {len(controllers)} controllers with aircraft interactions")
        return controllers
    
    async def _get_flight_summaries(self, session) -> Dict[str, Dict[str, Any]]:
        """Get all flight summaries with controller interaction data."""
        self.logger.info("Fetching flight summaries...")
        
        query = """
            SELECT 
                callsign,
                controller_callsigns,
                controller_time_percentage,
                completion_time
            FROM flight_summaries 
            WHERE controller_callsigns IS NOT NULL 
            AND jsonb_array_length(controller_callsigns) > 0
            ORDER BY callsign
        """
        
        result = await session.execute(text(query))
        flights = {}
        
        for row in result.fetchall():
            try:
                # Handle both JSON strings and direct Python objects
                controller_callsigns = row.controller_callsigns
                if isinstance(controller_callsigns, str):
                    controller_callsigns = json.loads(controller_callsigns) if controller_callsigns else []
                elif not isinstance(controller_callsigns, (list, dict)):
                    continue
                
                # Handle both array format (new) and dict format (old) for backward compatibility
                if isinstance(controller_callsigns, list) and controller_callsigns:
                    # New array format: extract callsigns from array of objects
                    controller_names = {item['callsign'] for item in controller_callsigns if 'callsign' in item}
                    flights[row.callsign] = {
                        'controller_callsigns': controller_callsigns,
                        'controller_time_percentage': row.controller_time_percentage,
                        'completion_time': row.completion_time,
                        'controller_names': controller_names
                    }
                elif isinstance(controller_callsigns, dict) and controller_callsigns:
                    # Old dict format: extract callsigns from dict keys (for backward compatibility)
                    controller_names = set(controller_callsigns.keys())
                    flights[row.callsign] = {
                        'controller_callsigns': controller_callsigns,
                        'controller_time_percentage': row.controller_time_percentage,
                        'completion_time': row.completion_time,
                        'controller_names': controller_names
                    }
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self.logger.warning(f"Error parsing controller_callsigns for {row.callsign}: {e}")
                continue
        
        self.stats['total_flights'] = len(flights)
        self.stats['flights_with_interactions'] = len(flights)
        
        self.logger.info(f"Found {len(flights)} flights with controller interactions")
        return flights
    
    async def _analyze_bidirectional_relationships(self, controller_data: Dict, flight_data: Dict):
        """Analyze the bidirectional relationships between controllers and flights."""
        self.logger.info("Analyzing bidirectional relationships...")
        
        # Check each controller's aircraft interactions
        for controller_callsign, controller_info in controller_data.items():
            controller_flights = controller_info['flight_callsigns']
            
            for flight_callsign in controller_flights:
                if flight_callsign in flight_data:
                    flight_controllers = flight_data[flight_callsign]['controller_names']
                    
                    # Check if flight shows this controller
                    if controller_callsign in flight_controllers:
                        self.stats['bidirectional_matches'] += 1
                    else:
                        self.stats['missing_flight_to_controller'] += 1
                        self.inconsistencies.append({
                            'type': 'missing_flight_to_controller',
                            'controller': controller_callsign,
                            'flight': flight_callsign,
                            'description': f"Controller {controller_callsign} shows interaction with {flight_callsign}, but flight doesn't show this controller"
                        })
                else:
                    self.stats['orphaned_controller_interactions'] += 1
                    self.inconsistencies.append({
                        'type': 'orphaned_controller_interaction',
                        'controller': controller_callsign,
                        'flight': flight_callsign,
                        'description': f"Controller {controller_callsign} shows interaction with {flight_callsign}, but flight not found in flight_summaries"
                    })
        
        # Check each flight's controller interactions
        for flight_callsign, flight_info in flight_data.items():
            flight_controllers = flight_info['controller_names']
            
            for controller_callsign in flight_controllers:
                if controller_callsign in controller_data:
                    controller_flights = controller_data[controller_callsign]['flight_callsigns']
                    
                    # Check if controller shows this flight
                    if flight_callsign in controller_flights:
                        # Already counted above
                        pass
                    else:
                        self.stats['missing_controller_to_flight'] += 1
                        self.inconsistencies.append({
                            'type': 'missing_controller_to_flight',
                            'controller': controller_callsign,
                            'flight': flight_callsign,
                            'description': f"Flight {flight_callsign} shows interaction with {controller_callsign}, but controller doesn't show this flight"
                        })
                else:
                    self.stats['orphaned_flight_interactions'] += 1
                    self.inconsistencies.append({
                        'type': 'orphaned_flight_interaction',
                        'controller': controller_callsign,
                        'flight': flight_callsign,
                        'description': f"Flight {flight_callsign} shows interaction with {controller_callsign}, but controller not found in controller_summaries"
                    })
    
    def _generate_inconsistency_report(self):
        """Generate detailed inconsistency report."""
        if not self.inconsistencies:
            self.logger.info("✅ No inconsistencies found! All bidirectional relationships are properly maintained.")
            return
        
        self.logger.warning(f"❌ Found {len(self.inconsistencies)} inconsistencies:")
        
        # Group by type
        by_type = {}
        for inc in self.inconsistencies:
            inc_type = inc['type']
            if inc_type not in by_type:
                by_type[inc_type] = []
            by_type[inc_type].append(inc)
        
        # Report by type
        for inc_type, incs in by_type.items():
            self.logger.warning(f"\n{inc_type.upper()} ({len(incs)} issues):")
            for inc in incs[:10]:  # Show first 10 of each type
                self.logger.warning(f"  - {inc['description']}")
            if len(incs) > 10:
                self.logger.warning(f"  ... and {len(incs) - 10} more")
    
    def _generate_summary_statistics(self):
        """Generate summary statistics."""
        self.logger.info("\n" + "="*60)
        self.logger.info("SUMMARY STATISTICS")
        self.logger.info("="*60)
        
        self.logger.info(f"Total Controllers: {self.stats['total_controllers']}")
        self.logger.info(f"Controllers with Interactions: {self.stats['controllers_with_interactions']}")
        self.logger.info(f"Total Flights: {self.stats['total_flights']}")
        self.logger.info(f"Flights with Interactions: {self.stats['flights_with_interactions']}")
        
        self.logger.info(f"\nBidirectional Relationships:")
        self.logger.info(f"  ✅ Properly Matched: {self.stats['bidirectional_matches']}")
        self.logger.info(f"  ❌ Missing Flight→Controller: {self.stats['missing_flight_to_controller']}")
        self.logger.info(f"  ❌ Missing Controller→Flight: {self.stats['missing_controller_to_flight']}")
        self.logger.info(f"  ❌ Orphaned Controller Interactions: {self.stats['orphaned_controller_interactions']}")
        self.logger.info(f"  ❌ Orphaned Flight Interactions: {self.stats['orphaned_flight_interactions']}")
        
        total_issues = (self.stats['missing_flight_to_controller'] + 
                       self.stats['missing_controller_to_flight'] + 
                       self.stats['orphaned_controller_interactions'] + 
                       self.stats['orphaned_flight_interactions'])
        
        if total_issues == 0:
            self.logger.info(f"\n🎉 PERFECT CONSISTENCY: {self.stats['bidirectional_matches']} bidirectional relationships all properly maintained!")
        else:
            consistency_percentage = (self.stats['bidirectional_matches'] / 
                                   (self.stats['bidirectional_matches'] + total_issues)) * 100
            self.logger.warning(f"\n⚠️  CONSISTENCY ISSUES: {consistency_percentage:.1f}% of relationships are properly maintained")
            self.logger.warning(f"   {total_issues} issues need to be resolved")


async def main():
    """Main function to run the consistency check."""
    tester = SummaryConsistencyTester()
    
    try:
        await tester.run_consistency_check()
        
        # Exit with error code if inconsistencies found
        if tester.inconsistencies:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"Error running consistency check: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
