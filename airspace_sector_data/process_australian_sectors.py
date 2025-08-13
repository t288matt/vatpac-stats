#!/usr/bin/env python3
"""
Australian Sector Processing Script - Responsible Sectors Approach

This script processes VATSYS XML sector files to extract Australian airspace sector data
using the new ResponsibleSectors approach. It only processes sectors that have:
1. A <ResponsibleSectors> section
2. Callsigns starting with "ML-" or "BN-" and ending with "_CTR" or "_FSS"

The script combines the main sector polygon with all its responsible sector polygons
to create a single outer perimeter (convex hull) for each sector.

Author: VATSIM Data Project Team
Date: January 2025
Status: New Implementation - Responsible Sectors Approach
"""

import xml.etree.ElementTree as ET
import re
import json
import os
from shapely.geometry import Polygon
from shapely.ops import unary_union

def parse_coordinate(coord_str):
    """Parse coordinate string from Volumes.xml format (e.g., -343848.000+1494851.000)"""
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
    
    # Determine format based on number of digits
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
    
    For volumes with comma-separated boundaries, only takes the first one
    (e.g., "HUO,HUO_TMA_CAP" -> only "HUO")
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
                                                    
                                                    if lat is not None and lon is not None:
                                                        boundary_coords.append((lon, lat))  # Note: Shapely uses (x,y) = (lon,lat)
                                    
                                    # Create polygon from this boundary if we have enough coordinates
                                    if len(boundary_coords) >= 3:
                                        try:
                                            polygon = Polygon(boundary_coords)
                                            if polygon.is_valid:
                                                return polygon
                                        except Exception as e:
                                            print(f"Warning: Could not create polygon for boundary {primary_boundary_name}: {e}")
                                    
                                break  # Found Boundaries element, no need to check other children
                        
                        break  # Found volume, no need to check other volumes
                
                break  # Found volume, no need to check other volumes
        
        return None
        
    except Exception as e:
        print(f"Error parsing volume {volume_name}: {e}")
        return None

def should_process_sector(sector):
    """
    Determine if a sector should be processed based on criteria:
    1. Has a <ResponsibleSectors> section
    2. Callsign starts with "ML-" or "BN-"
    3. Callsign ends with "_CTR" or "_FSS"
    """
    # Check if sector has ResponsibleSectors
    has_responsible = False
    for child in sector:
        if child.tag == 'ResponsibleSectors':
            has_responsible = True
            break
    
    if not has_responsible:
        return False
    
    # Check callsign pattern
    callsign = sector.get('Callsign', '')
    if not callsign:
        return False
    
    # Must start with "ML-" or "BN-" and end with "_CTR" or "_FSS"
    if not (callsign.startswith('ML-') or callsign.startswith('BN-')):
        return False
    
    if not (callsign.endswith('_CTR') or callsign.endswith('_FSS')):
        return False
    
    return True

def get_primary_volume(sector):
    """
    Extract the primary volume name from a sector's Volumes section.
    For comma-separated volumes, only takes the first one.
    """
    for child in sector:
        if child.tag == 'Volumes' and child.text:
            volumes = [vol.strip() for vol in child.text.split(',')]
            return volumes[0]  # Only take the first volume
    return None

def get_responsible_sectors(sector):
    """
    Extract the list of responsible sector names from a sector's ResponsibleSectors section.
    """
    for child in sector:
        if child.tag == 'ResponsibleSectors' and child.text:
            return [name.strip() for name in child.text.split(',')]
    return []

