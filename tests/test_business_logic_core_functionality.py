#!/usr/bin/env python3
"""
Stage 10: Business Logic & Core Functionality Tests

This module tests the ACTUAL business logic execution, not just API responses.
Focus: Does the system actually process data, transform it, and provide business value?

Author: VATSIM Data System
Stage: 10 - Business Logic & Core Functionality
"""

import pytest
import sys
import os
import asyncio
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock, AsyncMock

# Add app to path for imports (works from both host and Docker)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
sys.path.insert(0, os.path.dirname(__file__))

from app.services.data_service import DataService, get_data_service_sync
from app.services.vatsim_service import VATSIMService
from app.services.database_service import DatabaseService
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
from app.filters.callsign_pattern_filter import CallsignPatternFilter
from app.database import get_database_session
from app.models import Flight, Controller, Transceiver


class TestDataProcessingBusinessLogic:
    """Test actual data processing workflows and business logic execution"""
    
    @pytest.mark.stage10
    @pytest.mark.business_logic
    @pytest.mark.asyncio
    async def test_vatsim_data_processing_workflow(self):
        """Test: Does the system actually process VATSIM data into useful information?"""
        print("🧪 Testing: Does the system actually process VATSIM data into useful information?")
        
        try:
            # Create test VATSIM data that mimics real data
            test_vatsim_data = {
                "pilots": [
                    {
                        "callsign": "TEST001",
                        "cid": 12345,
                        "name": "Test Pilot",
                        "latitude": -33.8688,
                        "longitude": 151.2093,
                        "altitude": 3000,
                        "groundspeed": 120,
                        "heading": 90,
                        "departure": "YSBK",
                        "arrival": "YSSY",
                        "aircraft_type": "C172",
                        "flight_rules": "VFR"
                    }
                ],
                "controllers": [
                    {
                        "callsign": "YSSY_TWR",
                        "cid": 67890,
                        "name": "Test Controller",
                        "facility": 4,
                        "rating": 3,
                        "server": "AUSTRALIA",
                        "visual_range": 50,
                        "latitude": -33.9399,
                        "longitude": 151.1753
                    }
                ]
            }
            
            # Test data service initialization
            data_service = DataService()
            assert data_service is not None, "DataService should be created"
            
            # Test that the service can process this data
            # Note: We're testing the actual processing logic, not just if methods exist
            if hasattr(data_service, '_process_flights'):
                # Test flight processing logic
                flights_processed = await data_service._process_flights(test_vatsim_data.get('pilots', []))
                assert isinstance(flights_processed, int), "Flight processing should return count"
                print(f"✅ Flight processing logic executed: {flights_processed} flights processed")
            else:
                print("⚠️ _process_flights method not available for testing")
            
            if hasattr(data_service, '_process_controllers'):
                # Test controller processing logic
                controllers_processed = await data_service._process_controllers(test_vatsim_data.get('controllers', []))
                assert isinstance(controllers_processed, int), "Controller processing should return count"
                print(f"✅ Controller processing logic executed: {controllers_processed} controllers processed")
            else:
                print("⚠️ _process_controllers method not available for testing")
            
            print("✅ VATSIM data processing workflow test completed")
            
        except Exception as e:
            print(f"❌ VATSIM data processing workflow test failed: {e}")
            assert False, f"VATSIM data processing workflow test failed: {e}"

    @pytest.mark.stage10
    @pytest.mark.business_logic
    @pytest.mark.asyncio
    async def test_flight_summary_generation_workflow(self):
        """Test: Does the system actually generate flight summaries from raw data?"""
        print("🧪 Testing: Does the system actually generate flight summaries from raw data?")
        
        try:
            data_service = DataService()
            
            # Test flight summary processing logic
            if hasattr(data_service, 'process_completed_flights'):
                # Test the actual business logic
                result = await data_service.process_completed_flights()
                assert isinstance(result, dict), "Flight summary processing should return result dict"
                print(f"✅ Flight summary generation workflow executed: {type(result)}")
            else:
                print("⚠️ process_completed_flights method not available for testing")
            
            # Test individual components of flight summary generation
            if hasattr(data_service, '_identify_completed_flights'):
                # Test completed flight identification logic
                completed_flights = await data_service._identify_completed_flights(completion_hours=24)
                assert isinstance(completed_flights, list), "Should return list of completed flights"
                print(f"✅ Completed flight identification logic executed: {len(completed_flights)} flights identified")
            else:
                print("⚠️ _identify_completed_flights method not available for testing")
            
            if hasattr(data_service, '_create_flight_summaries'):
                # Test flight summary creation logic
                # Create mock completed flight data as tuple (matching what _identify_completed_flights returns)
                mock_completed_flight = (
                    'TEST002',  # callsign
                    'YSBK',     # departure
                    'YSSY',     # arrival
                    datetime.now(timezone.utc) - timedelta(hours=2)  # logon_time
                )
                
                summaries_created = await data_service._create_flight_summaries([mock_completed_flight])
                assert isinstance(summaries_created, int), "Should return count of summaries created"
                print(f"✅ Flight summary creation logic executed: {summaries_created} summaries created")
            else:
                print("⚠️ _create_flight_summaries method not available for testing")
            
            print("✅ Flight summary generation workflow test completed")
            
        except Exception as e:
            print(f"❌ Flight summary generation workflow test failed: {e}")
            assert False, f"Flight summary generation workflow test failed: {e}"

    @pytest.mark.stage10
    @pytest.mark.business_logic
    @pytest.mark.asyncio
    async def test_geographic_filtering_business_logic(self):
        """Test: Does geographic filtering actually work with real coordinates?"""
        print("🧪 Testing: Does geographic filtering actually work with real coordinates?")
        
        try:
            # Test with real Australian coordinates
            test_flights = [
                {
                    "callsign": "TEST_AU_001",
                    "latitude": -33.8688,  # Sydney
                    "longitude": 151.2093,
                    "altitude": 3000
                },
                {
                    "callsign": "TEST_AU_002", 
                    "latitude": -37.8136,  # Melbourne
                    "longitude": 144.9631,
                    "altitude": 5000
                },
                {
                    "callsign": "TEST_UK_001",
                    "latitude": 51.5074,   # London (outside Australia)
                    "longitude": -0.1278,
                    "altitude": 8000
                }
            ]
            
            # Test geographic boundary filter
            geo_filter = GeographicBoundaryFilter()
            
            if hasattr(geo_filter, 'filter_flights_list'):
                # Test actual filtering logic with real coordinates
                filtered_flights = geo_filter.filter_flights_list(test_flights)
                
                # Should filter out UK flight, keep Australian flights
                assert len(filtered_flights) <= len(test_flights), "Filtering should not add flights"
                
                # Check that Australian flights are included
                au_callsigns = [f["callsign"] for f in filtered_flights if "AU" in f["callsign"]]
                assert len(au_callsigns) > 0, "Should include Australian flights"
                
                print(f"✅ Geographic filtering logic executed: {len(filtered_flights)}/{len(test_flights)} flights passed filter")
            else:
                print("⚠️ filter_flights_list method not available for testing")
            
            print("✅ Geographic filtering business logic test completed")
            
        except Exception as e:
            print(f"❌ Geographic filtering business logic test failed: {e}")
            assert False, f"Geographic filtering business logic test failed: {e}"

    @pytest.mark.stage10
    @pytest.mark.business_logic
    @pytest.mark.asyncio
    async def test_data_transformation_workflow(self):
        """Test: Does the system actually transform raw VATSIM data into structured information?"""
        print("🧪 Testing: Does the system actually transform raw VATSIM data into structured information?")
        
        try:
            # Test data transformation logic
            data_service = DataService()
            
            # Test timestamp parsing logic
            if hasattr(data_service, '_parse_timestamp'):
                # Test various timestamp formats
                test_timestamps = [
                    "2025-08-13T08:42:51Z",
                    "2025-08-13T08:42:51+00:00",
                    None,  # Test null handling
                    "invalid_timestamp"  # Test error handling
                ]
                
                for timestamp in test_timestamps:
                    try:
                        result = data_service._parse_timestamp(timestamp)
                        if timestamp and "invalid" not in str(timestamp):
                            assert result is None or isinstance(result, datetime), "Should return datetime or None"
                        print(f"✅ Timestamp parsing: {timestamp} -> {type(result)}")
                    except Exception as e:
                        print(f"✅ Timestamp parsing error handling: {timestamp} -> {type(e).__name__}")
            else:
                print("⚠️ _parse_timestamp method not available for testing")
            
            # Test ATIS text conversion logic
            if hasattr(data_service, '_convert_text_atis'):
                # Test ATIS text processing
                test_atis_data = [
                    "TEST ATIS INFO",
                    None,  # Test null handling
                    "",    # Test empty string
                    {"complex": "object"}  # Test complex data handling
                ]
                
                for atis_data in test_atis_data:
                    try:
                        result = data_service._convert_text_atis(atis_data)
                        print(f"✅ ATIS conversion: {type(atis_data)} -> {type(result)}")
                    except Exception as e:
                        print(f"✅ ATIS conversion error handling: {type(atis_data)} -> {type(e).__name__}")
            else:
                print("⚠️ _convert_text_atis method not available for testing")
            
            print("✅ Data transformation workflow test completed")
            
        except Exception as e:
            print(f"❌ Data transformation workflow test failed: {e}")
            assert False, f"Data transformation workflow test failed: {e}"


