#!/usr/bin/env python3
"""
TEMPORARY TESTING SCRIPT - Polygon Testing with Live VATSIM Data

This script fetches live VATSIM aircraft data and tests if aircraft positions
are inside a specified polygon boundary using Shapely.

Usage:
    python test_polygon_with_live_vatsim_data.py

Requirements:
    pip install shapely requests

Author: Testing Script
Created: 2025-01-08
Status: TEMPORARY - For polygon coordinate validation only
"""

import json
import requests
import sys
from typing import List, Tuple, Dict, Any
from shapely.geometry import Point, Polygon

# VATSIM API endpoint for live data
VATSIM_API_URL = "https://data.vatsim.net/v3/vatsim-data.json"

def load_polygon_from_json(json_file_path: str) -> List[Tuple[float, float]]:
    """
    Load polygon coordinates from JSON file.
    
    Supports multiple formats:
    1. Simple format: {"coordinates": [[lat, lon], [lat, lon], ...]}
    2. GeoJSON format: {"coordinates": [[[lon, lat], [lon, lat], ...]]}
    
    Args:
        json_file_path: Path to JSON file with polygon coordinates
        
    Returns:
        List of (lat, lon) tuples
    """
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        if "coordinates" not in data:
            raise ValueError("JSON file must contain 'coordinates' key")
        
        coords = data["coordinates"]
        
        # Handle GeoJSON format with nested arrays
        if isinstance(coords, list) and len(coords) > 0 and isinstance(coords[0], list):
            if len(coords[0]) > 0 and isinstance(coords[0][0], list):
                # This is GeoJSON format: [[[lon, lat], [lon, lat], ...]]
                coords = coords[0]  # Extract first polygon
                print("📍 Detected GeoJSON format")
                
                # Convert from [lon, lat] to [lat, lon] and create tuples
                coordinates = []
                for coord in coords:
                    if len(coord) != 2:
                        raise ValueError(f"Invalid coordinate format: {coord}")
                    lon, lat = float(coord[0]), float(coord[1])
                    coordinates.append((lat, lon))
            else:
                # Simple format: [[lat, lon], [lat, lon], ...]
                coordinates = []
                for coord in coords:
                    if len(coord) != 2:
                        raise ValueError(f"Invalid coordinate format: {coord}")
                    lat, lon = float(coord[0]), float(coord[1])
                    coordinates.append((lat, lon))
        else:
            raise ValueError(f"Invalid coordinate structure: {coords}")
        
        if len(coordinates) < 3:
            raise ValueError("Polygon must have at least 3 points")
        
        print(f"✅ Loaded polygon with {len(coordinates)} points")
        return coordinates
        
    except FileNotFoundError:
        print(f"❌ Error: JSON file not found: {json_file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading polygon: {e}")
        sys.exit(1)