def combine_sector_polygons(main_sector_name, responsible_sector_names):
    """
    Combine the main sector polygon with all responsible sector polygons
    to create a single outer perimeter (convex hull).
    """
    all_polygons = []
    
    # Get main sector polygon
    main_polygon = get_volume_boundaries(main_sector_name)
    if main_polygon:
        all_polygons.append(main_polygon)
        print(f"  ✅ Main sector {main_sector_name}: {len(main_polygon.exterior.coords)} points")
    else:
        print(f"  ❌ Main sector {main_sector_name}: No coordinates found")
    
    # Get responsible sector polygons
    for resp_sector in responsible_sector_names:
        resp_polygon = get_volume_boundaries(resp_sector)
        if resp_polygon:
            all_polygons.append(resp_polygon)
            print(f"  ✅ Responsible sector {resp_sector}: {len(resp_polygon.exterior.coords)} points")
        else:
            print(f"  ❌ Responsible sector {resp_sector}: No coordinates found")
    
    # Combine all polygons and extract outer perimeter
    if len(all_polygons) >= 2:
        try:
            # Union all polygons to create combined shape
            combined_polygon = unary_union(all_polygons)
            
            # USE SHAPELY'S BUILT-IN FEATURES: Get the actual coordinates properly
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
            
            # Convert back to (lat, lon) format and remove duplicates
            final_boundaries = []
            seen = set()
            for coord in exterior_coords:
                lon, lat = coord  # Shapely returns (x,y) = (lon,lat)
                coord_tuple = (lat, lon)  # Convert back to (lat, lon)
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
                    return [(lat, lon) for lon, lat in coords]
    
    elif len(all_polygons) == 1:
        # Only one polygon, return its coordinates
        polygon = all_polygons[0]
        if hasattr(polygon, 'exterior'):
            coords = list(polygon.exterior.coords)
            return [(lat, lon) for lon, lat in coords]
    
    return []

def process_australian_sectors():
    """
    Main function to process Australian sectors using the new ResponsibleSectors approach.
    Only processes sectors that meet the criteria and have coordinate data.
    """
    print("Processing Australian Sectors - Responsible Sectors Approach")
    print("=" * 60)
    
    try:
        # Load Sectors.xml
        sectors_tree = ET.parse('Sectors.xml')
        sectors_root = sectors_tree.getroot()
        
        processed_sectors = []
        
        # Process each sector
        for sector in sectors_root.findall('.//Sector'):
            sector_name = sector.get('Name')
            full_name = sector.get('FullName')
            callsign = sector.get('Callsign')
            
            # Check if sector should be processed
            if not should_process_sector(sector):
                continue
            
            # Get primary volume and responsible sectors
            primary_volume = get_primary_volume(sector)
            responsible_sectors = get_responsible_sectors(sector)
            
            if not primary_volume:
                continue
            
            print(f"\nProcessing sector: {sector_name} ({full_name})")
            print(f"  Callsign: {callsign}")
            print(f"  📍 Primary volume: {primary_volume}")
            print(f"  🔗 Responsible sectors: {', '.join(responsible_sectors)}")
            
            # Combine polygons
            combined_boundaries = combine_sector_polygons(primary_volume, responsible_sectors)
            
            if combined_boundaries:
                processed_sectors.append({
                    'name': sector_name,
                    'full_name': full_name,
                    'callsign': callsign,
                    'primary_volume': primary_volume,
                    'responsible_sectors': responsible_sectors,
                    'boundaries': combined_boundaries,
                    'boundary_count': len(combined_boundaries)
                })
                print(f"  ✅ Successfully processed with {len(combined_boundaries)} boundary points")
        
        # Save results
        os.makedirs('processed_sectors', exist_ok=True)
        
        # Save processed sectors
        with open('processed_sectors/australian_sectors_responsible.json', 'w', encoding='utf-8') as f:
            json.dump(processed_sectors, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"\n" + "=" * 60)
        print(f"PROCESSING COMPLETE")
        print(f"=" * 60)
        print(f"✅ Successfully processed: {len(processed_sectors)} sectors")
        print(f"📁 Output file:")
        print(f"   - processed_sectors/australian_sectors_responsible.json")
        
        # Show processed sectors
        if processed_sectors:
            print(f"\nProcessed sectors:")
            for sector in processed_sectors:
                print(f"  • {sector['name']} ({sector['full_name']}): {sector['boundary_count']} points")
        
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