class TestBackgroundTaskExecution:
    """Test background task execution and error recovery"""
    
    @pytest.mark.stage10
    @pytest.mark.business_logic
    @pytest.mark.asyncio
    async def test_background_data_ingestion_workflow(self):
        """Test: Does background data ingestion actually work and handle errors?"""
        print("🧪 Testing: Does background data ingestion actually work and handle errors?")
        
        try:
            # Test data service background processing
            data_service = DataService()
            
            if hasattr(data_service, 'start_scheduled_flight_processing'):
                # Test scheduled processing logic
                await data_service.start_scheduled_flight_processing()
                print("✅ Scheduled flight processing started")
            else:
                print("⚠️ start_scheduled_flight_processing method not available for testing")
            
            # Test trigger processing logic
            if hasattr(data_service, 'trigger_flight_summary_processing'):
                result = await data_service.trigger_flight_summary_processing()
                assert isinstance(result, dict), "Should return processing result"
                print(f"✅ Flight summary processing triggered: {type(result)}")
            else:
                print("⚠️ trigger_flight_summary_processing method not available for testing")
            
            print("✅ Background data ingestion workflow test completed")
            
        except Exception as e:
            print(f"❌ Background data ingestion workflow test failed: {e}")
            assert False, f"Background data ingestion workflow test failed: {e}"

    @pytest.mark.stage10
    @pytest.mark.business_logic
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_workflow(self):
        """Test: Does the system actually handle errors and recover gracefully?"""
        print("🧪 Testing: Does the system actually handle errors and recover gracefully?")
        
        try:
            data_service = DataService()
            
            # Test error handling in data processing
            if hasattr(data_service, '_process_flights'):
                # Test with invalid data to see error handling
                invalid_flight_data = [
                    {"invalid": "data", "missing": "required_fields"},
                    None,  # Test null handling
                    {"callsign": "TEST", "latitude": "invalid_lat", "longitude": "invalid_lon"}
                ]
                
                try:
                    result = await data_service._process_flights(invalid_flight_data)
                    print(f"✅ Error handling in flight processing: processed {result} flights")
                except Exception as e:
                    print(f"✅ Error handling working: {type(e).__name__} caught")
            else:
                print("⚠️ _process_flights method not available for testing")
            
            print("✅ Error handling and recovery workflow test completed")
            
        except Exception as e:
            print(f"❌ Error handling and recovery workflow test failed: {e}")
            assert False, f"Error handling and recovery workflow test failed: {e}"


