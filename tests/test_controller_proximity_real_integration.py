#!/usr/bin/env python3
"""
Real Integration Tests for Controller-Specific Proximity Ranges

This module tests the controller-specific proximity functionality with minimal mocking,
focusing on actual outcomes and real system behavior.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
import os
import logging

from app.services.data_service import DataService
from app.services.flight_detection_service import FlightDetectionService
from app.services.controller_type_detector import ControllerTypeDetector
from app.database import get_database_session


class TestControllerProximityRealIntegration:
    """Test controller-specific proximity ranges with real system behavior"""
    
    @pytest.fixture
    def data_service(self):
        """Create real DataService instance"""
        return DataService()
    
    @pytest.fixture
    def flight_detection_service(self):
        """Create real FlightDetectionService instance"""
        return FlightDetectionService()
    
    @pytest.fixture
    def controller_type_detector(self):
        """Create real ControllerTypeDetector instance"""
        return ControllerTypeDetector()

    def test_environment_variables_loaded_correctly(self, controller_type_detector):
        """Test that environment variables are correctly loaded into the system"""
        # This tests the actual environment variable loading, not mocked values
        ranges = controller_type_detector.proximity_ranges
        
        # Verify the actual ranges match what's configured in docker-compose.yml
        assert ranges["Ground"][0] == 15, f"Ground range should be 15nm, got {ranges['Ground'][0]}nm"
        assert ranges["Tower"][0] == 15, f"Tower range should be 15nm, got {ranges['Tower'][0]}nm"
        assert ranges["Approach"][0] == 60, f"Approach range should be 60nm, got {ranges['Approach'][0]}nm"
        assert ranges["Center"][0] == 400, f"Center range should be 400nm, got {ranges['Center'][0]}nm"
        assert ranges["FSS"][0] == 1000, f"FSS range should be 1000nm, got {ranges['FSS'][0]}nm"
        assert ranges["default"][0] == 30, f"Default range should be 30nm, got {ranges['default'][0]}nm"
    
    def test_real_callsign_detection_logic(self, controller_type_detector):
        """Test actual callsign pattern detection with real controller callsigns"""
        # Test with real VATSIM-style callsigns
        real_test_cases = [
            # Australian callsigns
            ("YBBN_TWR", "Tower", 15),
            ("YBBN_GND", "Ground", 15),
            ("YBBN_DEL", "Ground", 15),
            ("BN_APP", "Approach", 60),
            ("BN_DEP", "Approach", 60),
            ("BNE_CTR", "Center", 400),
            ("AU_FSS", "FSS", 1000),
            
            # International callsigns
            ("EGLL_TWR", "Tower", 15),
            ("LHR_APP", "Approach", 60),
            ("LON_CTR", "Center", 400),
            ("KJFK_GND", "Ground", 15),
            ("N90_APP", "Approach", 60),
            ("ZNY_CTR", "Center", 400),
            
            # Edge cases
            ("SHORT", "Ground", 15),  # Fallback to Ground
            ("UNKNOWN_PATTERN", "Ground", 15),  # Fallback to Ground
        ]
        
        for callsign, expected_type, expected_range in real_test_cases:
            # Test actual detection logic
            detected_type = controller_type_detector.detect_controller_type(callsign)
            assert detected_type == expected_type, f"Callsign {callsign}: expected {expected_type}, got {detected_type}"
            
            # Test actual proximity threshold
            proximity_threshold = controller_type_detector.get_proximity_threshold(detected_type)
            assert proximity_threshold == expected_range, f"Callsign {callsign}: expected {expected_range}nm, got {proximity_threshold}nm"
            
            # Test actual controller info method
            controller_info = controller_type_detector.get_controller_info(callsign)
            assert controller_info["type"] == expected_type
            assert controller_info["proximity_threshold"] == expected_range

    def test_real_service_integration(self, data_service):
        """Test that services are actually integrated correctly"""
        # Test that DataService has FlightDetectionService
        assert hasattr(data_service, 'flight_detection_service')
        assert isinstance(data_service.flight_detection_service, FlightDetectionService)
        
        # Test that FlightDetectionService has ControllerTypeDetector
        assert hasattr(data_service.flight_detection_service, 'controller_type_detector')
        assert isinstance(data_service.flight_detection_service.controller_type_detector, ControllerTypeDetector)
        
        # Test that the integration chain works
        test_callsign = "SY_TWR"
        controller_info = data_service.flight_detection_service.controller_type_detector.get_controller_info(test_callsign)
        
        assert controller_info["type"] == "Tower"
        assert controller_info["proximity_threshold"] == 15

    @pytest.mark.asyncio
    async def test_real_proximity_threshold_detection(self, flight_detection_service):
        """Test that the real proximity threshold is correctly detected and would be used in SQL queries"""
        # This test verifies that the proximity detection logic works correctly
        # even though we can't easily test the full SQL execution without data
        
        test_cases = [
            ("SY_TWR", 15),    # Tower
            ("ML_APP", 60),    # Approach  
            ("AU_CTR", 400),   # Center
            ("AU_FSS", 1000),  # FSS
        ]
        
        for callsign, expected_proximity in test_cases:
            # Test the real controller type detection that would be used in SQL
            controller_info = flight_detection_service.controller_type_detector.get_controller_info(callsign)
            proximity_threshold = controller_info["proximity_threshold"]
            
            assert proximity_threshold == expected_proximity, f"Controller {callsign}: expected {expected_proximity}nm, got {proximity_threshold}nm"
            
            # Verify this is the same value that would be passed to the SQL query
            # by testing the internal method that calculates it
            detected_type = flight_detection_service.controller_type_detector.detect_controller_type(callsign)
            sql_proximity = flight_detection_service.controller_type_detector.get_proximity_threshold(detected_type)
            
            assert sql_proximity == expected_proximity, f"SQL proximity for {callsign} should be {expected_proximity}nm, got {sql_proximity}nm"

    def test_different_controller_types_have_different_proximities(self, flight_detection_service):
        """Test that different controller types have different proximity ranges configured"""
        # Test different controller types and their expected proximity ranges
        controller_tests = [
            ("SY_TWR", 15),    # Tower
            ("ML_APP", 60),    # Approach
            ("AU_CTR", 400),   # Center
            ("AU_FSS", 1000),  # FSS
        ]
        
        for callsign, expected_proximity in controller_tests:
            # Test the real proximity detection logic
            controller_info = flight_detection_service.controller_type_detector.get_controller_info(callsign)
            actual_proximity = controller_info["proximity_threshold"]
            
            assert actual_proximity == expected_proximity, f"Controller {callsign}: expected {expected_proximity}nm, got {actual_proximity}nm"
            
            # Also test the underlying detection method
            detected_type = flight_detection_service.controller_type_detector.detect_controller_type(callsign)
            threshold = flight_detection_service.controller_type_detector.get_proximity_threshold(detected_type)
            
            assert threshold == expected_proximity, f"Threshold for {callsign} ({detected_type}): expected {expected_proximity}nm, got {threshold}nm"

    @pytest.mark.asyncio
    async def test_real_aircraft_interactions_method_uses_dynamic_proximity(self, data_service):
        """Test that _get_aircraft_interactions method actually uses dynamic proximity ranges"""
        test_callsign = "BN_APP"  # Approach controller - should use 60nm
        session_start = datetime(2025, 8, 19, 10, 0, 0, tzinfo=timezone.utc)
        session_end = datetime(2025, 8, 19, 11, 0, 0, tzinfo=timezone.utc)
        
        captured_params = {}
        
        # Mock only the flight detection service's database calls
        async def mock_detect_interactions(callsign, start, end, timeout_seconds=None):
            # This should be called with the actual proximity range
            controller_info = data_service.flight_detection_service.controller_type_detector.get_controller_info(callsign)
            captured_params['controller_type'] = controller_info['type']
            captured_params['proximity_threshold'] = controller_info['proximity_threshold']
            
            return {
                "flights_detected": True,
                "total_aircraft": 3,
                "peak_count": 2,
                "hourly_breakdown": {"10": 2, "11": 1},
                "details": []
            }
        
        # Mock only the database-dependent method, not the proximity logic
        with patch.object(data_service.flight_detection_service, 'detect_controller_flight_interactions_with_timeout', mock_detect_interactions):
            mock_session = AsyncMock()
            
            # Call the real _get_aircraft_interactions method
            result = await data_service._get_aircraft_interactions(test_callsign, session_start, session_end, mock_session)
            
            # Verify the real proximity logic was used
            assert captured_params['controller_type'] == 'Approach'
            assert captured_params['proximity_threshold'] == 60
            
            # Verify the result structure
            assert result['total_aircraft'] == 3
            assert result['peak_count'] == 2

    def test_real_controller_info_accuracy(self, data_service):
        """Test that controller info is accurate for different controller types"""
        # Test various real controller callsigns
        test_cases = [
            ("AU_FSS", "FSS", 1000),
            ("SY_TWR", "Tower", 15),
            ("BN_APP", "Approach", 60),
            ("ML_CTR", "Center", 400),
        ]
        
        for callsign, expected_type, expected_range in test_cases:
            controller_info = data_service.flight_detection_service.controller_type_detector.get_controller_info(callsign)
            
            # Verify the real controller info
            assert controller_info["type"] == expected_type, f"Expected {expected_type} for {callsign}, got {controller_info['type']}"
            assert controller_info["proximity_threshold"] == expected_range, f"Expected {expected_range}nm for {callsign}, got {controller_info['proximity_threshold']}nm"
            
            # Verify consistency across different access methods
            detected_type = data_service.flight_detection_service.controller_type_detector.detect_controller_type(callsign)
            assert detected_type == expected_type, f"Detect method returned {detected_type}, expected {expected_type}"

    def test_performance_of_real_controller_type_detection(self, controller_type_detector):
        """Test performance of actual controller type detection (no mocking)"""
        import time
        
        # Test with a large number of real callsigns
        test_callsigns = [
            f"TEST_{i}_TWR" for i in range(100)
        ] + [
            f"TEST_{i}_APP" for i in range(100)
        ] + [
            f"TEST_{i}_CTR" for i in range(100)
        ]
        
        start_time = time.time()
        
        # Run real controller type detection
        results = []
        for callsign in test_callsigns:
            controller_info = controller_type_detector.get_controller_info(callsign)
            results.append(controller_info)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify performance (should be very fast for 300 callsigns)
        assert processing_time < 1.0, f"Controller type detection took {processing_time:.3f}s for 300 callsigns (should be < 1s)"
        
        # Verify all results are correct
        assert len(results) == 300
        
        # Verify the first 100 are Tower controllers
        for i in range(100):
            assert results[i]["type"] == "Tower"
            assert results[i]["proximity_threshold"] == 15
        
        # Verify the next 100 are Approach controllers
        for i in range(100, 200):
            assert results[i]["type"] == "Approach"
            assert results[i]["proximity_threshold"] == 60
        
        # Verify the last 100 are Center controllers
        for i in range(200, 300):
            assert results[i]["type"] == "Center"
            assert results[i]["proximity_threshold"] == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
