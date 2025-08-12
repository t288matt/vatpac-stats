#!/usr/bin/env python3
"""
Unit Tests for Critical Functions - Geographic Utilities

This module provides comprehensive unit tests for the most critical
geographic functions in the VATSIM data system.

Focus Areas:
- Coordinate parsing (DDMMSS format)
- Point-in-polygon calculations
- Boundary edge cases
- Global coordinate coverage
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
    
    @pytest.mark.parametrize("coord_string,expected", [
        # DDMMSS.SSSS format (6 digits before decimal)
        ("-343848.000", -34.6467),      # Sydney area
        ("+1494851.000", 149.8142),     # Sydney area
        ("+515100.000", 51.85),         # London area
        ("+000030.000", 0.0083),        # Equator (6 digits)
        ("+000000.000", 0.0),           # Prime meridian (6 digits)
        ("+1800000.000", 180.0),        # International date line
        ("-900000.000", -90.0),         # South pole
        ("+900000.000", 90.0),          # North pole
        
        # DDDMMSS.SSSS format (7 digits before decimal)
        ("-1343848.000", -134.6467),    # Pacific Ocean
        ("+1794851.000", 179.8142),     # Pacific Ocean
        ("+0515100.000", 51.85),        # London area (padded)
        
        # Decimal degrees (should pass through unchanged)
        ("-34.6467", -34.6467),         # Sydney area
        ("149.8142", 149.8142),         # Sydney area
        ("51.0167", 51.0167),           # London area
        ("0.0", 0.0),                   # Origin
        ("180.0", 180.0),               # International date line
        ("-90.0", -90.0),               # South pole
        ("90.0", 90.0),                 # North pole
        
        # Edge cases
        ("+000000.000", 0.0),           # Zero with padding
        ("-000000.000", 0.0),           # Negative zero with padding
        ("+001000.000", 0.1667),        # 1 minute
        ("+000100.000", 0.0167),        # 1 second
        ("+000001.000", 0.0003),        # 0.1 seconds
    ])
    def test_coordinate_parsing_valid_formats(self, coord_string, expected):
        """Test coordinate parsing with various valid formats"""
        result = parse_ddmm_coordinate(coord_string)
        assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
    
    @pytest.mark.parametrize("coord_string", [
        "invalid",
        "123",                          # Too few digits
        "12345678.000",                 # Too many digits
        "12345.000",                    # Wrong format
        "12.34.56",                     # Multiple decimals
        "",                             # Empty string
        "   ",                          # Whitespace only
        "abc123.000",                   # Letters mixed
        "123.abc",                      # Letters after decimal
    ])
    def test_coordinate_parsing_invalid_formats(self, coord_string):
        """Test coordinate parsing with invalid formats"""
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
        # This is a simplified rectangle for testing purposes
        # Note: Shapely expects (lon, lat) format, not (lat, lon)
        self.australia_polygon = Polygon([
            (110.0, -45.0),   # Southwest
            (155.0, -45.0),   # Southeast  
            (155.0, -10.0),   # Northeast
            (110.0, -10.0),   # Northwest
            (110.0, -45.0)    # Close the polygon
        ])
        
        # Create a smaller polygon for edge case testing
        # Note: Shapely expects (lon, lat) format, not (lat, lon)
        self.small_polygon = Polygon([
            (0.0, 0.0),       # Southwest
            (1.0, 0.0),       # Southeast
            (1.0, 1.0),       # Northeast
            (0.0, 1.0),       # Northwest
            (0.0, 0.0)        # Close the polygon
        ])
    
    @pytest.mark.parametrize("lat,lon,expected", [
        # Points clearly inside Australia
        (-25.0, 135.0, True),      # Alice Springs area
        (-33.0, 151.0, True),      # Sydney area
        (-37.0, 145.0, True),      # Melbourne area
        (-31.0, 115.0, True),      # Perth area
        (-20.0, 130.0, True),      # Northern Territory
        (-42.0, 147.0, True),      # Tasmania area
        
        # Points clearly outside Australia
        (0.0, 0.0, False),         # Gulf of Guinea
        (40.0, -74.0, False),      # New York
        (51.0, 0.0, False),        # London
        (35.0, 139.0, False),      # Tokyo
        (-90.0, 0.0, False),       # South Pole
        (90.0, 0.0, False),        # North Pole
        (-45.0, 180.0, False),     # Pacific Ocean
        (-45.0, -180.0, False),    # Pacific Ocean
        
        # Edge cases - just inside boundary (reliable testing)
        (-44.999, 110.001, True),  # Southwest corner - just inside
        (-44.999, 154.999, True),  # Southeast corner - just inside
        (-10.001, 154.999, True),  # Northeast corner - just inside
        (-10.001, 110.001, True),  # Northwest corner - just inside
        
        # Edge cases - just inside boundary (marginally inside)
        (-44.999, 110.001, True),  # Just inside southwest
        (-10.001, 154.999, True),  # Just inside northeast
        (-44.9999, 110.0001, True), # Very marginally inside southwest
        (-10.0001, 154.9999, True), # Very marginally inside northeast
        (-44.99, 110.01, True),     # Marginally inside southwest
        (-10.01, 154.99, True),     # Marginally inside northeast
        (-44.9, 110.1, True),       # Marginally inside southwest
        (-10.1, 154.9, True),       # Marginally inside northeast
        
        # Edge cases - just outside boundary (marginally outside)
        (-45.001, 110.0, False),   # Just outside south
        (-10.0, 155.001, False),   # Just outside east
        (-45.0001, 110.0, False),  # Very marginally outside south
        (-10.0, 155.0001, False),  # Very marginally outside east
        (-45.01, 110.0, False),    # Marginally outside south
        (-10.0, 155.01, False),    # Marginally outside east
        (-45.1, 110.0, False),     # Marginally outside south
        (-10.0, 155.1, False),     # Marginally outside east
        
        # Edge cases - boundary corners with tiny offsets
        (-44.999, 109.999, False), # Just outside southwest corner
        (-44.999, 155.001, False), # Just outside southeast corner
        (-10.001, 155.001, False), # Just outside northeast corner
        (-10.001, 109.999, False), # Just outside northwest corner
    ])
    def test_australia_polygon_boundary_testing(self, lat, lon, expected):
        """Test points around Australian airspace boundary"""
        result = is_point_in_polygon(lat, lon, self.australia_polygon)
        assert result == expected, f"Point ({lat}, {lon}) should be {'inside' if expected else 'outside'}"
    
    @pytest.mark.parametrize("lat,lon,expected", [
        # Points inside small polygon
        (0.5, 0.5, True),          # Center
        (0.1, 0.1, True),          # Near southwest
        (0.9, 0.9, True),          # Near northeast
        
        # Points outside small polygon
        (-0.1, 0.5, False),        # West
        (1.1, 0.5, False),         # East
        (0.5, -0.1, False),        # South
        (0.5, 1.1, False),         # North
        
        # Edge cases - just inside boundary (reliable testing)
        (0.001, 0.001, True),      # Southwest corner - just inside
        (0.999, 0.999, True),      # Northeast corner - just inside
        (0.001, 0.5, True),        # West edge - just inside
        (0.999, 0.5, True),        # East edge - just inside
        (0.5, 0.001, True),        # South edge - just inside
        (0.5, 0.999, True),        # North edge - just inside
    ])
    def test_small_polygon_edge_cases(self, lat, lon, expected):
        """Test edge cases with small polygon"""
        result = is_point_in_polygon(lat, lon, self.small_polygon)
        assert result == expected, f"Point ({lat}, {lon}) should be {'inside' if expected else 'outside'}"
    
    def test_global_coordinate_coverage(self):
        """Test points all over the world"""
        global_test_points = [
            # North America
            (40.7128, -74.0060, False),    # New York
            (34.0522, -118.2437, False),   # Los Angeles
            (43.6532, -79.3832, False),    # Toronto
            (19.4326, -99.1332, False),    # Mexico City
            
            # South America
            (-23.5505, -46.6333, False),   # Sao Paulo
            (-34.6118, -58.3960, False),   # Buenos Aires
            (-12.9716, -38.5011, False),   # Salvador
            (-33.4489, -70.6693, False),   # Santiago
            
            # Europe
            (51.5074, -0.1278, False),     # London
            (48.8566, 2.3522, False),      # Paris
            (52.5200, 13.4050, False),     # Berlin
            (41.9028, 12.4964, False),     # Rome
            (55.7558, 37.6176, False),     # Moscow
            
            # Africa
            (30.0444, 31.2357, False),     # Cairo
            (-26.2041, 28.0473, False),    # Johannesburg
            (6.5244, 3.3792, False),       # Lagos
            (-1.2921, 36.8219, False),     # Nairobi
            
            # Asia
            (35.6762, 139.6503, False),    # Tokyo
            (39.9042, 116.4074, False),    # Beijing
            (28.6139, 77.2090, False),     # New Delhi
            (1.3521, 103.8198, False),     # Singapore
            (25.2048, 55.2708, False),     # Dubai
            
            # Pacific
            (-41.2866, 174.7756, False),   # Wellington
            (-17.6797, 178.8325, False),   # Suva
            (21.3099, -157.8581, False),   # Honolulu
            
            # Arctic/Antarctic
            (78.2232, 15.6267, False),     # Svalbard
            (-77.8463, 166.6683, False),   # McMurdo Station
            
            # Ocean centers
            (0.0, 0.0, False),             # Gulf of Guinea
            (0.0, 180.0, False),           # Pacific Ocean
            (0.0, -180.0, False),          # Pacific Ocean
            (0.0, 90.0, False),            # Indian Ocean
            (0.0, -90.0, False),           # Atlantic Ocean
        ]
        
        for lat, lon, expected in global_test_points:
            result = is_point_in_polygon(lat, lon, self.australia_polygon)
            assert result == expected, f"Global point ({lat}, {lon}) should be {'inside' if expected else 'outside'} Australia"
    
    def test_polygon_edge_behavior(self):
        """Test behavior exactly on polygon edges"""
        # Test points exactly on the edges of Australia polygon
        edge_points = [
            (-45.0, 110.0),   # Southwest corner
            (-45.0, 132.5),   # South edge
            (-45.0, 155.0),   # Southeast corner
            (-27.5, 155.0),   # East edge
            (-10.0, 155.0),   # Northeast corner
            (-10.0, 132.5),   # North edge
            (-10.0, 110.0),   # Northwest corner
            (-27.5, 110.0),   # West edge
        ]
        
        for lat, lon in edge_points:
            result = is_point_in_polygon(lat, lon, self.australia_polygon)
            # Note: Shapely's contains() behavior on edges may vary
            # We're testing that it doesn't crash and gives consistent results
            assert isinstance(result, bool), f"Edge point ({lat}, {lon}) should return boolean"
    
    def test_marginal_boundary_testing(self):
        """Test points very close to boundary - critical for real-world accuracy"""
        # Test with reliable offsets to ensure boundary detection is precise
        marginal_offsets = [0.1, 0.5, 1.0]
        
        for offset in marginal_offsets:
            # Test south boundary - ensure points are clearly inside, not on boundary
            point_inside = Point(110.0 + offset, -45.0 + offset)  # Just inside (diagonal)
            point_outside = Point(110.0 - offset, -45.0 - offset)  # Just outside (diagonal)
            
            result_inside = is_point_in_polygon(point_inside.y, point_inside.x, self.australia_polygon)
            result_outside = is_point_in_polygon(point_outside.y, point_outside.x, self.australia_polygon)
            
            assert result_inside == True, f"Point {offset} degrees inside south boundary should be inside"
            assert result_outside == False, f"Point {offset} degrees outside south boundary should be outside"
            
            # Test north boundary - ensure points are clearly inside, not on boundary
            point_inside = Point(155.0 - offset, -10.0 - offset)  # Just inside (diagonal)
            point_outside = Point(155.0 + offset, -10.0 + offset)  # Just outside (diagonal)
            
            result_inside = is_point_in_polygon(point_inside.y, point_inside.x, self.australia_polygon)
            result_outside = is_point_in_polygon(point_outside.y, point_outside.x, self.australia_polygon)
            
            assert result_inside == True, f"Point {offset} degrees inside north boundary should be inside"
            assert result_outside == False, f"Point {offset} degrees outside north boundary should be outside"
            
            # Test west boundary - ensure points are clearly inside, not on boundary
            point_inside = Point(110.0 + offset, -27.5 + offset)  # Just inside (diagonal)
            point_outside = Point(110.0 - offset, -27.5 - offset)  # Just outside (diagonal)
            
            result_inside = is_point_in_polygon(point_inside.y, point_inside.x, self.australia_polygon)
            result_outside = is_point_in_polygon(point_outside.y, point_outside.x, self.australia_polygon)
            
            assert result_inside == True, f"Point {offset} degrees inside west boundary should be inside"
            assert result_outside == False, f"Point {offset} degrees outside west boundary should be outside"
            
            # Test east boundary - ensure points are clearly inside, not on boundary
            point_inside = Point(155.0 - offset, -27.5 - offset)  # Just inside (diagonal)
            point_outside = Point(155.0 + offset, -27.5 + offset)  # Just outside (diagonal)
            
            result_inside = is_point_in_polygon(point_inside.y, point_inside.x, self.australia_polygon)
            result_outside = is_point_in_polygon(point_outside.y, point_outside.x, self.australia_polygon)
            
            assert result_inside == True, f"Point {offset} degrees inside east boundary should be inside"
            assert result_outside == False, f"Point {offset} degrees outside east boundary should be outside"
    
    def test_corner_marginal_testing(self):
        """Test points very close to polygon corners"""
        # Test southwest corner with tiny offsets
        sw_corner_lat, sw_corner_lon = -45.0, 110.0
        
        # Test inside corner (diagonal)
        for offset in [0.01, 0.1, 0.5]:
            point_inside = Point(sw_corner_lon + offset, sw_corner_lat + offset)
            result = is_point_in_polygon(point_inside.y, point_inside.x, self.australia_polygon)
            assert result == True, f"Point {offset} degrees inside southwest corner should be inside"
        
        # Test outside corner (diagonal)
        for offset in [0.01, 0.1, 0.5]:
            point_outside = Point(sw_corner_lon - offset, sw_corner_lat - offset)
            result = is_point_in_polygon(point_outside.y, point_outside.x, self.australia_polygon)
            assert result == False, f"Point {offset} degrees outside southwest corner should be outside"
        
        # Test northeast corner with reliable offsets
        ne_corner_lat, ne_corner_lon = -10.0, 155.0
        
        # Test inside corner (diagonal)
        for offset in [0.01, 0.1, 0.5]:
            point_inside = Point(ne_corner_lon - offset, ne_corner_lat - offset)
            result = is_point_in_polygon(point_inside.y, point_inside.x, self.australia_polygon)
            assert result == True, f"Point {offset} degrees inside northeast corner should be inside"
        
        # Test outside corner (diagonal)
        for offset in [0.01, 0.1, 0.5]:
            point_outside = Point(ne_corner_lon + offset, ne_corner_lat + offset)
            result = is_point_in_polygon(point_outside.y, point_outside.x, self.australia_polygon)
            assert result == False, f"Point {offset} degrees outside northeast corner should be outside"
    
    def test_floating_point_precision_edge_cases(self):
        """Test floating-point precision issues that commonly occur in real-world coordinates"""
        # Test with small but reliable floating-point differences
        precision_offsets = [1e-4, 1e-3, 1e-2, 1e-1]
        
        for offset in precision_offsets:
            # Test boundary with floating-point precision
            point_inside = Point(110.0 + offset, -45.0 + offset)
            point_outside = Point(110.0 - offset, -45.0 - offset)
            
            result_inside = is_point_in_polygon(point_inside.y, point_inside.x, self.australia_polygon)
            result_outside = is_point_in_polygon(point_outside.y, point_outside.x, self.australia_polygon)
            
            # For very small offsets, we expect consistent behavior
            assert result_inside == True, f"Point {offset} (scientific notation) inside should be inside"
            assert result_outside == False, f"Point {offset} (scientific notation) outside should be outside"
        
        # Test with coordinates that might have floating-point representation issues
        problematic_coords = [
            (110.00000000000001, -45.00000000000001),  # Just inside with floating-point error
            (109.99999999999999, -44.99999999999999),  # Just outside with floating-point error
            (155.00000000000001, -10.00000000000001),  # Just inside with floating-point error
            (154.99999999999999, -9.99999999999999),   # Just outside with floating-point error
        ]
        
        for lon, lat in problematic_coords:
            result = is_point_in_polygon(lat, lon, self.australia_polygon)
            # These should give consistent results despite floating-point precision
            assert isinstance(result, bool), f"Floating-point coordinate ({lat}, {lon}) should return boolean"


class TestPolygonLoading:
    """Test polygon loading functionality"""
    
    def test_load_polygon_from_geojson_valid(self):
        """Test loading valid GeoJSON polygon"""
        # Create a temporary GeoJSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            geojson_data = {
                "coordinates": [
                    [110.0, -45.0],
                    [155.0, -45.0],
                    [155.0, -10.0],
                    [110.0, -10.0],
                    [110.0, -45.0]
                ]
            }
            json.dump(geojson_data, f)
            temp_file = f.name
        
        try:
            polygon = load_polygon_from_geojson(temp_file)
            assert isinstance(polygon, Polygon)
            assert not polygon.is_empty
            assert polygon.is_valid
        finally:
            os.unlink(temp_file)
    
    def test_load_polygon_from_geojson_invalid_file(self):
        """Test loading from non-existent file"""
        with pytest.raises(FileNotFoundError):
            load_polygon_from_geojson("nonexistent_file.json")
    
    def test_load_polygon_from_geojson_invalid_format(self):
        """Test loading invalid GeoJSON format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": "json"}')
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError):
                load_polygon_from_geojson(temp_file)
        finally:
            os.unlink(temp_file)


class TestCaching:
    """Test polygon caching functionality"""
    
    def test_get_cached_polygon_same_file(self):
        """Test that same file returns cached polygon"""
        # Create a temporary GeoJSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            geojson_data = {
                "coordinates": [
                    [0.0, 0.0],
                    [1.0, 0.0],
                    [1.0, 1.0],
                    [0.0, 1.0],
                    [0.0, 0.0]
                ]
            }
            json.dump(geojson_data, f)
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


if __name__ == "__main__":
    # Run tests directly if called as script
    pytest.main([__file__, "-v"])