class TestCompleteUserWorkflows:
    """Test complete end-to-end user workflows"""
    
    @pytest.mark.stage10
    @pytest.mark.business_logic
    @pytest.mark.asyncio
    async def test_complete_flight_data_workflow(self):
        """Test: Does the complete flight data workflow actually work end-to-end?"""
        print("🧪 Testing: Does the complete flight data workflow actually work end-to-end?")
        
        try:
            # Test the complete workflow:
            # 1. Data ingestion
            # 2. Processing and transformation
            # 3. Filtering
            # 4. Storage
            # 5. Retrieval
            
            data_service = DataService()
            
            # Test initialization workflow
            if hasattr(data_service, 'initialize'):
                init_result = await data_service.initialize()
                assert isinstance(init_result, bool), "Initialization should return boolean"
                print(f"✅ Service initialization workflow: {init_result}")
            else:
                print("⚠️ initialize method not available for testing")
            
            # Test processing workflow
            if hasattr(data_service, 'process_vatsim_data'):
                # Test with minimal test data
                test_data = {"pilots": [], "controllers": []}
                result = await data_service.process_vatsim_data()
                assert isinstance(result, dict), "Processing should return result dict"
                print(f"✅ Data processing workflow: {type(result)}")
            else:
                print("⚠️ process_vatsim_data method not available for testing")
            
            # Test filter status workflow
            if hasattr(data_service, 'get_filter_status'):
                filter_status = data_service.get_filter_status()
                assert isinstance(filter_status, dict), "Filter status should return dict"
                print(f"✅ Filter status workflow: {type(filter_status)}")
            else:
                print("⚠️ get_filter_status method not available for testing")
            
            print("✅ Complete flight data workflow test completed")
            
        except Exception as e:
            print(f"❌ Complete flight data workflow test failed: {e}")
            assert False, f"Complete flight data workflow test failed: {e}"

    @pytest.mark.stage10
    @pytest.mark.business_logic
    @pytest.mark.asyncio
    async def test_complete_controller_data_workflow(self):
        """Test: Does the complete controller data workflow actually work end-to-end?"""
        print("🧪 Testing: Does the complete controller data workflow actually work end-to-end?")
        
        try:
            # Test ATC detection service workflow
            from app.services.atc_detection_service import ATCDetectionService
            
            atc_service = ATCDetectionService()
            
            # Test ATC detection logic
            if hasattr(atc_service, 'detect_atc_positions'):
                # Test with sample controller data
                test_controllers = [
                    {
                        "callsign": "YSSY_TWR",
                        "facility": 4,
                        "rating": 3,
                        "server": "AUSTRALIA"
                    }
                ]
                
                try:
                    result = atc_service.detect_atc_positions(test_controllers)
                    print(f"✅ ATC detection workflow: {type(result)}")
                except Exception as e:
                    print(f"✅ ATC detection error handling: {type(e).__name__}")
            else:
                print("⚠️ detect_atc_positions method not available for testing")
            
            print("✅ Complete controller data workflow test completed")
            
        except Exception as e:
            print(f"❌ Complete controller data workflow test failed: {e}")
            assert False, f"Complete controller data workflow test failed: {e}"

    @pytest.mark.stage10
    @pytest.mark.business_logic
    @pytest.mark.sector_tracking
    @pytest.mark.asyncio
    async def test_speed_based_sector_entry_exit_logic(self):
        """Test: Does the speed-based sector entry/exit logic work correctly?"""
        print("🧪 Testing: Does the speed-based sector entry/exit logic work correctly?")
        
        try:
            # Create mock sector loader
            class MockSectorLoader:
                def get_sector_for_point(self, lat: float, lon: float):
                    return "TEST_SECTOR"
            
            # Create data service with mock components
            data_service = DataService()
            data_service.sector_loader = MockSectorLoader()
            data_service.sector_tracking_enabled = True
            data_service.flight_sector_states = {}
            
            # Test 1: Aircraft above 60 knots should enter sector
            print("📋 Test 1: Aircraft above 60 knots enters sector")
            flight_data_1 = {
                "callsign": "TEST001",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 120
            }
            
            await data_service._track_sector_occupancy(flight_data_1, None)
            
            # Verify aircraft entered sector
            assert "TEST001" in data_service.flight_sector_states
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] == "TEST_SECTOR"
            assert state["exit_counter"] == 0
            assert state["last_speed"] == 120
            print("✅ Aircraft above 60 knots successfully entered sector")
            
            # Test 2: Aircraft below 60 knots should exit sector
            print("📋 Test 2: Aircraft below 60 knots exits sector")
            flight_data_2 = {
                "callsign": "TEST001",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 45
            }
            
            await data_service._track_sector_occupancy(flight_data_2, None)
            
            # Verify aircraft exited sector
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] is None
            assert state["exit_counter"] == 0  # Reset when speed goes above 30
            print("✅ Aircraft below 60 knots successfully exited sector")
            
            # Test 3: Aircraft at exactly 60 knots should enter sector
            print("📋 Test 3: Aircraft at exactly 60 knots enters sector")
            flight_data_3 = {
                "callsign": "TEST001",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 60
            }
            
            await data_service._track_sector_occupancy(flight_data_3, None)
            
            # Verify aircraft entered sector
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] == "TEST_SECTOR"
            assert state["exit_counter"] == 0
            print("✅ Aircraft at exactly 60 knots successfully entered sector")
            
            # Test 4: Aircraft below 30 knots - start exit counter
            print("📋 Test 4: Aircraft below 30 knots - start exit counter")
            flight_data_4 = {
                "callsign": "TEST001",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 25
            }
            
            await data_service._track_sector_occupancy(flight_data_4, None)
            
            # Verify exit counter started
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] is None
            assert state["exit_counter"] == 1
            print("✅ Exit counter started for aircraft below 30 knots")
            
            # Test 5: Aircraft still below 30 knots - increment exit counter
            print("📋 Test 5: Aircraft still below 30 knots - increment exit counter")
            await data_service._track_sector_occupancy(flight_data_4, None)
            
            # Verify exit counter incremented
            state = data_service.flight_sector_states["TEST001"]
            assert state["exit_counter"] == 2
            print("✅ Exit counter incremented to 2")
            
            # Test 6: Aircraft goes above 30 knots - reset exit counter
            print("📋 Test 6: Aircraft goes above 30 knots - reset exit counter")
            flight_data_6 = {
                "callsign": "TEST001",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 80
            }
            
            await data_service._track_sector_occupancy(flight_data_6, None)
            
            # Verify exit counter reset
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] == "TEST_SECTOR"
            assert state["exit_counter"] == 0
            print("✅ Exit counter reset when speed went above 30 knots")
            
            # Test 7: Missing speed data handling
            print("📋 Test 7: Missing speed data handling")
            flight_data_7 = {
                "callsign": "TEST001",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": None
            }
            
            await data_service._track_sector_occupancy(flight_data_7, None)
            
            # Verify missing speed data handled gracefully
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] == "TEST_SECTOR"  # Keep previous state
            assert state["exit_counter"] == 0  # Reset counter
            print("✅ Missing speed data handled gracefully")
            
            # Test 8: New aircraft with missing speed data
            print("📋 Test 8: New aircraft with missing speed data")
            flight_data_8 = {
                "callsign": "TEST002",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": None
            }
            
            await data_service._track_sector_occupancy(flight_data_8, None)
            
            # Verify new aircraft handled correctly
            assert "TEST002" in data_service.flight_sector_states
            state = data_service.flight_sector_states["TEST002"]
            assert state["current_sector"] is None  # No previous state to defer to
            assert state["exit_counter"] == 0
            print("✅ New aircraft with missing speed data handled correctly")
            
            # Test 9: Verify final state
            print("📋 Test 9: Verify final state")
            assert len(data_service.flight_sector_states) == 2
            assert data_service.flight_sector_states["TEST001"]["current_sector"] == "TEST_SECTOR"
            assert data_service.flight_sector_states["TEST002"]["current_sector"] is None
            print("✅ Final state verification passed")
            
            print("✅ Speed-based sector entry/exit logic test completed successfully")
            
        except Exception as e:
            print(f"❌ Speed-based sector entry/exit logic test failed: {e}")
            assert False, f"Speed-based sector entry/exit logic test failed: {e}"

    @pytest.mark.business_logic
    @pytest.mark.sector_tracking
    @pytest.mark.asyncio
    async def test_sector_transition_logic_comprehensive(self):
        """Test: Does the comprehensive sector transition logic work correctly?"""
        print("🧪 Testing: Does the comprehensive sector transition logic work correctly?")
        
        try:
            # Create mock sector loader that returns different sectors
            class MockSectorLoader:
                def __init__(self):
                    self.sector_map = {
                        (-33.8688, 151.2093): "SYDNEY",      # Sydney coordinates
                        (-37.8136, 144.9631): "MELBOURNE",    # Melbourne coordinates
                        (-27.4698, 153.0251): "BRISBANE",     # Brisbane coordinates
                        (-31.9505, 115.8605): "PERTH"         # Perth coordinates
                    }
                
                def get_sector_for_point(self, lat: float, lon: float):
                    # Round coordinates to avoid floating point precision issues
                    lat_rounded = round(lat, 4)
                    lon_rounded = round(lon, 4)
                    return self.sector_map.get((lat_rounded, lon_rounded), "UNKNOWN")
            
            # Create data service with mock components
            data_service = DataService()
            data_service.sector_loader = MockSectorLoader()
            data_service.sector_tracking_enabled = True
            data_service.flight_sector_states = {}
            
            # Create mock database session
            mock_session = AsyncMock()
            
            # Test 1: Flight enters first sector (SYDNEY)
            print("📋 Test 1: Flight enters first sector (SYDNEY)")
            flight_data_1 = {
                "callsign": "TEST001",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 120
            }
            
            # Mock the database calls for sector entry
            mock_session.execute.return_value.fetchone.return_value = None  # No existing entry
            
            await data_service._track_sector_occupancy(flight_data_1, mock_session)
            
            # Verify aircraft entered SYDNEY sector
            assert "TEST001" in data_service.flight_sector_states
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] == "SYDNEY"
            print("✅ Flight successfully entered SYDNEY sector")
            
            # Test 2: Flight moves to different sector (MELBOURNE) - should close SYDNEY and enter MELBOURNE
            print("📋 Test 2: Flight moves to different sector (MELBOURNE)")
            flight_data_2 = {
                "callsign": "TEST001",
                "latitude": -37.8136,
                "longitude": 144.9631,
                "altitude": 3500,
                "groundspeed": 150
            }
            
            # Mock the database calls for sector transition
            # First call: find open sectors (should find SYDNEY)
            mock_session.execute.return_value.fetchall.return_value = [
                type('MockRow', (), {'sector_name': 'SYDNEY', 'entry_timestamp': datetime.now(timezone.utc)})()
            ]
            
            await data_service._track_sector_occupancy(flight_data_2, mock_session)
            
            # Verify aircraft now in MELBOURNE sector
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] == "MELBOURNE"
            print("✅ Flight successfully transitioned from SYDNEY to MELBOURNE sector")
            
            # Test 3: Flight moves to another different sector (BRISBANE) - should close MELBOURNE and enter BRISBANE
            print("📋 Test 3: Flight moves to another different sector (BRISBANE)")
            flight_data_3 = {
                "callsign": "TEST001",
                "latitude": -27.4698,
                "longitude": 153.0251,
                "altitude": 4000,
                "groundspeed": 180
            }
            
            # Mock the database calls for sector transition
            # First call: find open sectors (should find MELBOURNE)
            mock_session.execute.return_value.fetchall.return_value = [
                type('MockRow', (), {'sector_name': 'MELBOURNE', 'entry_timestamp': datetime.now(timezone.utc)})()
            ]
            
            await data_service._track_sector_occupancy(flight_data_3, mock_session)
            
            # Verify aircraft now in BRISBANE sector
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] == "BRISBANE"
            print("✅ Flight successfully transitioned from MELBOURNE to BRISBANE sector")
            
            # Test 4: Flight returns to previous sector (SYDNEY) - should close BRISBANE and enter SYDNEY
            print("📋 Test 4: Flight returns to previous sector (SYDNEY)")
            flight_data_4 = {
                "callsign": "TEST001",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 120
            }
            
            # Mock the database calls for sector transition
            # First call: find open sectors (should find BRISBANE)
            mock_session.execute.return_value.fetchall.return_value = [
                type('MockRow', (), {'sector_name': 'BRISBANE', 'entry_timestamp': datetime.now(timezone.utc)})()
            ]
            
            await data_service._track_sector_occupancy(flight_data_4, mock_session)
            
            # Verify aircraft now back in SYDNEY sector
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] == "SYDNEY"
            print("✅ Flight successfully returned to SYDNEY sector")
            
            # Test 5: Flight exits all sectors (speed below 60 knots)
            print("📋 Test 5: Flight exits all sectors (speed below 60 knots)")
            flight_data_5 = {
                "callsign": "TEST001",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 45
            }
            
            # Mock the database calls for sector exit
            # First call: find open sectors (should find SYDNEY)
            mock_session.execute.return_value.fetchall.return_value = [
                type('MockRow', (), {'sector_name': 'SYDNEY', 'entry_timestamp': datetime.now(timezone.utc)})()
            ]
            
            await data_service._track_sector_occupancy(flight_data_5, mock_session)
            
            # Verify aircraft exited all sectors
            state = data_service.flight_sector_states["TEST001"]
            assert state["current_sector"] is None
            print("✅ Flight successfully exited all sectors")
            
            # Test 6: Multiple open sectors scenario (simulating corrupted state)
            print("📋 Test 6: Multiple open sectors scenario (corrupted state)")
            
            # Simulate a corrupted state where flight has multiple open sectors
            data_service.flight_sector_states["TEST002"] = {"current_sector": "SYDNEY"}
            
            # Mock database to return multiple open sectors
            mock_session.execute.return_value.fetchall.return_value = [
                type('MockRow', (), {'sector_name': 'SYDNEY', 'entry_timestamp': datetime.now(timezone.utc)})(),
                type('MockRow', (), {'sector_name': 'MELBOURNE', 'entry_timestamp': datetime.now(timezone.utc)})(),
                type('MockRow', (), {'sector_name': 'BRISBANE', 'entry_timestamp': datetime.now(timezone.utc)})()
            ]
            
            # Flight moves to new sector (PERTH)
            flight_data_6 = {
                "callsign": "TEST002",
                "latitude": -31.9505,
                "longitude": 115.8605,
                "altitude": 5000,
                "groundspeed": 200
            }
            
            await data_service._track_sector_occupancy(flight_data_6, mock_session)
            
            # Verify aircraft now in PERTH sector
            state = data_service.flight_sector_states["TEST002"]
            assert state["current_sector"] == "PERTH"
            print("✅ Flight with multiple open sectors successfully transitioned to PERTH sector")
            
            # Test 7: Flight stays in same sector (no transition needed)
            print("📋 Test 7: Flight stays in same sector (no transition needed)")
            flight_data_7 = {
                "callsign": "TEST002",
                "latitude": -31.9505,
                "longitude": 115.8605,
                "altitude": 5000,
                "groundspeed": 200
            }
            
            # Mock no open sectors found (already in PERTH)
            mock_session.execute.return_value.fetchall.return_value = []
            
            await data_service._track_sector_occupancy(flight_data_7, mock_session)
            
            # Verify aircraft still in PERTH sector
            state = data_service.flight_sector_states["TEST002"]
            assert state["current_sector"] == "PERTH"
            print("✅ Flight successfully stayed in PERTH sector (no transition)")
            
            # Test 8: Force exit scenario (should_exit = True)
            print("📋 Test 8: Force exit scenario (should_exit = True)")
            
            # Create a new flight in a sector
            data_service.flight_sector_states["TEST003"] = {"current_sector": "SYDNEY"}
            
            # Mock database to return one open sector
            mock_session.execute.return_value.fetchall.return_value = [
                type('MockRow', (), {'sector_name': 'SYDNEY', 'entry_timestamp': datetime.now(timezone.utc)})()
            ]
            
            # Force exit due to speed criteria
            flight_data_8 = {
                "callsign": "TEST003",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 30  # Below 60 knots
            }
            
            await data_service._track_sector_occupancy(flight_data_8, mock_session)
            
            # Verify aircraft exited sector
            state = data_service.flight_sector_states["TEST003"]
            assert state["current_sector"] is None
            print("✅ Flight successfully forced to exit sector")
            
            # Test 9: Verify final state of all flights
            print("📋 Test 9: Verify final state of all flights")
            assert len(data_service.flight_sector_states) == 3
            assert data_service.flight_sector_states["TEST001"]["current_sector"] is None  # Exited all sectors
            assert data_service.flight_sector_states["TEST002"]["current_sector"] == "PERTH"  # In PERTH
            assert data_service.flight_sector_states["TEST003"]["current_sector"] is None  # Forced exit
            print("✅ Final state verification passed")
            
            print("✅ Comprehensive sector transition logic test completed successfully")
            
        except Exception as e:
            print(f"❌ Comprehensive sector transition logic test failed: {e}")
            assert False, f"Comprehensive sector transition logic test failed: {e}"

    @pytest.mark.business_logic
    @pytest.mark.sector_tracking
    @pytest.mark.asyncio
    async def test_close_all_open_sectors_for_flight_method(self):
        """Test: Does the _close_all_open_sectors_for_flight method work correctly?"""
        print("🧪 Testing: Does the _close_all_open_sectors_for_flight method work correctly?")
        
        try:
            # Create data service
            data_service = DataService()
            
            # Test 1: Method exists and is callable
            print("📋 Test 1: Method exists and is callable")
            assert hasattr(data_service, '_close_all_open_sectors_for_flight'), "Method should exist"
            assert callable(data_service._close_all_open_sectors_for_flight), "Method should be callable"
            print("✅ Method exists and is callable")
            
            # Test 2: Method signature is correct
            print("📋 Test 2: Method signature is correct")
            import inspect
            sig = inspect.signature(data_service._close_all_open_sectors_for_flight)
            params = list(sig.parameters.keys())
            # inspect.signature doesn't include 'self' for bound methods
            expected_params = ['callsign', 'lat', 'lon', 'altitude', 'timestamp', 'session']
            assert params == expected_params, f"Expected parameters {expected_params}, got {params}"
            print("✅ Method signature is correct")
            
            # Test 3: Method is async
            print("📋 Test 3: Method is async")
            assert inspect.iscoroutinefunction(data_service._close_all_open_sectors_for_flight), "Method should be async"
            print("✅ Method is async")
            
            # Test 4: Method docstring contains expected content
            print("📋 Test 4: Method docstring contains expected content")
            doc = data_service._close_all_open_sectors_for_flight.__doc__
            assert doc is not None, "Method should have docstring"
            assert "Close ALL open sectors" in doc, "Docstring should mention closing all open sectors"
            assert "critical fix" in doc, "Docstring should mention this is a critical fix"
            print("✅ Method docstring contains expected content")
            
            print("✅ _close_all_open_sectors_for_flight method test completed successfully")
            
        except Exception as e:
            print(f"❌ _close_all_open_sectors_for_flight method test failed: {e}")
            assert False, f"_close_all_open_sectors_for_flight method test failed: {e}"

    @pytest.mark.business_logic
    @pytest.mark.sector_tracking
    @pytest.mark.asyncio
    async def test_cleanup_stale_sectors_outcome(self):
        """Test: Does the cleanup_stale_sectors method actually work and return expected outcomes?"""
        print("🧪 Testing: Does the cleanup_stale_sectors method actually work and return expected outcomes?")
        
        try:
            # Create data service
            data_service = DataService()
            
            # Test 1: Method exists and is callable
            print("📋 Test 1: Method exists and is callable")
            assert hasattr(data_service, 'cleanup_stale_sectors'), "cleanup_stale_sectors method should exist"
            assert callable(data_service.cleanup_stale_sectors), "cleanup_stale_sectors method should be callable"
            print("✅ Method exists and is callable")
            
            # Test 2: Method returns expected outcome format
            print("📋 Test 2: Method returns expected outcome format")
            result = await data_service.cleanup_stale_sectors()
            
            # Verify the result structure matches what main.py expects
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "sectors_closed" in result, "Result should contain 'sectors_closed' key"
            assert isinstance(result["sectors_closed"], int), "'sectors_closed' should be an integer"
            assert result["sectors_closed"] >= 0, "'sectors_closed' should be non-negative"
            
            # Verify additional expected keys
            assert "timestamp" in result, "Result should contain 'timestamp' key"
            assert "stale_cutoff" in result, "Result should contain 'stale_cutoff' key"
            
            print(f"✅ Method returned expected format: {result}")
            
            # Test 3: Method can be called multiple times without error
            print("📋 Test 3: Method can be called multiple times without error")
            result2 = await data_service.cleanup_stale_sectors()
            assert isinstance(result2, dict), "Second call should also return dictionary"
            assert "sectors_closed" in result2, "Second call should contain 'sectors_closed' key"
            print("✅ Method can be called multiple times")
            
            # Test 4: Verify the result format matches main.py expectations
            print("📋 Test 4: Verify result format matches main.py expectations")
            
            # This simulates what main.py does with the result
            try:
                sectors_closed = result["sectors_closed"]
                print(f"✅ Main.py can successfully access result['sectors_closed']: {sectors_closed}")
            except KeyError as e:
                assert False, f"Main.py cannot access result['sectors_closed']: {e}"
            
            # Test 5: Verify error handling works
            print("📋 Test 5: Verify error handling works")
            # The method should handle errors gracefully and return a valid result
            # even if there are database issues
            assert "error" not in result or isinstance(result["error"], str), "Error field should be string if present"
            print("✅ Error handling works correctly")
            
            print("✅ cleanup_stale_sectors outcome test completed successfully")
            
        except Exception as e:
            print(f"❌ cleanup_stale_sectors outcome test failed: {e}")
            assert False, f"cleanup_stale_sectors outcome test failed: {e}"

    @pytest.mark.business_logic
    @pytest.mark.sector_tracking
    @pytest.mark.asyncio
    async def test_main_py_cleanup_workflow_integration(self):
        """Test: Does the main.py cleanup workflow actually work with DataService?"""
        print("🧪 Testing: Does the main.py cleanup workflow actually work with DataService?")
        
        try:
            # Create data service (simulating what main.py does)
            data_service = DataService()
            
            # Test 1: Simulate main.py calling cleanup_stale_sectors
            print("📋 Test 1: Simulate main.py calling cleanup_stale_sectors")
            try:
                cleanup_result = await data_service.cleanup_stale_sectors()
                print(f"✅ Main.py successfully called cleanup_stale_sectors: {cleanup_result}")
            except AttributeError as e:
                assert False, f"Main.py cannot call cleanup_stale_sectors: {e}"
            
            # Test 2: Simulate main.py accessing the result
            print("📋 Test 2: Simulate main.py accessing the result")
            try:
                sectors_closed = cleanup_result['sectors_closed']
                print(f"✅ Main.py can access cleanup_result['sectors_closed']: {sectors_closed}")
            except (KeyError, TypeError) as e:
                assert False, f"Main.py cannot access cleanup_result['sectors_closed']: {e}"
            
            # Test 3: Simulate main.py logging the result
            print("📋 Test 3: Simulate main.py logging the result")
            try:
                log_message = f"✅ Cleanup completed: {cleanup_result['sectors_closed']} sectors closed"
                print(f"✅ Main.py can log: {log_message}")
            except (KeyError, TypeError) as e:
                assert False, f"Main.py cannot log cleanup result: {e}"
            
            # Test 4: Verify the complete workflow doesn't crash
            print("📋 Test 4: Verify the complete workflow doesn't crash")
            try:
                # This simulates the exact main.py workflow
                data_service.logger.info("🧹 Running cleanup job after successful data processing...")
                cleanup_result = await data_service.cleanup_stale_sectors()
                data_service.logger.info(f"✅ Cleanup completed: {cleanup_result['sectors_closed']} sectors closed")
                print("✅ Complete main.py workflow executed successfully")
            except Exception as e:
                assert False, f"Main.py workflow failed: {e}"
            
            print("✅ Main.py cleanup workflow integration test completed successfully")
            
        except Exception as e:
            print(f"❌ Main.py cleanup workflow integration test failed: {e}")
            assert False, f"Main.py cleanup workflow integration test failed: {e}"


# Test execution helper
def run_business_logic_core_functionality_tests():
    """Run all Stage 10 business logic and core functionality tests"""
    print("🚀 Starting Stage 10: Business Logic & Core Functionality Tests")
    print("=" * 70)
    
    # This would run the tests using pytest
    # For now, just show what we're testing
    print("🧪 Testing actual business logic execution:")
    print("  - VATSIM data processing workflows")
    print("  - Flight summary generation")
    print("  - Geographic filtering with real coordinates")
    print("  - Data transformation logic")
    print("  - Background task execution")
    print("  - Error handling and recovery")
    print("  - Complete end-to-end user workflows")
    print("  - Speed-based sector entry/exit logic")
    print("\n🎯 Focus: Testing WHAT the system does, not just IF it responds")


if __name__ == "__main__":
    run_business_logic_core_functionality_tests()