def fetch_live_vatsim_data() -> List[Dict[str, Any]]:
    """
    Fetch live VATSIM aircraft data from the API.
    
    Returns:
        List of aircraft data dictionaries
    """
    try:
        print("🌐 Fetching live VATSIM data...")
        response = requests.get(VATSIM_API_URL, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        pilots = data.get("pilots", [])
        
        print(f"✅ Fetched {len(pilots)} aircraft from VATSIM API")
        return pilots
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching VATSIM data: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing VATSIM data: {e}")
        sys.exit(1)

def is_point_in_polygon(lat: float, lon: float, polygon_coords: List[Tuple[float, float]]) -> bool:
    """
    Check if a point (lat, lon) is inside a polygon using Shapely.
    
    Args:
        lat: Latitude of the point
        lon: Longitude of the point
        polygon_coords: List of (lat, lon) tuples defining the polygon
        
    Returns:
        True if point is inside the polygon, False otherwise
    """
    try:
        # Shapely expects (x, y) => (lon, lat) order
        point = Point(lon, lat)
        
        # Convert polygon coordinates from (lat, lon) to (lon, lat) for Shapely
        shapely_coords = [(coord[1], coord[0]) for coord in polygon_coords]
        polygon = Polygon(shapely_coords)
        
        if not polygon.is_valid:
            print(f"⚠️  Warning: Invalid polygon detected, attempting to fix...")
            polygon = polygon.buffer(0)
        
        return polygon.contains(point)
        
    except Exception as e:
        print(f"❌ Error in polygon detection: {e}")
        return False

def test_aircraft_in_polygon(aircraft_list: List[Dict[str, Any]], polygon_coords: List[Tuple[float, float]]) -> Dict[str, List[Dict]]:
    """
    Test which aircraft are inside the polygon boundary.
    
    Args:
        aircraft_list: List of aircraft data from VATSIM
        polygon_coords: Polygon boundary coordinates
        
    Returns:
        Dictionary with 'inside' and 'outside' lists of aircraft
    """
    results = {
        "inside": [],
        "outside": [],
        "no_position": []
    }
    
    print(f"\n🧪 Testing {len(aircraft_list)} aircraft against polygon boundary...")
    print("=" * 70)
    
    for aircraft in aircraft_list:
        callsign = aircraft.get("callsign", "UNKNOWN")
        latitude = aircraft.get("latitude")
        longitude = aircraft.get("longitude")
        
        # Skip aircraft without position data
        if latitude is None or longitude is None:
            results["no_position"].append({
                "callsign": callsign,
                "reason": "No position data"
            })
            continue
        
        try:
            lat = float(latitude)
            lon = float(longitude)
            
            # Test if aircraft is in polygon
            is_inside = is_point_in_polygon(lat, lon, polygon_coords)
            
            # Safely extract flight plan data
            flight_plan = aircraft.get("flight_plan") or {}
            departure = flight_plan.get("departure", "N/A") if isinstance(flight_plan, dict) else "N/A"
            arrival = flight_plan.get("arrival", "N/A") if isinstance(flight_plan, dict) else "N/A"
            
            aircraft_info = {
                "callsign": callsign,
                "latitude": lat,
                "longitude": lon,
                "departure": departure,
                "arrival": arrival,
                "altitude": aircraft.get("altitude", "N/A")
            }
            
            if is_inside:
                results["inside"].append(aircraft_info)
                print(f"✅ INSIDE:  {callsign:8} at ({lat:8.4f}, {lon:9.4f}) - {aircraft_info['departure']} → {aircraft_info['arrival']}")
            else:
                results["outside"].append(aircraft_info)
                print(f"❌ OUTSIDE: {callsign:8} at ({lat:8.4f}, {lon:9.4f}) - {aircraft_info['departure']} → {aircraft_info['arrival']}")
                
        except (ValueError, TypeError) as e:
            results["no_position"].append({
                "callsign": callsign,
                "reason": f"Invalid coordinates: {e}"
            })
    
    return results

def print_summary(results: Dict[str, List[Dict]]):
    """Print summary of test results."""
    inside_count = len(results["inside"])
    outside_count = len(results["outside"])
    no_position_count = len(results["no_position"])
    total_count = inside_count + outside_count + no_position_count
    
    print("\n" + "=" * 70)
    print("📊 POLYGON TEST SUMMARY")
    print("=" * 70)
    print(f"Total Aircraft Tested: {total_count}")
    print(f"✅ Inside Polygon:     {inside_count:3d} ({inside_count/total_count*100:.1f}%)")
    print(f"❌ Outside Polygon:    {outside_count:3d} ({outside_count/total_count*100:.1f}%)")
    print(f"⚠️  No Position Data:   {no_position_count:3d} ({no_position_count/total_count*100:.1f}%)")
    
    if inside_count > 0:
        print(f"\n🎯 Aircraft INSIDE polygon:")
        for aircraft in results["inside"][:10]:  # Show first 10
            print(f"   {aircraft['callsign']} - {aircraft['departure']} → {aircraft['arrival']} (Alt: {aircraft['altitude']})")
        if inside_count > 10:
            print(f"   ... and {inside_count - 10} more")

def create_sample_polygon_file():
    """Create a sample polygon file for testing if none exists."""
    sample_file = "sample_polygon_coordinates.json"
    
    # Sample polygon around Sydney area
    sample_polygon = {
        "name": "Sydney Test Area",
        "description": "Sample polygon for testing around Sydney, Australia",
        "coordinates": [
            [-33.0, 150.5],  # Northwest
            [-33.0, 152.0],  # Northeast  
            [-34.5, 152.0],  # Southeast
            [-34.5, 150.5],  # Southwest
            [-33.0, 150.5]   # Close polygon
        ],
        "metadata": {
            "created": "2025-01-08",
            "source": "Testing script",
            "coordinate_system": "WGS84",
            "format": "lat,lon"
        }
    }
    
    try:
        with open(sample_file, 'w') as f:
            json.dump(sample_polygon, f, indent=2)
        print(f"📄 Created sample polygon file: {sample_file}")
        return sample_file
    except Exception as e:
        print(f"❌ Error creating sample file: {e}")
        return None

def find_flight_by_callsign(aircraft_list: List[Dict[str, Any]], callsign: str) -> Dict[str, Any]:
    """
    Find a specific flight by callsign in the aircraft data.
    
    Args:
        aircraft_list: List of aircraft data from VATSIM API
        callsign: Flight callsign to search for
        
    Returns:
        Aircraft data dictionary if found, None otherwise
    """
    callsign_upper = callsign.upper().strip()
    
    for aircraft in aircraft_list:
        if aircraft.get("callsign", "").upper().strip() == callsign_upper:
            return aircraft
    
    return None

def check_single_flight(polygon_file: str, callsign: str):
    """Check if a single flight is inside the polygon."""
    print("🔍 FLIGHT POSITION CHECKER")
    print("=" * 50)
    print(f"Searching for flight: {callsign.upper()}")
    print()
    
    # Load polygon coordinates
    polygon_coords = load_polygon_from_json(polygon_file)
    
    # Fetch live VATSIM data
    aircraft_list = fetch_live_vatsim_data()
    
    if not aircraft_list:
        print("❌ No aircraft data available from VATSIM API")
        return
    
    # Find the specific flight
    flight = find_flight_by_callsign(aircraft_list, callsign)
    
    if not flight:
        print(f"❌ Flight {callsign.upper()} not found in live VATSIM data")
        print(f"📊 Searched through {len(aircraft_list)} active aircraft")
        print("\n💡 Tips:")
        print("   • Make sure the callsign is exactly as shown on VATSIM")
        print("   • The flight must be currently active and online")
        print("   • Try checking https://map.vatsim.net for active flights")
        return
    
    # Extract flight information
    lat = flight.get("latitude")
    lon = flight.get("longitude")
    altitude = flight.get("altitude", "N/A")
    flight_plan = flight.get("flight_plan") or {}
    departure = flight_plan.get("departure", "N/A") if isinstance(flight_plan, dict) else "N/A"
    arrival = flight_plan.get("arrival", "N/A") if isinstance(flight_plan, dict) else "N/A"
    
    print(f"✅ Found flight: {callsign.upper()}")
    print(f"   Route: {departure} → {arrival}")
    print(f"   Position: {lat:.4f}, {lon:.4f}")
    print(f"   Altitude: {altitude} ft")
    print()
    
    if lat is None or lon is None:
        print("❌ Flight has no position data - cannot check polygon")
        return
    
    # Check if inside polygon
    is_inside = is_point_in_polygon(lat, lon, polygon_coords)
    
    print("🎯 POLYGON CHECK RESULT:")
    print("=" * 30)
    if is_inside:
        print(f"✅ {callsign.upper()} is INSIDE the polygon boundary")
        print(f"   📍 Position ({lat:.4f}, {lon:.4f}) is within the defined airspace")
    else:
        print(f"❌ {callsign.upper()} is OUTSIDE the polygon boundary")
        print(f"   📍 Position ({lat:.4f}, {lon:.4f}) is outside the defined airspace")
    
    print(f"\n📄 Polygon file used: {polygon_file}")
    print(f"🌐 VATSIM data source: {VATSIM_API_URL}")

def main():
    """Main function to run the polygon testing."""
    # Check command line arguments
    if len(sys.argv) < 2:
        print("❌ Error: Please provide a polygon JSON file")
        print("Usage:")
        print("  # Test all aircraft:")
        print("  python test_polygon_with_live_vatsim_data.py <polygon_file.json>")
        print("  # Test specific flight:")
        print("  python test_polygon_with_live_vatsim_data.py <polygon_file.json> <flight_callsign>")
        sys.exit(1)
    
    polygon_file = sys.argv[1]
    
    # Check if a specific flight callsign was provided
    if len(sys.argv) >= 3:
        callsign = sys.argv[2]
        check_single_flight(polygon_file, callsign)
        return
    
    # Original functionality - test all aircraft
    print("🧪 TEMPORARY POLYGON TESTING SCRIPT")
    print("=" * 50)
    print("Testing live VATSIM aircraft positions against polygon boundary")
    print()
    
    # Load polygon coordinates
    polygon_coords = load_polygon_from_json(polygon_file)
    
    # Fetch live VATSIM data
    aircraft_list = fetch_live_vatsim_data()
    
    if not aircraft_list:
        print("❌ No aircraft data available")
        sys.exit(1)
    
    # Test aircraft against polygon
    results = test_aircraft_in_polygon(aircraft_list, polygon_coords)
    
    # Print summary
    print_summary(results)
    
    # Save detailed results to file
    output_file = "polygon_test_results.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Detailed results saved to: {output_file}")
    except Exception as e:
        print(f"⚠️  Could not save results: {e}")
    
    print(f"\n🎯 Polygon testing complete!")
    print(f"📄 Polygon file used: {polygon_file}")
    print(f"🌐 VATSIM data source: {VATSIM_API_URL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
