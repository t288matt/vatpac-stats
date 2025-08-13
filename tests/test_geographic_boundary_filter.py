#!/usr/bin/env python3
"""
Comprehensive Tests for Geographic Boundary Filter

Tests the GeographicBoundaryFilter class with various configurations
and edge cases to ensure robust operation.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from shapely.geometry import Polygon

# Import the filter class
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter, GeographicBoundaryConfig


@pytest.mark.unit
@pytest.mark.geographic
class TestGeographicBoundaryFilter:
    """Test the GeographicBoundaryFilter class"""
    
    def setup_method(self):
        """Setup test environment"""
        # Create a test polygon
        self.test_polygon = Polygon([
            (110.0, -45.0),   # Southwest
            (155.0, -45.0),   # Southeast  
            (155.0, -10.0),   # Northeast
            (110.0, -10.0),   # Northwest
            (110.0, -45.0)    # Close the polygon
        ])
        
        # Create test flight data
        self.test_flight_inside = {
            'callsign': 'TEST001',
            'latitude': -25.0,
            'longitude': 135.0
        }
        
        self.test_flight_outside = {
            'callsign': 'TEST002',
            'latitude': 40.0,
            'longitude': -74.0
        }
        
        self.test_flight_no_position = {
            'callsign': 'TEST003',
            'latitude': None,
            'longitude': None
        }
        
        # Create test transceiver data
        self.test_transceiver_inside = {
            'id': 'T1',
            'position_lat': -33.0,
            'position_lon': 151.0
        }
        
        self.test_transceiver_outside = {
            'id': 'T2',
            'position_lat': 51.0,
            'position_lon': 0.0
        }
        
        # Create test controller data
        self.test_controller = {
            'callsign': 'CTRL001',
            'frequency': '118.1'
        }
    
    def test_filter_disabled_initialization(self):
        """Test filter initialization when disabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'false',
            'BOUNDARY_DATA_PATH': 'nonexistent.json'
        }):
            filter_instance = GeographicBoundaryFilter()
            
            assert filter_instance.config.enabled == False
            assert filter_instance.is_initialized == False
            assert filter_instance.polygon is None
    
    def test_filter_enabled_initialization_success(self):
        """Test filter initialization when enabled and polygon loads successfully"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            assert filter_instance.config.enabled == True
            assert filter_instance.is_initialized == True
            assert filter_instance.polygon is not None
            assert len(filter_instance.polygon.exterior.coords) > 0
    
    def test_filter_enabled_initialization_failure_no_path(self):
        """Test filter initialization fails when enabled but no path configured"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': ''
        }):
            with pytest.raises(RuntimeError, match="No boundary data path configured"):
                GeographicBoundaryFilter()
    
    def test_filter_enabled_initialization_failure_invalid_file(self):
        """Test filter initialization fails when enabled but file cannot be loaded"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'invalid.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', side_effect=FileNotFoundError("File not found")):
            with pytest.raises(RuntimeError, match="CRITICAL: Failed to load boundary data"):
                GeographicBoundaryFilter()
    
    def test_filter_disabled_flight_filtering(self):
        """Test that disabled filter allows all flights through"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'false',
            'BOUNDARY_DATA_PATH': 'test.json'
        }):
            filter_instance = GeographicBoundaryFilter()
            
            # All flights should pass through when filter is disabled
            result = filter_instance._is_flight_in_boundary(self.test_flight_inside)
            assert result == True
            
            result = filter_instance._is_flight_in_boundary(self.test_flight_outside)
            assert result == True
            
            result = filter_instance._is_flight_in_boundary(self.test_flight_no_position)
            assert result == True
    
    def test_filter_enabled_flight_filtering_success(self):
        """Test that enabled filter correctly filters flights"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            # Flight inside should be included
            result = filter_instance._is_flight_in_boundary(self.test_flight_inside)
            assert result == True
            
            # Flight outside should be excluded
            result = filter_instance._is_flight_in_boundary(self.test_flight_outside)
            assert result == False
            
            # Flight with no position should be included (default behavior)
            result = filter_instance._is_flight_in_boundary(self.test_flight_no_position)
            assert result == True
    
    def test_filter_enabled_flight_filtering_failure_not_initialized(self):
        """Test that enabled filter fails when not properly initialized"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', side_effect=Exception("Test error")):
            # This should fail during initialization
            with pytest.raises(RuntimeError):
                GeographicBoundaryFilter()
    
    def test_filter_disabled_transceiver_filtering(self):
        """Test that disabled filter allows all transceivers through"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'false',
            'BOUNDARY_DATA_PATH': 'test.json'
        }):
            filter_instance = GeographicBoundaryFilter()
            
            # All transceivers should pass through when filter is disabled
            result = filter_instance._is_transceiver_in_boundary(self.test_transceiver_inside)
            assert result == True
            
            result = filter_instance._is_transceiver_in_boundary(self.test_transceiver_outside)
            assert result == True
    
    def test_filter_enabled_transceiver_filtering_success(self):
        """Test that enabled filter correctly filters transceivers"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            # Transceiver inside should be included
            result = filter_instance._is_transceiver_in_boundary(self.test_transceiver_inside)
            assert result == True
            
            # Transceiver outside should be excluded
            result = filter_instance._is_transceiver_in_boundary(self.test_transceiver_outside)
            assert result == False
    
    def test_filter_disabled_controller_filtering(self):
        """Test that disabled filter allows all controllers through"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'false',
            'BOUNDARY_DATA_PATH': 'test.json'
        }):
            filter_instance = GeographicBoundaryFilter()
            
            # All controllers should pass through when filter is disabled
            result = filter_instance._is_controller_in_boundary(self.test_controller)
            assert result == True
    
    def test_filter_enabled_controller_filtering_success(self):
        """Test that enabled filter allows all controllers through (no position data)"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            # Controllers should always pass through (no position data)
            result = filter_instance._is_controller_in_boundary(self.test_controller)
            assert result == True
    
    def test_filter_flights_list_disabled(self):
        """Test filtering list of flights when filter is disabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'false',
            'BOUNDARY_DATA_PATH': 'test.json'
        }):
            filter_instance = GeographicBoundaryFilter()
            
            flights = [self.test_flight_inside, self.test_flight_outside, self.test_flight_no_position]
            result = filter_instance.filter_flights_list(flights)
            
            # All flights should pass through unchanged
            assert len(result) == 3
            assert result == flights
    
    def test_filter_flights_list_enabled(self):
        """Test filtering list of flights when filter is enabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            flights = [self.test_flight_inside, self.test_flight_outside, self.test_flight_no_position]
            result = filter_instance.filter_flights_list(flights)
            
            # Only inside flights and no-position flights should pass through
            assert len(result) == 2
            assert self.test_flight_inside in result
            assert self.test_flight_no_position in result
            assert self.test_flight_outside not in result
    
    def test_filter_transceivers_list_enabled(self):
        """Test filtering list of transceivers when filter is enabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            transceivers = [self.test_transceiver_inside, self.test_transceiver_outside]
            result = filter_instance.filter_transceivers_list(transceivers)
            
            # Only inside transceivers should pass through
            assert len(result) == 1
            assert self.test_transceiver_inside in result
            assert self.test_transceiver_outside not in result
    
    def test_filter_controllers_list_enabled(self):
        """Test filtering list of controllers when filter is enabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            controllers = [self.test_controller]
            result = filter_instance.filter_controllers_list(controllers)
            
            # All controllers should pass through (no position data)
            assert len(result) == 1
            assert self.test_controller in result
    
    def test_filter_vatsim_data_disabled(self):
        """Test filtering VATSIM data when filter is disabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'false',
            'BOUNDARY_DATA_PATH': 'test.json'
        }):
            filter_instance = GeographicBoundaryFilter()
            
            vatsim_data = {
                'pilots': [self.test_flight_inside, self.test_flight_outside],
                'controllers': [self.test_controller]
            }
            
            result = filter_instance.filter_vatsim_data(vatsim_data)
            
            # Data should pass through unchanged
            assert result == vatsim_data
    
    def test_filter_vatsim_data_enabled(self):
        """Test filtering VATSIM data when filter is enabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            vatsim_data = {
                'pilots': [self.test_flight_inside, self.test_flight_outside],
                'controllers': [self.test_controller]
            }
            
            result = filter_instance.filter_vatsim_data(vatsim_data)
            
            # Only inside flights should pass through
            assert len(result['pilots']) == 1
            assert self.test_flight_inside in result['pilots']
            assert self.test_flight_outside not in result['pilots']
            assert result['controllers'] == vatsim_data['controllers']
    
    def test_get_filter_status_disabled(self):
        """Test filter status when filter is disabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'false',
            'BOUNDARY_DATA_PATH': 'test.json'
        }):
            filter_instance = GeographicBoundaryFilter()
            
            status = filter_instance.get_filter_status()
            
            assert status['enabled'] == False
            assert status['initialized'] == False
            assert status['polygon_loaded'] == False
            assert status['polygon_points'] == 0
            assert status['configuration_valid'] == False
            assert 'status' in status
            assert 'Filter is disabled' in status['status']
    
    def test_get_filter_status_enabled_success(self):
        """Test filter status when filter is enabled and working"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            status = filter_instance.get_filter_status()
            
            assert status['enabled'] == True
            assert status['initialized'] == True
            assert status['polygon_loaded'] == True
            assert status['polygon_points'] > 0
            assert status['configuration_valid'] == True
            assert 'error' not in status
            assert 'status' not in status
    
    def test_get_filter_stats(self):
        """Test filter statistics"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            # Process some flights to generate stats
            flights = [self.test_flight_inside, self.test_flight_outside]
            filter_instance.filter_flights_list(flights)
            
            stats = filter_instance.get_filter_stats()
            
            assert stats['enabled'] == True
            assert stats['initialized'] == True
            assert stats['total_processed'] == 2
            assert stats['flights_included'] == 1
            assert stats['flights_excluded'] == 1
            assert 'polygon_points' in stats
            assert 'boundary_file' in stats
    
    def test_reload_boundary_data_disabled(self):
        """Test reloading boundary data when filter is disabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'false',
            'BOUNDARY_DATA_PATH': 'test.json'
        }):
            filter_instance = GeographicBoundaryFilter()
            
            # Should not fail, just log and continue
            filter_instance.reload_boundary_data()
            
            assert filter_instance.is_initialized == False
            assert filter_instance.polygon is None
    
    def test_reload_boundary_data_enabled(self):
        """Test reloading boundary data when filter is enabled"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            # Reload should work
            filter_instance.reload_boundary_data()
            
            assert filter_instance.is_initialized == True
            assert filter_instance.polygon is not None
    
    def test_get_boundary_info_not_initialized(self):
        """Test getting boundary info when not initialized"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'false',
            'BOUNDARY_DATA_PATH': 'test.json'
        }):
            filter_instance = GeographicBoundaryFilter()
            
            info = filter_instance.get_boundary_info()
            
            assert info is None
    
    def test_get_boundary_info_initialized(self):
        """Test getting boundary info when initialized"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            info = filter_instance.get_boundary_info()
            
            assert info is not None
            assert 'file_path' in info
            assert 'polygon_points' in info
            assert 'area_sq_degrees' in info
            assert 'is_valid' in info
            assert info['is_valid'] == True
    
    def test_edge_case_empty_flights_list(self):
        """Test filtering empty list of flights"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            result = filter_instance.filter_flights_list([])
            
            assert result == []
    
    def test_edge_case_none_flights_list(self):
        """Test filtering None list of flights"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            result = filter_instance.filter_flights_list(None)
            
            assert result == []
    
    def test_edge_case_invalid_coordinates(self):
        """Test handling of invalid coordinate data"""
        with patch.dict(os.environ, {
            'ENABLE_BOUNDARY_FILTER': 'true',
            'BOUNDARY_DATA_PATH': 'test.json'
        }), patch('app.filters.geographic_boundary_filter.get_cached_polygon', return_value=self.test_polygon):
            filter_instance = GeographicBoundaryFilter()
            
            # Test with invalid coordinate types
            invalid_flight = {
                'callsign': 'INVALID',
                'latitude': 'not_a_number',
                'longitude': 'also_not_a_number'
            }
            
            # Should handle gracefully and return True (include)
            result = filter_instance._is_flight_in_boundary(invalid_flight)
            assert result == True


@pytest.mark.unit
@pytest.mark.geographic
class TestGeographicBoundaryConfig:
    """Test the GeographicBoundaryConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = GeographicBoundaryConfig()
        
        assert config.enabled == False
        assert config.boundary_data_path == ""
        assert config.log_level == "INFO"
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = GeographicBoundaryConfig(
            enabled=True,
            boundary_data_path="/path/to/file.json",
            log_level="DEBUG"
        )
        
        assert config.enabled == True
        assert config.boundary_data_path == "/path/to/file.json"
        assert config.log_level == "DEBUG"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
