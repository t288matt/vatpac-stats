#!/usr/bin/env python3
"""
Consolidated Unit Tests for Critical Functions - Geographic Utilities

This module provides efficient unit tests for the most critical
geographic functions in the VATSIM data system.

Focus Areas:
- Coordinate parsing (DDMMSS format)
- Point-in-polygon calculations
- Boundary edge cases
- Error handling
"""

import pytest
import sys
import os
from pathlib import Path

# Add the app directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from utils.geographic_utils import (
    parse_ddmm_coordinate,
    is_point_in_polygon,
    load_polygon_from_geojson,
    get_cached_polygon
)
from shapely.geometry import Point, Polygon
import tempfile
import json


class TestCoordinateParsing:
    """Test coordinate parsing functionality - most critical function"""
    
    def test_coordinate_parsing_ddmmss_format(self):
        """Test coordinate parsing with DDMMSS.SSSS format"""
        test_cases = [
            ("-343848.000", -34.6467),      # Sydney area
            ("+1494851.000", 149.8142),     # Sydney area
            ("+515100.000", 51.85),         # London area
            ("+000030.000", 0.0083),        # Equator
            ("+1800000.000", 180.0),        # International date line
            ("-900000.000", -90.0),         # South pole
            ("+900000.000", 90.0),          # North pole
        ]
        
        for coord_string, expected in test_cases:
            result = parse_ddmm_coordinate(coord_string)
            assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
    
    def test_coordinate_parsing_decimal_format(self):
        """Test coordinate parsing with decimal degrees format"""
        test_cases = [
            ("-34.6467", -34.6467),         # Sydney area
            ("149.8142", 149.8142),         # Sydney area
            ("51.0167", 51.0167),           # London area
            ("0.0", 0.0),                   # Origin
            ("180.0", 180.0),               # International date line
        ]
        
        for coord_string, expected in test_cases:
            result = parse_ddmm_coordinate(coord_string)
            assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
    
    def test_coordinate_parsing_edge_cases(self):
        """Test coordinate parsing edge cases"""
        test_cases = [
            ("+000000.000", 0.0),           # Zero with padding
            ("-000000.000", 0.0),           # Negative zero with padding
            ("+001000.000", 0.1667),        # 1 minute
            ("+000100.000", 0.0167),        # 1 second
        ]
        
        for coord_string, expected in test_cases:
            result = parse_ddmm_coordinate(coord_string)
            assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
    
    def test_coordinate_parsing_invalid_formats(self):
        """Test coordinate parsing with invalid formats"""
        invalid_cases = [
            "invalid",
            "123",                          # Too few digits
            "12345678.000",                 # Too many digits
            "12345.000",                    # Wrong format
            "12.34.56",                     # Multiple decimals
            "",                             # Empty string
            "   ",                          # Whitespace only
            "abc123.000",                   # Letters mixed
            "123.abc",                      # Letters after decimal
        ]
        
        for coord_string in invalid_cases:
            with pytest.raises(ValueError):
                parse_ddmm_coordinate(coord_string)
    
    def test_coordinate_parsing_whitespace_handling(self):
        """Test coordinate parsing handles whitespace correctly"""
        result1 = parse_ddmm_coordinate("  -343848.000  ")
        result2 = parse_ddmm_coordinate("\t+1494851.000\n")
        assert abs(result1 - (-34.6467)) < 0.0001, f"Expected -34.6467, got {result1}"
        assert abs(result2 - 149.8142) < 0.0001, f"Expected 149.8142, got {result2}"


