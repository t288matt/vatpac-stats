"""
Unit tests for GeographicBoundaryFilter.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch, mock_open
from pathlib import Path

from app.filters.geographic_boundary_filter import GeographicBoundaryFilter, GeographicBoundaryConfig


class TestGeographicBoundaryFilter:
    """Test cases for GeographicBoundaryFilter."""

    @pytest.fixture
    def sample_geojson_data(self):
        """Sample GeoJSON polygon data for testing."""
        return {
            "type": "Polygon",
            "coordinates": [[
                [151.0, -33.0],  # lon, lat format for GeoJSON
                [152.0, -33.0],
                [152.0, -34.0],
                [151.0, -34.0],
                [151.0, -33.0]
            ]]
        }

    @pytest.fixture
    def sample_flight_data(self):
        """Sample flight data for testing."""
        return [
            {
                "callsign": "QFA77",
                "latitude": -33.5,  # Inside polygon
                "longitude": 151.5,
                "altitude": 35000
            },
            {
                "callsign": "BAW15",
                "latitude": 51.5,   # Outside polygon
                "longitude": -0.1,
                "altitude": 39000
            },
            {
                "callsign": "NOPOS",  # No position data
                "altitude": 30000
            }
        ]

    @pytest.fixture
    def temp_geojson_file(self, sample_geojson_data):
        """Create a temporary GeoJSON file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_geojson_data, f)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    def setup_method(self):
        """Setup before each test."""
        # Clear environment variables
        env_vars = ["ENABLE_BOUNDARY_FILTER", "BOUNDARY_DATA_PATH", 
                   "BOUNDARY_FILTER_LOG_LEVEL", "BOUNDARY_FILTER_PERFORMANCE_THRESHOLD"]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

    # Test Configuration
    def test_config_default_values(self):
        """Test default configuration values."""
        filter_instance = GeographicBoundaryFilter()
        config = filter_instance.config
        
        assert config.enabled is False
        assert config.boundary_data_path == ""
        assert config.log_level == "INFO"
        assert config.performance_threshold_ms == 10.0

    def test_config_from_environment(self):
        """Test configuration loading from environment variables."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = "/path/to/boundary.json"
        os.environ["BOUNDARY_FILTER_LOG_LEVEL"] = "DEBUG"
        os.environ["BOUNDARY_FILTER_PERFORMANCE_THRESHOLD"] = "5.0"
        
        filter_instance = GeographicBoundaryFilter()
        config = filter_instance.config
        
        assert config.enabled is True
        assert config.boundary_data_path == "/path/to/boundary.json"
        assert config.log_level == "DEBUG"
        assert config.performance_threshold_ms == 5.0

    # Test Initialization
    def test_initialization_disabled(self):
        """Test filter initialization when disabled."""
        filter_instance = GeographicBoundaryFilter()
        
        assert filter_instance.config.enabled is False
        assert filter_instance.is_initialized is False
        assert filter_instance.polygon is None

    def test_initialization_enabled_no_file(self):
        """Test filter initialization when enabled but no boundary file."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        
        filter_instance = GeographicBoundaryFilter()
        
        assert filter_instance.config.enabled is True
        assert filter_instance.is_initialized is False

    def test_initialization_enabled_invalid_file(self):
        """Test filter initialization with invalid boundary file."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = "nonexistent.json"
        
        filter_instance = GeographicBoundaryFilter()
        
        assert filter_instance.config.enabled is True
        assert filter_instance.is_initialized is False

    def test_initialization_enabled_valid_file(self, temp_geojson_file):
        """Test filter initialization with valid boundary file."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        filter_instance = GeographicBoundaryFilter()
        
        assert filter_instance.config.enabled is True
        assert filter_instance.is_initialized is True
        assert filter_instance.polygon is not None

    # Test Flight Filtering
    def test_filter_flights_list_disabled(self, sample_flight_data):
        """Test flight filtering when filter is disabled."""
        filter_instance = GeographicBoundaryFilter()
        
        result = filter_instance.filter_flights_list(sample_flight_data)
        
        assert len(result) == len(sample_flight_data)
        assert result == sample_flight_data

    def test_filter_flights_list_empty(self, temp_geojson_file):
        """Test flight filtering with empty flight list."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        filter_instance = GeographicBoundaryFilter()
        result = filter_instance.filter_flights_list([])
        
        assert result == []

    def test_filter_flights_list_enabled(self, temp_geojson_file, sample_flight_data):
        """Test flight filtering when filter is enabled."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        filter_instance = GeographicBoundaryFilter()
        result = filter_instance.filter_flights_list(sample_flight_data)
        
        # Should include QFA77 (inside) and NOPOS (no position, allowed through)
        # Should exclude BAW15 (outside)
        assert len(result) == 2
        callsigns = [f.get('callsign') for f in result]
        assert 'QFA77' in callsigns
        assert 'NOPOS' in callsigns
        assert 'BAW15' not in callsigns

    def test_filter_vatsim_data_structure(self, temp_geojson_file, sample_flight_data):
        """Test filtering of complete VATSIM data structure."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        vatsim_data = {
            "pilots": sample_flight_data,
            "controllers": [{"callsign": "SYD_TWR"}],
            "servers": [{"name": "SERVER1"}]
        }
        
        filter_instance = GeographicBoundaryFilter()
        result = filter_instance.filter_vatsim_data(vatsim_data)
        
        # Pilots should be filtered, other data unchanged
        assert len(result["pilots"]) == 2  # QFA77 + NOPOS
        assert len(result["controllers"]) == 1  # Unchanged
        assert len(result["servers"]) == 1  # Unchanged

    # Test Edge Cases
    def test_flight_with_invalid_coordinates(self, temp_geojson_file):
        """Test flight with invalid coordinate data."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        flights = [
            {
                "callsign": "INVALID1",
                "latitude": "not_a_number",
                "longitude": 151.5
            },
            {
                "callsign": "INVALID2", 
                "latitude": -33.5,
                "longitude": "also_invalid"
            }
        ]
        
        filter_instance = GeographicBoundaryFilter()
        result = filter_instance.filter_flights_list(flights)
        
        # Invalid coordinates should be allowed through (conservative approach)
        assert len(result) == 2

    def test_flight_with_partial_coordinates(self, temp_geojson_file):
        """Test flight with partial coordinate data."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        flights = [
            {
                "callsign": "PARTIAL1",
                "latitude": -33.5
                # No longitude
            },
            {
                "callsign": "PARTIAL2",
                "longitude": 151.5
                # No latitude
            }
        ]
        
        filter_instance = GeographicBoundaryFilter()
        result = filter_instance.filter_flights_list(flights)
        
        # Partial coordinates should be allowed through
        assert len(result) == 2

    def test_flight_with_different_coordinate_fields(self, temp_geojson_file):
        """Test flight with different coordinate field names."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        flights = [
            {
                "callsign": "ALT1",
                "lat": -33.5,  # Alternative field name
                "lon": 151.5
            },
            {
                "callsign": "ALT2",
                "latitude": -33.5,
                "lng": 151.5  # Alternative field name
            }
        ]
        
        filter_instance = GeographicBoundaryFilter()
        result = filter_instance.filter_flights_list(flights)
        
        # Should handle alternative field names
        assert len(result) == 2

    # Test Statistics and Performance
    def test_filter_statistics(self, temp_geojson_file, sample_flight_data):
        """Test filter statistics collection."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        filter_instance = GeographicBoundaryFilter()
        filter_instance.filter_flights_list(sample_flight_data)
        
        stats = filter_instance.get_filter_stats()
        
        assert stats["enabled"] is True
        assert stats["initialized"] is True
        assert stats["total_processed"] == 3
        assert stats["flights_included"] == 1  # Only QFA77 has valid inside coordinates
        assert stats["flights_excluded"] == 1  # BAW15 is outside
        assert stats["flights_no_position"] == 1  # NOPOS has no coordinates
        assert "processing_time_ms" in stats
        assert "polygon_points" in stats

    def test_performance_threshold_warning(self, temp_geojson_file, sample_flight_data):
        """Test performance threshold warning."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        os.environ["BOUNDARY_FILTER_PERFORMANCE_THRESHOLD"] = "0.001"  # Very low threshold
        
        filter_instance = GeographicBoundaryFilter()
        
        # This should trigger performance warning (processing will likely exceed 0.001ms)
        result = filter_instance.filter_flights_list(sample_flight_data)
        
        stats = filter_instance.get_filter_stats()
        assert stats["performance_threshold_ms"] == 0.001

    # Test Boundary Information
    def test_get_boundary_info_not_initialized(self):
        """Test getting boundary info when not initialized."""
        filter_instance = GeographicBoundaryFilter()
        
        info = filter_instance.get_boundary_info()
        
        assert info is None

    def test_get_boundary_info_initialized(self, temp_geojson_file):
        """Test getting boundary info when initialized."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        filter_instance = GeographicBoundaryFilter()
        info = filter_instance.get_boundary_info()
        
        assert info is not None
        assert "file_path" in info
        assert "polygon_points" in info
        assert "bounds" in info
        assert info["polygon_points"] == 5  # 4 corners + closing point

    # Test Reload Functionality
    def test_reload_boundary_data(self, temp_geojson_file):
        """Test reloading boundary data."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        filter_instance = GeographicBoundaryFilter()
        assert filter_instance.is_initialized is True
        
        # Reload
        filter_instance.reload_boundary_data()
        assert filter_instance.is_initialized is True

    def test_reload_boundary_data_disabled(self):
        """Test reloading boundary data when filter is disabled."""
        filter_instance = GeographicBoundaryFilter()
        assert filter_instance.is_initialized is False
        
        # Reload should not initialize when disabled
        filter_instance.reload_boundary_data()
        assert filter_instance.is_initialized is False

    # Test Real-world Scenarios
    def test_large_flight_list_performance(self, temp_geojson_file):
        """Test performance with large flight list."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        # Create large flight list
        large_flight_list = []
        for i in range(100):
            large_flight_list.append({
                "callsign": f"TEST{i:03d}",
                "latitude": -33.5 + (i * 0.01),  # Vary positions
                "longitude": 151.5 + (i * 0.01),
                "altitude": 35000
            })
        
        filter_instance = GeographicBoundaryFilter()
        result = filter_instance.filter_flights_list(large_flight_list)
        
        stats = filter_instance.get_filter_stats()
        
        # Should process all flights quickly
        assert stats["total_processed"] == 100
        assert stats["processing_time_ms"] < 100  # Should be much faster than 100ms
        assert len(result) > 0  # Some flights should be inside the test polygon

    def test_mixed_data_quality(self, temp_geojson_file):
        """Test filtering with mixed data quality."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        mixed_flights = [
            {"callsign": "GOOD", "latitude": -33.5, "longitude": 151.5},  # Good data, inside
            {"callsign": "BAD_LAT", "latitude": "invalid", "longitude": 151.5},  # Bad latitude
            {"callsign": "NO_POS"},  # No position at all
            {"callsign": "OUTSIDE", "latitude": 51.5, "longitude": -0.1},  # Good data, outside
            {"callsign": "PARTIAL", "latitude": -33.5},  # Missing longitude
        ]
        
        filter_instance = GeographicBoundaryFilter()
        result = filter_instance.filter_flights_list(mixed_flights)
        
        # Should handle mixed data gracefully
        callsigns = [f.get('callsign') for f in result]
        assert 'GOOD' in callsigns  # Inside polygon
        assert 'BAD_LAT' in callsigns  # Invalid data allowed through
        assert 'NO_POS' in callsigns  # No position allowed through
        assert 'PARTIAL' in callsigns  # Partial data allowed through
        assert 'OUTSIDE' not in callsigns  # Outside polygon excluded

    def test_filter_stats_comprehensive(self, temp_geojson_file):
        """Test comprehensive filter statistics."""
        os.environ["ENABLE_BOUNDARY_FILTER"] = "true"
        os.environ["BOUNDARY_DATA_PATH"] = temp_geojson_file
        
        filter_instance = GeographicBoundaryFilter()
        stats = filter_instance.get_filter_stats()
        
        # Check all expected fields
        expected_fields = [
            "enabled", "initialized", "log_level", "performance_threshold_ms",
            "filter_type", "inclusion_criteria", "validation_method", 
            "conservative_approach", "polygon_points", "polygon_bounds",
            "boundary_file", "total_processed", "flights_included", 
            "flights_excluded", "flights_no_position", "processing_time_ms"
        ]
        
        for field in expected_fields:
            assert field in stats
