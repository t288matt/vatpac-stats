#!/usr/bin/env python3
"""
Check if Darwin is enclosed within the TRT sector boundary
"""

import json
from shapely.geometry import Point, Polygon

def check_darwin_coverage():
    """Check if Darwin is within the TRT sector boundary"""
    
    # Darwin coordinates (approximately)
    darwin_lat = -12.4628
    darwin_lon = 130.8418
    
    # Load the GeoJSON file
    with open('processed_sectors/australian_airspace_sectors.geojson', 'r') as f:
        data = json.load(f)
    
    # Find the TRT sector
    trt_feature = None
    for feature in data['features']:
        if feature['properties']['name'] == 'TRT':
            trt_feature = feature
            break
    
    if not trt_feature:
        print("❌ TRT sector not found!")
        return
    
    # Extract coordinates
    coords = trt_feature['geometry']['coordinates'][0]
    
    # Create Shapely polygon
    polygon = Polygon(coords)
    
    # Create Darwin point
    darwin_point = Point(darwin_lon, darwin_lat)
    
    # Check if Darwin is within the polygon
    is_within = polygon.contains(darwin_point)
    
    print(f"📍 Darwin coordinates: ({darwin_lon}, {darwin_lat})")
    print(f"🔍 TRT polygon valid: {polygon.is_valid}")
    print(f"🔍 TRT polygon area: {polygon.area:.6f}")
    print(f"🔍 Darwin within TRT: {is_within}")
    
    # Check distance to boundary
    distance_to_boundary = polygon.exterior.distance(darwin_point)
    print(f"🔍 Distance to TRT boundary: {distance_to_boundary:.6f} degrees")
    
    # Analyze the boundary path
    print(f"\n🔍 TRT Boundary Analysis:")
    print(f"   Total coordinate pairs: {len(coords)}")
    
    # Find the closest point on the boundary
    min_distance = float('inf')
    closest_point = None
    
    for i, coord in enumerate(coords):
        lon, lat = coord
        point = Point(lon, lat)
        dist = darwin_point.distance(point)
        if dist < min_distance:
            min_distance = dist
            closest_point = (lon, lat, i)
    
    print(f"   Closest boundary point: ({closest_point[0]:.6f}, {closest_point[1]:.6f}) at index {closest_point[2]}")
    print(f"   Distance to closest boundary: {min_distance:.6f} degrees")
    
    # Check if there are any obvious gaps
    print(f"\n🔍 Boundary Continuity Check:")
    
    # Look for large jumps in coordinates
    large_jumps = []
    for i in range(1, len(coords)):
        prev_lon, prev_lat = coords[i-1]
        curr_lon, curr_lat = coords[i]
        
        # Calculate distance between consecutive points
        dist = ((curr_lon - prev_lon)**2 + (curr_lat - prev_lat)**2)**0.5
        
        if dist > 1.0:  # More than 1 degree jump
            large_jumps.append((i, prev_lon, prev_lat, curr_lon, curr_lat, dist))
    
    if large_jumps:
        print(f"   ⚠️  Found {len(large_jumps)} large coordinate jumps:")
        for jump in large_jumps:
            print(f"      Jump {jump[0]}: ({jump[1]:.3f}, {jump[2]:.3f}) -> ({jump[3]:.3f}, {jump[4]:.3f}) = {jump[5]:.3f}°")
    else:
        print(f"   ✅ No large coordinate jumps found")
    
    # Check if the polygon is simple (no self-intersections)
    is_simple = polygon.is_simple
    print(f"   Polygon is simple (no self-intersections): {is_simple}")
    
    return is_within

if __name__ == "__main__":
    check_darwin_coverage()