class TestPointInPolygon:
    """Test point-in-polygon calculations - core filtering logic"""
    
    def setup_method(self):
        """Setup test polygon (Australian airspace approximation)"""
        # Create a simple polygon approximating Australian airspace
        self.australia_polygon = Polygon([
            (110.0, -45.0),   # Southwest
            (155.0, -45.0),   # Southeast  
            (155.0, -10.0),   # Northeast
            (110.0, -10.0),   # Northwest
            (110.0, -45.0)    # Close the polygon
        ])
        
        # Create a smaller polygon for edge case testing
        self.small_polygon = Polygon([
            (0.0, 0.0),       # Southwest
            (1.0, 0.0),       # Southeast
            (1.0, 1.0),       # Northeast
            (0.0, 1.0),       # Northwest
            (0.0, 0.0)        # Close the polygon
        ])
    
    def test_australia_polygon_inside_points(self):
        """Test points clearly inside Australia"""
        inside_points = [
            (-25.0, 135.0),      # Alice Springs area
            (-33.0, 151.0),      # Sydney area
            (-37.0, 145.0),      # Melbourne area
            (-31.0, 115.0),      # Perth area
            (-20.0, 130.0),      # Northern Territory
            (-42.0, 147.0),      # Tasmania area
        ]
        
        for lat, lon in inside_points:
            result = is_point_in_polygon(lat, lon, self.australia_polygon)
            assert result == True, f"Point ({lat}, {lon}) should be inside"
    
    def test_australia_polygon_outside_points(self):
        """Test points clearly outside Australia"""
        outside_points = [
            (0.0, 0.0),         # Gulf of Guinea
            (40.0, -74.0),      # New York
            (51.0, 0.0),        # London
            (35.0, 139.0),      # Tokyo
            (-90.0, 0.0),       # South Pole
            (90.0, 0.0),        # North Pole
        ]
        
        for lat, lon in outside_points:
            result = is_point_in_polygon(lat, lon, self.australia_polygon)
            assert result == False, f"Point ({lat}, {lon}) should be outside"
    
    def test_australia_polygon_boundary_edge_cases(self):
        """Test boundary edge cases with representative samples"""
        # Test a few key boundary cases instead of all 40+ variations
        edge_cases = [
            (-44.999, 110.001, True),   # Just inside southwest
            (-10.001, 154.999, True),   # Just inside northeast
            (-45.001, 110.0, False),    # Just outside south
            (-10.0, 155.001, False),   # Just outside east
        ]
        
        for lat, lon, expected in edge_cases:
            result = is_point_in_polygon(lat, lon, self.australia_polygon)
            assert result == expected, f"Point ({lat}, {lon}) should be {'inside' if expected else 'outside'}"
    
    def test_small_polygon_edge_cases(self):
        """Test small polygon with key edge cases"""
        # Test representative edge cases instead of all variations
        edge_cases = [
            (0.5, 0.5, True),          # Center
            (0.001, 0.001, True),      # Just inside southwest
            (0.999, 0.999, True),      # Just inside northeast
            (-0.1, 0.5, False),        # Just outside west
            (1.1, 0.5, False),         # Just outside east
        ]
        
        for lat, lon, expected in edge_cases:
            result = is_point_in_polygon(lat, lon, self.small_polygon)
            assert result == expected, f"Point ({lat}, {lon}) should be {'inside' if expected else 'outside'}"
    
    def test_global_coordinate_coverage(self):
        """Test global coordinate coverage with representative points"""
        # Test a few key global coordinates instead of exhaustive coverage
        global_points = [
            (0.0, 0.0),         # Origin
            (90.0, 0.0),        # North Pole
            (-90.0, 0.0),       # South Pole
            (0.0, 180.0),       # International date line
            (0.0, -180.0),      # International date line (negative)
        ]
        
        for lat, lon in global_points:
            # These should all be outside Australia
            result = is_point_in_polygon(lat, lon, self.australia_polygon)
            assert result == False, f"Global point ({lat}, {lon}) should be outside Australia"


class TestPolygonLoading:
    """Test polygon loading from GeoJSON files"""
    
    def test_load_polygon_from_geojson_valid(self):
        """Test loading valid GeoJSON polygon"""
        # Create a temporary valid GeoJSON file
        # The function expects coordinates at the top level, not nested under geometry
        valid_geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_geojson, f)
            temp_file = f.name
        
        try:
            polygon = load_polygon_from_geojson(temp_file)
            assert polygon is not None
            assert isinstance(polygon, Polygon)
        finally:
            os.unlink(temp_file)
    
    def test_load_polygon_from_geojson_invalid_file(self):
        """Test loading from non-existent file"""
        with pytest.raises(FileNotFoundError):
            load_polygon_from_geojson("nonexistent_file.json")
    
    def test_load_polygon_from_geojson_invalid_format(self):
        """Test loading invalid GeoJSON format"""
        # Create a temporary invalid GeoJSON file
        invalid_geojson = {"invalid": "format"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_geojson, f)
            temp_file = f.name
        
        try:
            with pytest.raises(Exception):  # Should raise some kind of error
                load_polygon_from_geojson(temp_file)
        finally:
            os.unlink(temp_file)


class TestCaching:
    """Test polygon caching functionality"""
    
    def test_get_cached_polygon_same_file(self):
        """Test that same file returns cached polygon"""
        # Create a temporary valid GeoJSON file
        # The function expects coordinates at the top level, not nested under geometry
        valid_geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_geojson, f)
            temp_file = f.name
        
        try:
            # Load polygon twice
            polygon1 = get_cached_polygon(temp_file)
            polygon2 = get_cached_polygon(temp_file)
            
            # Should be the same object (cached)
            assert polygon1 is polygon2
            assert isinstance(polygon1, Polygon)
        finally:
            os.unlink(temp_file)
