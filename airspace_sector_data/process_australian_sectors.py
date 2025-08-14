#!/usr/bin/env python3
"""
Australian Sector Processing Script - Simplified Sector Hierarchy Approach

This script processes Australian airspace sector data using a simple SectorHierarchy.txt file
that defines main sectors and their subsectors. It reads coordinates from Volumes.xml and
outputs a combined GeoJSON file with each sector as a separate Feature.

Author: VATSIM Data Project Team
Date: January 2025
Status: Simplified Implementation - Sector Hierarchy Approach
"""

import xml.etree.ElementTree as ET
import json
import os
from shapely.geometry import Polygon
from shapely.ops import unary_union

def parse_coordinate(coord_str):
    """Parse coordinate string from Volumes.xml format - handles both DDMMSS.SSSS and decimal degrees"""
    if not coord_str or '.' not in coord_str:
        return None
    
    # Handle positive coordinates (remove + sign for parsing)
    is_negative = coord_str.startswith('-')
    if coord_str.startswith('+'):
        coord_str = coord_str[1:]  # Remove + sign
    elif is_negative:
        coord_str = coord_str[1:]  # Remove - sign for parsing
    
    # Find the decimal point
    decimal_pos = coord_str.find('.')
    
    # Extract digits before decimal point
    before_decimal = coord_str[:decimal_pos]
    
    # Check if this is already in decimal degrees format (e.g., -12.665278)
    if len(before_decimal) <= 3:  # Likely decimal degrees
        try:
            decimal_degrees = float(coord_str)
            # Apply negative sign if original was negative
            if is_negative:
                decimal_degrees = -decimal_degrees
            return decimal_degrees
        except ValueError:
            pass  # Fall through to DDMMSS parsing
    
    # Determine DDMMSS format based on number of digits
    if len(before_decimal) == 7:  # DDDMMSS
        # Format: DDDMMSS.SSSS
        degrees = int(before_decimal[:3])
        minutes = int(before_decimal[3:5])
        seconds = int(before_decimal[5:7])
        decimal_seconds = float(coord_str[decimal_pos:])
        total_seconds = seconds + decimal_seconds
    elif len(before_decimal) == 6:  # DDMMSS
        # Format: DDMMSS.SSSS
        degrees = int(before_decimal[:2])
        minutes = int(before_decimal[2:4])
        seconds = int(before_decimal[4:6])
        decimal_seconds = float(coord_str[decimal_pos:])
        total_seconds = seconds + decimal_seconds
    else:
        return None
    
    # Convert to decimal degrees
    decimal_degrees = degrees + (minutes / 60.0) + (total_seconds / 3600.0)
    
    # Apply negative sign if original was negative
    if is_negative:
        decimal_degrees = -decimal_degrees
    
    return decimal_degrees

