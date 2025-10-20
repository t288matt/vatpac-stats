#!/usr/bin/env python3
"""
Verify Sector Assignments - Manual Check
"""

import json
import sys
import os
from shapely.geometry import Point, Polygon

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from utils.sector_loader import SectorLoader

def verify_coordinates():
    """Verify what sectors specific coordinates should be in"""
    
    # Load sector boundaries
    geojson_path = os.path.join(os.path.dirname(__file__), "config", "australian_airspace_sectors.geojson")
    sector_loader = SectorLoader(geojson_path)
    
    if not sector_loader.load_sectors():
        print("Failed to load sectors")
        return
    
    # Test coordinates from QTR44Y flight - ASP exit time
    test_coordinates = [
        (-36.78576, 131.78948),  # 06:10:39 - ASP exit time
        (-36.80176, 131.96798),  # 06:11:40 - ASP exit time
        (-36.81752, 132.1468),   # 06:12:41 - ASP exit time
        (-36.833, 132.32561),    # 06:13:41 - ASP exit time
        (-36.88033, 132.89307),  # 06:16:43 - Exact ASP exit time
    ]
    
    print("Manual sector verification for QTR44Y coordinates:")
    print("=" * 60)
    
    for i, (lat, lon) in enumerate(test_coordinates):
        sector = sector_loader.get_sector_for_point(lat, lon)
        print(f"Point {i+1}: ({lat:8.5f}, {lon:8.5f}) -> Sector: {sector}")
    
    print("\n" + "=" * 60)
    print("Expected: All points should be in IND sector")
    print("If any point shows a different sector, there may be an issue")

if __name__ == "__main__":
    verify_coordinates()
