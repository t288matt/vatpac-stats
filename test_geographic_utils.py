#!/usr/bin/env python3
"""
Test script for geographic utilities functions.
"""

from app.utils.geographic_utils import *
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    print('🧪 Testing Geographic Utils Functions')
    print('=' * 50)

    try:
        # Test 1: Load polygon from GeoJSON
        print("\n📂 Test 1: Loading Australian airspace polygon...")
        polygon = load_polygon_from_geojson('australian_airspace_polygon.json')
        print(f'✅ Polygon loaded successfully')
        print(f'📊 Polygon points: {len(polygon.exterior.coords)}')
        
        # Test 2: Get polygon bounds
        print("\n📍 Test 2: Getting polygon bounds...")
        bounds = get_polygon_bounds(polygon)
        print(f'📍 Bounds: {bounds}')
        
        # Test 3: Test point inside (Sydney coordinates)
        print("\n🏙️  Test 3: Testing Sydney coordinates...")
        sydney_lat, sydney_lon = -33.8688, 151.2093
        is_inside = is_point_in_polygon(sydney_lat, sydney_lon, polygon)
        print(f'🏙️  Sydney ({sydney_lat}, {sydney_lon}): {"INSIDE" if is_inside else "OUTSIDE"}')
        
        # Test 4: Test point outside (London coordinates)
        print("\n🏙️  Test 4: Testing London coordinates...")
        london_lat, london_lon = 51.5074, -0.1278
        is_outside = is_point_in_polygon(london_lat, london_lon, polygon)
        print(f'🏙️  London ({london_lat}, {london_lon}): {"INSIDE" if is_outside else "OUTSIDE"}')
        
        # Test 5: Test point inside (Melbourne coordinates)
        print("\n🏙️  Test 5: Testing Melbourne coordinates...")
        melbourne_lat, melbourne_lon = -37.8136, 144.9631
        is_melbourne_inside = is_point_in_polygon(melbourne_lat, melbourne_lon, polygon)
        print(f'🏙️  Melbourne ({melbourne_lat}, {melbourne_lon}): {"INSIDE" if is_melbourne_inside else "OUTSIDE"}')
        
        # Test 6: Validate GeoJSON file
        print("\n✅ Test 6: Validating GeoJSON file...")
        is_valid = validate_geojson_polygon('australian_airspace_polygon.json')
        print(f'✅ GeoJSON validation: {"PASSED" if is_valid else "FAILED"}')
        
        # Test 7: Test caching
        print("\n💾 Test 7: Testing polygon caching...")
        cached_polygon = get_cached_polygon('australian_airspace_polygon.json')
        print(f'💾 Cached polygon loaded: {len(cached_polygon.exterior.coords)} points')
        
        # Test 8: Test coordinate validation
        print("\n🔍 Test 8: Testing coordinate validation...")
        test_coords = [(-33.0, 151.0), (-34.0, 151.0), (-34.0, 152.0), (-33.0, 152.0)]
        is_coords_valid = validate_polygon_coordinates(test_coords)
        print(f'🔍 Test coordinates valid: {"YES" if is_coords_valid else "NO"}')
        
        print(f'\n🎯 All tests completed successfully!')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