def get_volume_boundaries(volume_name):
    """
    Extract boundary coordinates for a given volume from Volumes.xml
    """
    try:
        volumes_tree = ET.parse('Volumes.xml')
        volumes_root = volumes_tree.getroot()
        
        # Find the volume with matching name
        for volume in volumes_root.findall('.//Volume'):
            if volume.get('Name') == volume_name:
                # Get the boundary names from the Boundaries element
                for child in list(volume):
                    if child.tag == 'Boundaries' and child.text:
                        # Split comma-separated boundary names and take only the first one
                        boundary_names = [name.strip() for name in child.text.split(',')]
                        primary_boundary_name = boundary_names[0]  # Only take the first one
                        
                        # Search for the actual boundary coordinates using the boundary name
                        for boundary in volumes_root.findall('.//Boundary'):
                            if boundary.get('Name') == primary_boundary_name:
                                coords_text = boundary.text.strip() if boundary.text else ''
                                if coords_text:
                                    # Parse coordinates for this boundary
                                    boundary_coords = []
                                    coord_pairs = [pair.strip() for pair in coords_text.split('/') if pair.strip()]
                                    
                                    # Debug: Print what we found for TBD
                                    if volume_name == 'TBD':
                                        print(f"    🔍 DEBUG: Found boundary '{primary_boundary_name}' with {len(coord_pairs)} coordinate pairs")
                                        print(f"    🔍 DEBUG: First few coords: {coord_pairs[:3]}")
                                    
                                    for pair in coord_pairs:
                                        # Parse the coordinate pair (e.g., "-342011.000+1382231.000")
                                        if '+' in pair and '-' in pair:
                                            # Handle mixed signs (negative lat, positive lon)
                                            if pair.startswith('-'):
                                                # Find the position of the + sign
                                                plus_pos = pair.find('+')
                                                if plus_pos > 0:
                                                    lat_str = pair[:plus_pos]
                                                    lon_str = pair[plus_pos:]
                                                    
                                                    # Parse coordinates
                                                    lat = parse_coordinate(lat_str)
                                                    lon = parse_coordinate(lon_str)
                                                    
                                                    # Debug: Print parsing results for TBD
                                                    if volume_name == 'TBD':
                                                        print(f"    🔍 DEBUG: Parsed '{pair}' -> lat:{lat}, lon:{lon}")
                                                    
                                                    if lat is not None and lon is not None:
                                                        boundary_coords.append((lon, lat))  # Shapely uses (x,y) = (lon,lat) for GeoJSON compatibility
                                    
                                    # Debug: Print final results for TBD
                                    if volume_name == 'TBD':
                                        print(f"    🔍 DEBUG: Total valid coordinates: {len(boundary_coords)}")
                                        print(f"    🔍 DEBUG: First 3 coords: {boundary_coords[:3]}")
                                        print(f"    🔍 DEBUG: Last 3 coords: {boundary_coords[-3:]}")
                                        # Check if polygon is closed
                                        if boundary_coords[0] == boundary_coords[-1]:
                                            print(f"    🔍 DEBUG: Polygon is closed ✅")
                                        else:
                                            print(f"    🔍 DEBUG: Polygon is NOT closed ❌")
                                            print(f"    🔍 DEBUG: First: {boundary_coords[0]}, Last: {boundary_coords[-1]}")
                                    
                                    # Create polygon from this boundary if we have enough coordinates
                                    if len(boundary_coords) >= 3:
                                        try:
                                            # Debug: Print polygon creation attempt for TBD
                                            if volume_name == 'TBD':
                                                print(f"    🔍 DEBUG: Attempting to create polygon with {len(boundary_coords)} coordinates")
                                            
                                            polygon = Polygon(boundary_coords)
                                            
                                            # Debug: Check polygon validity for TBD
                                            if volume_name == 'TBD':
                                                print(f"    🔍 DEBUG: Polygon created, valid: {polygon.is_valid}")
                                            
                                            if polygon.is_valid:
                                                return polygon
                                            else:
                                                # Polygon is invalid, try coordinate simplification first
                                                if volume_name == 'TBD':
                                                    print(f"    🔍 DEBUG: Polygon invalid, trying coordinate simplification...")
                                                
                                                try:
                                                    # Simplify the coordinate sequence to reduce complexity
                                                    from shapely.geometry import LineString
                                                    line = LineString(boundary_coords)
                                                    simplified_line = line.simplify(tolerance=0.001, preserve_topology=True)
                                                    
                                                    # Extract simplified coordinates
                                                    simplified_coords = list(simplified_line.coords)
                                                    
                                                    if volume_name == 'TBD':
                                                        print(f"    🔍 DEBUG: Simplified from {len(boundary_coords)} to {len(simplified_coords)} coordinates")
                                                    
                                                    # Try creating polygon with simplified coordinates
                                                    simplified_polygon = Polygon(simplified_coords)
                                                    if simplified_polygon.is_valid:
                                                        if volume_name == 'TBD':
                                                            print(f"    🔍 DEBUG: Successfully created polygon with simplified coordinates")
                                                        return simplified_polygon
                                                    else:
                                                        if volume_name == 'TBD':
                                                            print(f"    🔍 DEBUG: Simplified polygon still invalid")
                                                        
                                                except Exception as simplify_error:
                                                    if volume_name == 'TBD':
                                                        print(f"    🔍 DEBUG: Coordinate simplification failed: {simplify_error}")
                                                
                                                # Try other fallback methods
                                                try:
                                                    # Try buffer with 0 distance to clean up geometry
                                                    fixed_polygon = polygon.buffer(0)
                                                    if fixed_polygon.is_valid and hasattr(fixed_polygon, 'exterior'):
                                                        if volume_name == 'TBD':
                                                            print(f"    🔍 DEBUG: Fixed invalid polygon using buffer(0)")
                                                        return fixed_polygon
                                                except Exception as buffer_error:
                                                    if volume_name == 'TBD':
                                                        print(f"    🔍 DEBUG: Buffer fix failed: {buffer_error}")
                                                
                                                # Try reversing coordinate order
                                                try:
                                                    reversed_coords = list(reversed(boundary_coords))
                                                    reversed_polygon = Polygon(reversed_coords)
                                                    if reversed_polygon.is_valid:
                                                        if volume_name == 'TBD':
                                                            print(f"    🔍 DEBUG: Fixed invalid polygon by reversing coordinates")
                                                        return reversed_polygon
                                                except Exception as reverse_error:
                                                    if volume_name == 'TBD':
                                                        print(f"    🔍 DEBUG: Reverse fix failed: {reverse_error}")
                                        
                                        except Exception as e:
                                            # Initial polygon creation failed completely
                                            if volume_name == 'TBD':
                                                print(f"    🔍 DEBUG: Initial polygon creation failed: {e}")
                                        
                                        # If we get here, all methods failed
                                        if volume_name == 'TBD':
                                            print(f"    🔍 DEBUG: All polygon creation methods failed")
                                        
                                        print(f"Warning: Could not create polygon for boundary {primary_boundary_name}")
                                    
                                break  # Found Boundaries element, no need to check other children
                        
                        break  # Found volume, no need to check other volumes
                
                break  # Found volume, no need to check other volumes
        
        return None
        
    except Exception as e:
        print(f"Error parsing volume {volume_name}: {e}")
        return None

