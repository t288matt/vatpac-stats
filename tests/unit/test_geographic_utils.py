"""
Unit tests for geographic utilities module.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open
from shapely.geometry import Polygon, Point

from app.utils.geographic_utils import (
    load_polygon_from_geojson,
    is_point_in_polygon,
    is_point_in_polygon_from_coords,
    validate_polygon_coordinates,
    validate_geojson_polygon,
    get_polygon_bounds,
    create_polygon_from_geojson_dict,
    get_cached_polygon,
    clear_polygon_cache
)


class TestGeographicUtils:
    """Test cases for geographic utilities."""

    @pytest.fixture
    def simple_polygon_coords(self):
        """Simple rectangular polygon for testing."""
        return [
            (-33.0, 151.0),  # Sydney area
            (-33.0, 152.0),
            (-34.0, 152.0),
            (-34.0, 151.0),
            (-33.0, 151.0)   # Closed polygon
        ]

    @pytest.fixture
    def geojson_polygon_data(self):
        """Standard GeoJSON polygon data."""
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
    def simple_format_data(self):
        """Simple coordinate format data."""
        return {
            "coordinates": [
                [-33.0, 151.0],  # lat, lon format
                [-33.0, 152.0],
                [-34.0, 152.0],
                [-34.0, 151.0],
                [-33.0, 151.0]
            ]
        }

    @pytest.fixture
    def temp_geojson_file(self, geojson_polygon_data):
        """Create a temporary GeoJSON file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(geojson_polygon_data, f)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    @pytest.fixture
    def temp_simple_file(self, simple_format_data):
        """Create a temporary simple format file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(simple_format_data, f)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    def setup_method(self):
        """Clear cache before each test."""
        clear_polygon_cache()

    # Test load_polygon_from_geojson
    def test_load_polygon_from_geojson_standard_format(self, temp_geojson_file):
        """Test loading standard GeoJSON format."""
        polygon = load_polygon_from_geojson(temp_geojson_file)
        
        assert isinstance(polygon, Polygon)
        assert polygon.is_valid
        assert len(polygon.exterior.coords) == 5  # 4 corners + closing point

    def test_load_polygon_from_geojson_simple_format(self, temp_simple_file):
        """Test loading simple coordinate format."""
        polygon = load_polygon_from_geojson(temp_simple_file)
        
        assert isinstance(polygon, Polygon)
        assert polygon.is_valid
        assert len(polygon.exterior.coords) == 5

    def test_load_polygon_file_not_found(self):
        """Test handling of non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_polygon_from_geojson("nonexistent_file.json")

    def test_load_polygon_invalid_json(self):
        """Test handling of invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid JSON format"):
                load_polygon_from_geojson(temp_file)
        finally:
            os.unlink(temp_file)

    def test_load_polygon_missing_coordinates(self):
        """Test handling of JSON without coordinates."""
        data = {"type": "Polygon", "other_field": "value"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError, match="must contain 'coordinates' key"):
                load_polygon_from_geojson(temp_file)
        finally:
            os.unlink(temp_file)

    # Test is_point_in_polygon
    def test_is_point_in_polygon_inside(self, simple_polygon_coords):
        """Test point inside polygon."""
        polygon = Polygon([(coord[1], coord[0]) for coord in simple_polygon_coords])
        
        # Point inside the polygon
        result = is_point_in_polygon(-33.5, 151.5, polygon)
        assert result is True

    def test_is_point_in_polygon_outside(self, simple_polygon_coords):
        """Test point outside polygon."""
        polygon = Polygon([(coord[1], coord[0]) for coord in simple_polygon_coords])
        
        # Point outside the polygon
        result = is_point_in_polygon(-32.0, 151.5, polygon)
        assert result is False

    def test_is_point_in_polygon_invalid_coordinates(self, simple_polygon_coords):
        """Test invalid coordinate handling."""
        polygon = Polygon([(coord[1], coord[0]) for coord in simple_polygon_coords])
        
        # Invalid latitude - should return False (logged as error)
        result = is_point_in_polygon(91.0, 151.5, polygon)
        assert result is False
        
        # Invalid longitude - should return False (logged as error)
        result = is_point_in_polygon(-33.5, 181.0, polygon)
        assert result is False

    def test_is_point_in_polygon_non_numeric(self, simple_polygon_coords):
        """Test non-numeric coordinate handling."""
        polygon = Polygon([(coord[1], coord[0]) for coord in simple_polygon_coords])
        
        # Non-numeric coordinates should return False (logged as error)
        result = is_point_in_polygon("invalid", 151.5, polygon)
        assert result is False

    def test_is_point_in_polygon_invalid_polygon_type(self):
        """Test invalid polygon type handling."""
        # Invalid polygon type should return False (logged as error)
        result = is_point_in_polygon(-33.5, 151.5, "not_a_polygon")
        assert result is False

    # Test is_point_in_polygon_from_coords
    def test_is_point_in_polygon_from_coords_inside(self, simple_polygon_coords):
        """Test point inside polygon using coordinate list."""
        result = is_point_in_polygon_from_coords(-33.5, 151.5, simple_polygon_coords)
        assert result is True

    def test_is_point_in_polygon_from_coords_outside(self, simple_polygon_coords):
        """Test point outside polygon using coordinate list."""
        result = is_point_in_polygon_from_coords(-32.0, 151.5, simple_polygon_coords)
        assert result is False

    def test_is_point_in_polygon_from_coords_insufficient_points(self):
        """Test polygon with insufficient points."""
        coords = [(-33.0, 151.0), (-34.0, 151.0)]  # Only 2 points
        
        # Insufficient points should return False (logged as error)
        result = is_point_in_polygon_from_coords(-33.5, 151.5, coords)
        assert result is False

    # Test validate_polygon_coordinates
    def test_validate_polygon_coordinates_valid(self, simple_polygon_coords):
        """Test validation of valid coordinates."""
        result = validate_polygon_coordinates(simple_polygon_coords)
        assert result is True

    def test_validate_polygon_coordinates_insufficient_points(self):
        """Test validation with insufficient points."""
        coords = [(-33.0, 151.0), (-34.0, 151.0)]
        result = validate_polygon_coordinates(coords)
        assert result is False

    def test_validate_polygon_coordinates_invalid_latitude(self):
        """Test validation with invalid latitude."""
        coords = [(-91.0, 151.0), (-33.0, 152.0), (-34.0, 151.0)]
        result = validate_polygon_coordinates(coords)
        assert result is False

    def test_validate_polygon_coordinates_invalid_longitude(self):
        """Test validation with invalid longitude."""
        coords = [(-33.0, 181.0), (-33.0, 152.0), (-34.0, 151.0)]
        result = validate_polygon_coordinates(coords)
        assert result is False

    def test_validate_polygon_coordinates_non_numeric(self):
        """Test validation with non-numeric coordinates."""
        coords = [("invalid", 151.0), (-33.0, 152.0), (-34.0, 151.0)]
        result = validate_polygon_coordinates(coords)
        assert result is False

    def test_validate_polygon_coordinates_empty_list(self):
        """Test validation with empty coordinate list."""
        result = validate_polygon_coordinates([])
        assert result is False

    def test_validate_polygon_coordinates_none(self):
        """Test validation with None input."""
        result = validate_polygon_coordinates(None)
        assert result is False

    # Test validate_geojson_polygon
    def test_validate_geojson_polygon_valid_geojson(self, temp_geojson_file):
        """Test validation of valid GeoJSON file."""
        result = validate_geojson_polygon(temp_geojson_file)
        assert result is True

    def test_validate_geojson_polygon_valid_simple(self, temp_simple_file):
        """Test validation of valid simple format file."""
        result = validate_geojson_polygon(temp_simple_file)
        assert result is True

    def test_validate_geojson_polygon_file_not_found(self):
        """Test validation of non-existent file."""
        result = validate_geojson_polygon("nonexistent.json")
        assert result is False

    def test_validate_geojson_polygon_invalid_json(self):
        """Test validation of invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json")
            temp_file = f.name
        
        try:
            result = validate_geojson_polygon(temp_file)
            assert result is False
        finally:
            os.unlink(temp_file)

    def test_validate_geojson_polygon_missing_coordinates(self):
        """Test validation of file missing coordinates."""
        data = {"type": "Polygon"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_file = f.name
        
        try:
            result = validate_geojson_polygon(temp_file)
            assert result is False
        finally:
            os.unlink(temp_file)

    # Test get_polygon_bounds
    def test_get_polygon_bounds(self, simple_polygon_coords):
        """Test getting polygon bounds."""
        polygon = Polygon([(coord[1], coord[0]) for coord in simple_polygon_coords])
        bounds = get_polygon_bounds(polygon)
        
        assert isinstance(bounds, dict)
        assert 'min_lat' in bounds
        assert 'max_lat' in bounds
        assert 'min_lon' in bounds
        assert 'max_lon' in bounds
        
        assert bounds['min_lat'] == -34.0
        assert bounds['max_lat'] == -33.0
        assert bounds['min_lon'] == 151.0
        assert bounds['max_lon'] == 152.0

    def test_get_polygon_bounds_invalid_polygon(self):
        """Test bounds calculation with invalid polygon."""
        bounds = get_polygon_bounds("not_a_polygon")
        
        # Should return default bounds on error
        assert bounds == {'min_lat': 0, 'max_lat': 0, 'min_lon': 0, 'max_lon': 0}

    # Test create_polygon_from_geojson_dict
    def test_create_polygon_from_geojson_dict_standard(self, geojson_polygon_data):
        """Test creating polygon from standard GeoJSON dict."""
        polygon = create_polygon_from_geojson_dict(geojson_polygon_data)
        
        assert isinstance(polygon, Polygon)
        assert polygon.is_valid
        assert len(polygon.exterior.coords) == 5

    def test_create_polygon_from_geojson_dict_simple(self, simple_format_data):
        """Test creating polygon from simple format dict."""
        polygon = create_polygon_from_geojson_dict(simple_format_data)
        
        assert isinstance(polygon, Polygon)
        assert polygon.is_valid
        assert len(polygon.exterior.coords) == 5

    def test_create_polygon_from_geojson_dict_no_coordinates(self):
        """Test creating polygon from dict without coordinates."""
        data = {"type": "Polygon"}
        
        with pytest.raises(ValueError, match="Invalid GeoJSON data"):
            create_polygon_from_geojson_dict(data)

    # Test caching functionality
    def test_get_cached_polygon_first_load(self, temp_geojson_file):
        """Test first load of polygon (should cache it)."""
        polygon = get_cached_polygon(temp_geojson_file)
        
        assert isinstance(polygon, Polygon)
        assert polygon.is_valid

    def test_get_cached_polygon_second_load(self, temp_geojson_file):
        """Test second load of polygon (should use cache)."""
        # First load
        polygon1 = get_cached_polygon(temp_geojson_file)
        
        # Second load (should be from cache)
        polygon2 = get_cached_polygon(temp_geojson_file)
        
        # Should be the same object (from cache)
        assert polygon1 is polygon2

    def test_get_cached_polygon_force_reload(self, temp_geojson_file):
        """Test force reload of cached polygon."""
        # First load
        polygon1 = get_cached_polygon(temp_geojson_file)
        
        # Force reload
        polygon2 = get_cached_polygon(temp_geojson_file, force_reload=True)
        
        # Should be different objects (reloaded)
        assert polygon1 is not polygon2
        assert polygon1.equals(polygon2)  # But geometrically equivalent

    def test_clear_polygon_cache(self, temp_geojson_file):
        """Test clearing the polygon cache."""
        # Load polygon to cache it
        get_cached_polygon(temp_geojson_file)
        
        # Clear cache
        clear_polygon_cache()
        
        # Load again (should reload from file)
        polygon = get_cached_polygon(temp_geojson_file)
        assert isinstance(polygon, Polygon)

    # Performance and edge case tests
    def test_large_polygon_performance(self):
        """Test performance with a large polygon."""
        # Create a polygon with many points
        import math
        num_points = 1000
        coords = []
        center_lat, center_lon = -33.0, 151.0
        radius = 0.1
        
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            lat = center_lat + radius * math.cos(angle)
            lon = center_lon + radius * math.sin(angle)
            coords.append((lat, lon))
        
        coords.append(coords[0])  # Close the polygon
        
        # Test validation
        result = validate_polygon_coordinates(coords)
        assert result is True
        
        # Test point-in-polygon
        result = is_point_in_polygon_from_coords(center_lat, center_lon, coords)
        assert result is True

    def test_point_on_boundary(self, simple_polygon_coords):
        """Test point exactly on polygon boundary."""
        # Point on the edge of the polygon
        result = is_point_in_polygon_from_coords(-33.0, 151.5, simple_polygon_coords)
        
        # Result should be boolean (implementation dependent, but consistent)
        assert isinstance(result, bool)

    def test_real_world_coordinates(self):
        """Test with real-world Australian coordinates."""
        # Simplified Australian polygon
        aus_coords = [
            (-10.0, 113.0),   # Northwest
            (-10.0, 154.0),   # Northeast  
            (-44.0, 154.0),   # Southeast
            (-44.0, 113.0),   # Southwest
            (-10.0, 113.0)    # Close
        ]
        
        # Sydney should be inside
        sydney_result = is_point_in_polygon_from_coords(-33.8688, 151.2093, aus_coords)
        assert sydney_result is True
        
        # London should be outside
        london_result = is_point_in_polygon_from_coords(51.5074, -0.1278, aus_coords)
        assert london_result is False

    def test_coordinate_edge_cases(self):
        """Test coordinate edge cases."""
        coords = [
            (-90.0, -180.0),  # Extreme southwest
            (-90.0, 180.0),   # Extreme southeast
            (90.0, 180.0),    # Extreme northeast
            (90.0, -180.0),   # Extreme northwest
            (-90.0, -180.0)   # Close
        ]
        
        # Should validate correctly
        result = validate_polygon_coordinates(coords)
        assert result is True
        
        # Test point at center
        result = is_point_in_polygon_from_coords(0.0, 0.0, coords)
        assert isinstance(result, bool)

    def test_logging_integration(self, temp_geojson_file, caplog):
        """Test that logging works correctly."""
        import logging
        
        with caplog.at_level(logging.INFO):
            load_polygon_from_geojson(temp_geojson_file)
        
        # Check that appropriate log messages were generated
        assert any("Detected GeoJSON format" in record.message for record in caplog.records)
        assert any("Loaded polygon with" in record.message for record in caplog.records)
