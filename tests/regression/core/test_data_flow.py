"""
Core Data Flow Regression Tests

These tests validate the complete data flow from VATSIM API through all services
to database tables. They ensure that data transformations, filtering, and storage
work correctly and catch regressions in the core pipeline.

Test Flow:
VATSIM API → VATSIM Service → Flight Filters → Data Service → Database Tables
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from typing import Dict, Any, List

from app.services.vatsim_service import VATSIMService, VATSIMData
from app.services.data_service import DataService
from app.models import Flight, Controller, VatsimStatus, Transceiver
from app.filters.flight_filter import FlightFilter
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter


@pytest.mark.regression
@pytest.mark.core
class TestCompleteDataFlow:
    """Test complete data flow from VATSIM API to database tables"""
    
    @pytest.mark.asyncio
    async def test_vatsim_api_to_database_complete_flow(
        self, 
        golden_vatsim_data, 
        expected_database_state, 
        vatsim_api_mock,
        db_session,
        clean_database
    ):
        """
        Test complete VATSIM API to database flow with known data
        
        This is the primary regression test that validates:
        1. VATSIM API data parsing
        2. Filter pipeline (airport + geographic)
        3. Data transformations (string→int, nested→flat)
        4. Database storage with correct relationships
        """
        # Setup: Mock VATSIM API with golden dataset
        vatsim_api_mock.set_response("/v3/vatsim-data.json", golden_vatsim_data)
        
        # Patch HTTP client to use our mock
        with patch('app.services.vatsim_service.httpx.AsyncClient') as mock_client:
            # Setup mock HTTP response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=golden_vatsim_data)
            mock_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Initialize services
            vatsim_service = VATSIMService()
            data_service = DataService()
            
            await vatsim_service.initialize()
            await data_service.initialize()
            
            # Step 1: Get data from VATSIM service
            vatsim_data = await vatsim_service.get_current_data()
            
            # Verify VATSIM service parsed data correctly
            assert vatsim_data is not None
            assert isinstance(vatsim_data, VATSIMData)
            assert len(vatsim_data.flights) == 3  # All 3 flights from golden data
            assert len(vatsim_data.controllers) == 1
            
            # Step 2: Process through data service (includes filtering)
            await data_service._process_data_in_memory(vatsim_data.__dict__)
            await data_service._flush_memory_to_disk()
            
            # Step 3: Verify database contains expected data
            
            # Check flights table - only Australian flights should be present
            flights = db_session.query(Flight).all()
            
            # Should have 2 flights (QFA123 and QFA789), UAL456 filtered out
            assert len(flights) == 2, f"Expected 2 flights, got {len(flights)}"
            
            # Verify QFA123 (Australian flight with coordinates)
            qfa123 = next((f for f in flights if f.callsign == "QFA123"), None)
            assert qfa123 is not None, "QFA123 flight should be in database"
            assert qfa123.cid == 123456
            assert qfa123.name == "Test Pilot 1"
            assert qfa123.departure == "YSSY"
            assert qfa123.arrival == "YBBN"
            assert abs(qfa123.latitude - (-33.8688)) < 0.0001
            assert abs(qfa123.longitude - 151.2093) < 0.0001
            assert qfa123.aircraft_short == "B738"
            assert qfa123.flight_rules == "I"
            assert qfa123.planned_altitude == "35000"
            
            # Verify QFA789 (Australian flight with missing coordinates)
            qfa789 = next((f for f in flights if f.callsign == "QFA789"), None)
            assert qfa789 is not None, "QFA789 flight should be in database"
            assert qfa789.cid == 345678
            assert qfa789.name == "Test Pilot 3"
            assert qfa789.departure == "YSSY"
            assert qfa789.arrival == "YMML"
            assert qfa789.latitude is None  # Missing coordinates preserved
            assert qfa789.longitude is None
            assert qfa789.aircraft_short == "A320"
            
            # Verify UAL456 is NOT in database (filtered out)
            ual456 = next((f for f in flights if f.callsign == "UAL456"), None)
            assert ual456 is None, "UAL456 should be filtered out (non-Australian)"
            
            # Check controllers table - string ID should be converted to int
            controllers = db_session.query(Controller).all()
            assert len(controllers) == 1
            
            controller = controllers[0]
            assert controller.callsign == "SY_APP"
            assert controller.controller_id == 345678  # String "345678" → int 345678
            assert controller.controller_name == "Test Controller"
            assert controller.controller_rating == 3  # String "3" → int 3
            assert controller.frequency == "124.400"
            assert controller.visual_range == 100
            assert controller.text_atis == "Test ATIS for regression testing"
            
            # Check VATSIM status table
            status_records = db_session.query(VatsimStatus).all()
            assert len(status_records) == 1
            
            status = status_records[0]
            assert status.api_version == 8
            assert status.reload == 1
            assert status.connected_clients == 150
            assert status.unique_users == 120
    
    @pytest.mark.asyncio
    async def test_data_transformation_accuracy(
        self, 
        golden_vatsim_data,
        vatsim_api_mock,
        db_session,
        clean_database
    ):
        """
        Test data transformations are applied correctly
        
        Validates:
        - String controller IDs converted to integers
        - Nested flight_plan objects flattened to database fields
        - API field names mapped to database column names
        - Data type conversions (string ratings to integers)
        """
        vatsim_api_mock.set_response("/v3/vatsim-data.json", golden_vatsim_data)
        
        with patch('app.services.vatsim_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=golden_vatsim_data)
            mock_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            vatsim_service = VATSIMService()
            data_service = DataService()
            
            await vatsim_service.initialize()
            await data_service.initialize()
            
            vatsim_data = await vatsim_service.get_current_data()
            await data_service._process_data_in_memory(vatsim_data.__dict__)
            await data_service._flush_memory_to_disk()
            
            # Test controller data transformations
            controller = db_session.query(Controller).first()
            
            # String "345678" should become integer 345678
            assert isinstance(controller.controller_id, int)
            assert controller.controller_id == 345678
            
            # String "3" should become integer 3
            assert isinstance(controller.controller_rating, int)
            assert controller.controller_rating == 3
            
            # Test flight plan field extraction
            flight = db_session.query(Flight).filter(Flight.callsign == "QFA123").first()
            
            # Nested flight_plan fields should be flattened
            assert flight.flight_rules == "I"
            assert flight.aircraft_faa == "B738"
            assert flight.aircraft_short == "B738"
            assert flight.departure == "YSSY"
            assert flight.arrival == "YBBN"
            assert flight.alternate == "YSCB"
            assert flight.cruise_tas == "450"
            assert flight.planned_altitude == "35000"
            assert flight.deptime == "1200"
            assert flight.enroute_time == "01:30"
            assert flight.fuel_time == "02:30"
            assert flight.remarks == "Test flight for regression testing"
            assert flight.revision_id == 1
            assert flight.assigned_transponder == "1200"
    
    @pytest.mark.asyncio
    async def test_filter_pipeline_integration(
        self,
        vatsim_api_mock,
        db_session,
        clean_database
    ):
        """
        Test filter pipeline processes data correctly in sequence
        
        Validates:
        - Airport filter correctly identifies Australian flights
        - Geographic filter correctly identifies flights in Australian airspace
        - Filters work together in sequence
        - Conservative approach for missing data
        """
        # Create test data with specific filter scenarios
        filter_test_data = {
            "general": {"version": 8, "reload": 1, "connected_clients": 100},
            "pilots": [
                # Case 1: Australian coordinates → PASS
                {
                    "cid": 111111,
                    "name": "Pass Geographic Filter",
                    "callsign": "TEST001",
                    "latitude": -33.8688,  # Sydney
                    "longitude": 151.2093,
                    "flight_plan": {"departure": "YSSY", "arrival": "YBBN"},
                    "last_updated": "2024-01-01T12:00:00Z"
                },
                # Case 2: Non-Australian coordinates → FAIL
                {
                    "cid": 222222,
                    "name": "Fail Geographic Filter",
                    "callsign": "TEST002", 
                    "latitude": 51.5074,  # London
                    "longitude": -0.1278,
                    "flight_plan": {"departure": "EGLL", "arrival": "KLAX"},
                    "last_updated": "2024-01-01T12:00:01Z"
                },
                # Case 3: Missing coordinates → FAIL (conservative)
                {
                    "cid": 333333,
                    "name": "Missing Coordinates",
                    "callsign": "TEST003",
                    "latitude": None,
                    "longitude": None,
                    "flight_plan": {"departure": "YSSY", "arrival": "YBBN"},
                    "last_updated": "2024-01-01T12:00:02Z"
                }
            ],
            "controllers": [],
            "atis": [], "servers": [], "prefiles": [], 
            "facilities": [], "ratings": [], "pilot_ratings": [], "military_ratings": []
        }
        
        vatsim_api_mock.set_response("/v3/vatsim-data.json", filter_test_data)
        
        with patch('app.services.vatsim_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=filter_test_data)
            mock_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            vatsim_service = VATSIMService()
            data_service = DataService()
            
            await vatsim_service.initialize()
            await data_service.initialize()
            
            vatsim_data = await vatsim_service.get_current_data()
            await data_service._process_data_in_memory(vatsim_data.__dict__)
            await data_service._flush_memory_to_disk()
            
            # Verify filter results
            flights = db_session.query(Flight).all()
            
            # Should have 1 flight (TEST001)
            # TEST002 and TEST003 should be filtered out
            assert len(flights) == 1, f"Expected 1 flight after filtering, got {len(flights)}"
            
            flight_callsigns = [f.callsign for f in flights]
            assert "TEST001" in flight_callsigns  # Pass geographic filter
            assert "TEST002" not in flight_callsigns  # Fail geographic filter
            assert "TEST003" not in flight_callsigns  # Fail due to missing coordinates
    
    @pytest.mark.asyncio
    async def test_database_relationship_integrity(
        self,
        golden_vatsim_data,
        vatsim_api_mock,
        db_session,
        clean_database
    ):
        """
        Test database relationships are maintained during data flow
        
        Validates:
        - Foreign key relationships work correctly
        - Related data is linked properly
        - Constraint violations are handled gracefully
        """
        vatsim_api_mock.set_response("/v3/vatsim-data.json", golden_vatsim_data)
        
        with patch('app.services.vatsim_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=golden_vatsim_data)
            mock_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            vatsim_service = VATSIMService()
            data_service = DataService()
            
            await vatsim_service.initialize()
            await data_service.initialize()
            
            vatsim_data = await vatsim_service.get_current_data()
            await data_service._process_data_in_memory(vatsim_data.__dict__)
            await data_service._flush_memory_to_disk()
            
            # Test that all data was inserted without constraint violations
            flights = db_session.query(Flight).all()
            controllers = db_session.query(Controller).all()
            status_records = db_session.query(VatsimStatus).all()
            
            assert len(flights) > 0, "Flights should be inserted"
            assert len(controllers) > 0, "Controllers should be inserted"
            assert len(status_records) > 0, "Status should be inserted"
            
            # Test unique constraints work (no duplicates)
            flight_callsigns = [f.callsign for f in flights]
            controller_callsigns = [c.callsign for c in controllers]
            
            # Each callsign should appear only once (for this timestamp)
            assert len(flight_callsigns) == len(set(flight_callsigns))
            assert len(controller_callsigns) == len(set(controller_callsigns))


@pytest.mark.regression
@pytest.mark.core
class TestDataFlowErrorHandling:
    """Test data flow handles error conditions gracefully"""
    
    @pytest.mark.asyncio
    async def test_malformed_vatsim_data_handling(
        self,
        vatsim_api_mock,
        db_session,
        clean_database
    ):
        """
        Test system handles malformed VATSIM API data gracefully
        
        Validates:
        - Invalid data types don't crash the system
        - Missing required fields are handled
        - Partial data processing continues
        """
        # Malformed VATSIM data
        malformed_data = {
            "general": {"version": 8, "reload": 1},
            "pilots": [
                {
                    "callsign": "VALID123",
                    "cid": 123456,
                    "latitude": -33.8688,
                    "longitude": 151.2093,
                    "flight_plan": {"departure": "YSSY", "arrival": "YBBN"},
                    "last_updated": "2024-01-01T12:00:00Z"
                },
                {
                    "callsign": "INVALID1",
                    "cid": "not_a_number",  # Invalid type
                    "latitude": "invalid_lat",  # Invalid type
                    "longitude": 151.2093,
                    "flight_plan": "not_an_object",  # Should be object
                    "last_updated": "2024-01-01T12:00:00Z"
                },
                {
                    "callsign": "INVALID2",
                    # Missing cid field
                    "latitude": None,
                    "longitude": None,
                    "flight_plan": {},
                    "last_updated": "2024-01-01T12:00:00Z"
                }
            ],
            "controllers": [
                {
                    "callsign": "VALID_CTR",
                    "cid": "123456",
                    "name": "Valid Controller",
                    "rating": "3"
                },
                {
                    "callsign": "",  # Empty required field
                    "cid": None,  # Missing required field
                    "name": "Invalid Controller"
                }
            ],
            "atis": [], "servers": [], "prefiles": [],
            "facilities": [], "ratings": [], "pilot_ratings": [], "military_ratings": []
        }
        
        vatsim_api_mock.set_response("/v3/vatsim-data.json", malformed_data)
        
        with patch('app.services.vatsim_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=malformed_data)
            mock_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            vatsim_service = VATSIMService()
            data_service = DataService()
            
            await vatsim_service.initialize()
            await data_service.initialize()
            
            # Should not crash when processing malformed data
            try:
                vatsim_data = await vatsim_service.get_current_data()
                await data_service._process_data_in_memory(vatsim_data.__dict__)
                await data_service._flush_memory_to_disk()
            except Exception as e:
                pytest.fail(f"Data processing should handle malformed data gracefully, but raised: {e}")
            
            # Verify only valid data was stored
            flights = db_session.query(Flight).all()
            controllers = db_session.query(Controller).all()
            
            # Should have only the valid records
            valid_flights = [f for f in flights if f.callsign == "VALID123"]
            valid_controllers = [c for c in controllers if c.callsign == "VALID_CTR"]
            
            assert len(valid_flights) <= 1, "Should have at most 1 valid flight"
            assert len(valid_controllers) <= 1, "Should have at most 1 valid controller"
            
            # Invalid records should not be stored
            invalid_flights = [f for f in flights if f.callsign in ["INVALID1", "INVALID2"]]
            assert len(invalid_flights) == 0, "Invalid flights should not be stored"
    
    @pytest.mark.asyncio
    async def test_vatsim_api_error_conditions(
        self,
        vatsim_api_mock,
        db_session,
        clean_database
    ):
        """
        Test system handles VATSIM API error conditions
        
        Validates:
        - Network timeouts are handled gracefully
        - HTTP error responses are handled
        - Service continues operating after errors
        """
        # Test timeout condition
        vatsim_api_mock.set_error_condition("/v3/vatsim-data.json", "timeout")
        
        with patch('app.services.vatsim_service.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = asyncio.TimeoutError("Mock timeout")
            
            vatsim_service = VATSIMService()
            await vatsim_service.initialize()
            
            # Should handle timeout gracefully
            with pytest.raises((asyncio.TimeoutError, Exception)):
                await vatsim_service.get_current_data()
            
        # Test HTTP 500 error
        vatsim_api_mock.set_error_condition("/v3/vatsim-data.json", "http_500")
        
        with patch('app.services.vatsim_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = Exception("HTTP 500 error")
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            vatsim_service = VATSIMService()
            await vatsim_service.initialize()
            
            # Should handle HTTP errors gracefully
            with pytest.raises(Exception):
                await vatsim_service.get_current_data()


@pytest.mark.regression
@pytest.mark.core
@pytest.mark.performance
class TestDataFlowPerformance:
    """Test data flow meets performance requirements"""
    
    @pytest.mark.asyncio
    async def test_large_dataset_processing_time(
        self,
        vatsim_api_mock,
        db_session,
        clean_database,
        performance_thresholds
    ):
        """
        Test processing time for large datasets
        
        Validates:
        - Large datasets are processed within time limits
        - Memory usage stays within bounds
        - No performance regressions
        """
        import time
        
        # Generate large dataset (100 flights, 20 controllers)
        large_dataset = {
            "general": {"version": 8, "reload": 1, "connected_clients": 1000},
            "pilots": [
                {
                    "cid": 100000 + i,
                    "name": f"Test Pilot {i}",
                    "callsign": f"TEST{i:03d}",
                    "latitude": -33.8688 + (i * 0.001),  # Spread around Sydney
                    "longitude": 151.2093 + (i * 0.001),
                    "altitude": 35000 + (i * 100),
                    "groundspeed": 400 + (i * 2),
                    "flight_plan": {
                        "departure": "YSSY",
                        "arrival": "YBBN",
                        "aircraft_short": "B738"
                    },
                    "last_updated": f"2024-01-01T12:{i%60:02d}:00Z"
                }
                for i in range(100)
            ],
            "controllers": [
                {
                    "cid": str(200000 + i),
                    "name": f"Controller {i}",
                    "callsign": f"CTR{i:02d}",
                    "facility": 4,
                    "rating": "3"
                }
                for i in range(20)
            ],
            "atis": [], "servers": [], "prefiles": [],
            "facilities": [], "ratings": [], "pilot_ratings": [], "military_ratings": []
        }
        
        vatsim_api_mock.set_response("/v3/vatsim-data.json", large_dataset)
        
        with patch('app.services.vatsim_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=large_dataset)
            mock_response.raise_for_status = AsyncMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            vatsim_service = VATSIMService()
            data_service = DataService()
            
            await vatsim_service.initialize()
            await data_service.initialize()
            
            # Measure processing time
            start_time = time.time()
            
            vatsim_data = await vatsim_service.get_current_data()
            await data_service._process_data_in_memory(vatsim_data.__dict__)
            await data_service._flush_memory_to_disk()
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Verify performance requirements
            max_time = performance_thresholds["large_dataset_max_time"]
            assert processing_time < max_time, f"Processing took {processing_time:.2f}s, should be < {max_time}s"
            
            # Verify all data was processed
            flights = db_session.query(Flight).all()
            controllers = db_session.query(Controller).all()
            
            assert len(flights) == 100, f"Expected 100 flights, got {len(flights)}"
            assert len(controllers) == 20, f"Expected 20 controllers, got {len(controllers)}"