def read_sector_hierarchy():
    """
    Read the sector hierarchy from SectorHierarchy.txt
    Returns a dictionary mapping main sectors to their subsectors
    """
    sector_hierarchy = {}
    
    try:
        with open('SectorHierarchy.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    main_sector, subsectors_str = line.split(':', 1)
                    main_sector = main_sector.strip()
                    subsectors = [s.strip() for s in subsectors_str.split(',')]
                    sector_hierarchy[main_sector] = subsectors
        
        print(f"✅ Loaded {len(sector_hierarchy)} sectors from SectorHierarchy.txt")
        return sector_hierarchy
        
    except Exception as e:
        print(f"❌ Error reading SectorHierarchy.txt: {e}")
        return {}

def combine_sector_polygons(sector_names):
    """
    Combine multiple sector polygons to create a single unified boundary
    """
    all_polygons = []
    
    for sector_name in sector_names:
        polygon = get_volume_boundaries(sector_name)
        if polygon:
            all_polygons.append(polygon)
            print(f"  ✅ Sector {sector_name}: {len(polygon.exterior.coords)} points")
        else:
            print(f"  ❌ Sector {sector_name}: No coordinates found")
    
    # Combine all polygons and extract outer perimeter
    if len(all_polygons) >= 2:
        try:
            # Union all polygons to create combined shape
            combined_polygon = unary_union(all_polygons)
            
            # Get the actual coordinates properly
            if hasattr(combined_polygon, 'exterior'):
                # Single polygon - extract the exterior ring coordinates
                exterior_coords = list(combined_polygon.exterior.coords)
            else:
                # Multi-polygon - use Shapely's built-in methods to get the true outer boundary
                try:
                    # Get the boundary and extract coordinates from all parts
                    boundary = combined_polygon.boundary
                    
                    if hasattr(boundary, 'coords'):
                        # Single line string - extract all coordinates
                        exterior_coords = list(boundary.coords)
                    else:
                        # Multiple line strings - collect coordinates from all boundary parts
                        all_coords = []
                        for geom in boundary.geoms:
                            if hasattr(geom, 'coords'):
                                coords = list(geom.coords)
                                all_coords.extend(coords)
                        
                        # Remove duplicates while preserving order
                        seen = set()
                        exterior_coords = []
                        for coord in all_coords:
                            if coord not in seen:
                                seen.add(coord)
                                exterior_coords.append(coord)
                except Exception as e:
                    # Fallback: extract from individual polygons
                    if hasattr(combined_polygon, 'geoms'):
                        all_coords = []
                        for geom in combined_polygon.geoms:
                            if hasattr(geom, 'exterior'):
                                coords = list(geom.exterior.coords)
                                all_coords.extend(coords)
                        
                        # Remove duplicates
                        seen = set()
                        exterior_coords = []
                        for coord in all_coords:
                            if coord not in seen:
                                seen.add(coord)
                                exterior_coords.append(coord)
                    else:
                        exterior_coords = []
            
            # Convert back to (lon, lat) format for GeoJSON and remove duplicates
            final_boundaries = []
            seen = set()
            for coord in exterior_coords:
                lon, lat = coord  # Shapely returns (x,y) = (lon,lat) in our case
                coord_tuple = (lon, lat)  # Keep as (lon, lat) for GeoJSON standard
                if coord_tuple not in seen:
                    final_boundaries.append(coord_tuple)
                    seen.add(coord_tuple)
            
            print(f"  🎯 Combined polygon: {len(final_boundaries)} outer perimeter points")
            return final_boundaries
            
        except Exception as e:
            print(f"  ❌ Error combining polygons: {e}")
            # Fallback: return coordinates from first valid polygon
            if all_polygons:
                polygon = all_polygons[0]
                if hasattr(polygon, 'exterior'):
                    coords = list(polygon.exterior.coords)
                    return [(lon, lat) for lon, lat in coords]
    
    elif len(all_polygons) == 1:
        # Only one polygon, return its coordinates
        polygon = all_polygons[0]
        if hasattr(polygon, 'exterior'):
            coords = list(polygon.exterior.coords)
            return [(lon, lat) for lon, lat in coords]
    
    return []

def create_geojson_feature(sector_name, boundaries):
    """
    Create a GeoJSON Feature for a sector
    """
    if not boundaries or len(boundaries) < 3:
        return None
    
    # Ensure the polygon is closed (first and last points are the same)
    if boundaries[0] != boundaries[-1]:
        boundaries.append(boundaries[0])
    
    feature = {
        "type": "Feature",
        "properties": {
            "name": sector_name,
            "sector_id": sector_name
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [boundaries]
        }
    }
    
    return feature

def process_australian_sectors():
    """
    Main function to process Australian sectors using the simplified SectorHierarchy.txt approach
    """
    print("Processing Australian Sectors - Simplified Sector Hierarchy Approach")
    print("=" * 70)
    
    try:
        # Read sector hierarchy
        sector_hierarchy = read_sector_hierarchy()
        if not sector_hierarchy:
            return False
        
        processed_sectors = []
        geojson_features = []
        
        # Process each main sector
        for main_sector, subsectors in sector_hierarchy.items():
            print(f"\nProcessing sector: {main_sector}")
            print(f"  📍 Subsectors: {', '.join(subsectors)}")
            
            # Combine polygons for all subsectors
            combined_boundaries = combine_sector_polygons(subsectors)
            
            if combined_boundaries:
                # Create GeoJSON feature
                feature = create_geojson_feature(main_sector, combined_boundaries)
                if feature:
                    geojson_features.append(feature)
                
                processed_sectors.append({
                    'name': main_sector,
                    'subsectors': subsectors,
                    'boundaries': combined_boundaries,
                    'boundary_count': len(combined_boundaries)
                })
                print(f"  ✅ Successfully processed with {len(combined_boundaries)} boundary points")
            else:
                print(f"  ❌ No valid boundaries found")
        
        # Create GeoJSON structure
        geojson = {
            "type": "FeatureCollection",
            "features": geojson_features
        }
        
        # Save results
        os.makedirs('processed_sectors', exist_ok=True)
        
        # Save combined GeoJSON file
        output_file = 'processed_sectors/australian_airspace_sectors.geojson'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        # Save processed sectors data as JSON (for reference)
        with open('processed_sectors/australian_sectors_data.json', 'w', encoding='utf-8') as f:
            json.dump(processed_sectors, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"\n" + "=" * 70)
        print(f"PROCESSING COMPLETE")
        print(f"=" * 70)
        print(f"✅ Successfully processed: {len(processed_sectors)} sectors")
        print(f"📁 Output files:")
        print(f"   - {output_file}")
        print(f"   - processed_sectors/australian_sectors_data.json")
        
        # Show processed sectors
        if processed_sectors:
            print(f"\nProcessed sectors:")
            for sector in processed_sectors:
                print(f"  • {sector['name']}: {sector['boundary_count']} points ({len(sector['subsectors'])} subsectors)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing sectors: {e}")
        return False

if __name__ == "__main__":
    success = process_australian_sectors()
    
    if success:
        print("\n🎯 Australian sector processing completed successfully!")
        print("   Check the processed_sectors/ directory for output files.")
    else:
        print("\n❌ Australian sector processing failed!")
        print("   Check the error messages above for details.")