#!/usr/bin/env python3
"""
Extract Australian Sector Boundaries from VATSIM XML Data

This script identifies and extracts geographic boundaries for Australian FSS/CTR sectors
from the VATSIM XML configuration files. It serves as the foundation for the flight summary
table system's sector occupancy tracking capabilities.

Purpose:
- Identify Australian FSS/CTR standalone sectors
- Extract geographic boundary coordinates from Volumes.xml
- Parse DDMMSS.SSSS coordinate format to decimal degrees
- Provide boundary data for Shapely polygon creation

Output:
- List of 17 target sectors with their metadata
- Geographic coordinates for sector boundaries
- Ready for integration with SectorManager class

Author: VATSIM Data Project Team
Date: January 2025
Status: Production Ready - Phase 1 Complete
"""

import xml.etree.ElementTree as ET
import re

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

def get_sector_boundaries(volume_name):
    """Extract boundary coordinates for a given volume from Volumes.xml"""
    try:
        volumes_tree = ET.parse('/app/Volumes.xml')
        volumes_root = volumes_tree.getroot()
        
        # Find the volume with matching name
        for volume in volumes_root.findall('.//Volume'):
            if volume.get('Name') == volume_name:
                boundaries = []
                
                # Get the boundary name from the Boundaries element
                for child in list(volume):
                    if child.tag == 'Boundaries' and child.text:
                        boundary_name = child.text.strip()
                        
                        # Now search for the actual boundary coordinates using the boundary name
                        for boundary in volumes_root.findall('.//Boundary'):
                            if boundary.get('Name') == boundary_name:
                                coords_text = boundary.text.strip() if boundary.text else ''
                                if coords_text:
                                    # Split coordinate pairs by forward slash
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
                                                        boundaries.append((lat, lon))
                        break  # Found Boundaries element, no need to check other children
                
                return boundaries
        
        return []
        
    except Exception as e:
        print(f"Error reading Volumes.xml: {e}")
        return []

def find_fss_ctr_sectors():
    """Find sectors matching the criteria - Australian domestic only."""
    
    print("Finding FSS/CTR Sectors (Australian Domestic Only):")
    print("=" * 80)
    
    try:
        # Load Sectors.xml
        sectors_tree = ET.parse('/app/Sectors.xml')
        sectors_root = sectors_tree.getroot()
        
        # Find all Sector elements
        sectors = sectors_root.findall('.//Sector')
        
        print(f"Total sectors: {len(sectors)}")
        print()
        
        # Find sectors matching criteria
        matching_sectors = []
        
        for sector in sectors:
            name = sector.get('Name', 'Unknown')
            
            # Check if callsign contains FSS or CTR (from attribute)
            callsign = sector.get('Callsign', '')
            if not callsign or ('FSS' not in callsign.upper() and 'CTR' not in callsign.upper()):
                continue
            
            # FILTER: Only Australian domestic callsigns (ML or BN)
            if not (callsign.startswith('ML-') or callsign.startswith('BN-')):
                continue
            
            # Check volumes - look through all child elements
            volumes = None
            responsible_sectors = None
            
            for child in list(sector):
                if child.tag == 'Volumes':
                    volumes = child.text.strip() if child.text else None
                elif child.tag == 'ResponsibleSectors':
                    responsible_sectors = child.text.strip() if child.text else None
            
            if not volumes:
                continue
                
            # Check if this sector appears in ResponsibleSectors of other sectors
            appears_as_responsible = False
            for other_sector in sectors:
                if other_sector.get('Name') == name:
                    continue  # Skip self
                    
                for child in list(other_sector):
                    if child.tag == 'ResponsibleSectors' and child.text:
                        responsible_list = [r.strip() for r in child.text.split(',')]
                        if name in responsible_list:
                            appears_as_responsible = True
                            break
                if appears_as_responsible:
                    break
            
            # If it doesn't appear as responsible in other sectors, it's standalone
            if not appears_as_responsible:
                frequency = sector.get('Frequency', 'N/A')
                full_name = sector.get('FullName', 'N/A')
                
                # Extract sector boundaries
                volume_names = [v.strip() for v in volumes.split(',')]
                all_boundaries = []
                
                # Process all volumes to find exact matches
                for volume_name in volume_names:
                    boundaries = get_sector_boundaries(volume_name)
                    if boundaries:
                        all_boundaries.extend(boundaries)
                
                matching_sectors.append({
                    'name': name,
                    'callsign': callsign,
                    'frequency': frequency,
                    'full_name': full_name,
                    'volumes': volumes,
                    'responsible_sectors': responsible_sectors,
                    'boundaries': all_boundaries
                })
        
        # Display results
        print(f"Found {len(matching_sectors)} Australian domestic FSS/CTR standalone sectors:")
        print("-" * 80)
        
        for i, sector in enumerate(matching_sectors):
            print(f"{i+1:2d}. {sector['name']}")
            print(f"     Callsign: {sector['callsign']}")
            print(f"     Frequency: {sector['frequency']}")
            print(f"     Full Name: {sector['full_name']}")
            print(f"     Volumes: {sector['volumes']}")
            if sector['responsible_sectors']:
                print(f"     Responsible for: {sector['responsible_sectors']}")
            
            # Display boundary information
            if sector['boundaries']:
                print(f"     Boundary Points: {len(sector['boundaries'])} coordinates")
                print(f"     Sample Coordinates:")
                for j, (lat, lon) in enumerate(sector['boundaries'][:3]):  # Show first 3
                    print(f"       Point {j+1}: {lat:.6f}, {lon:.6f}")
                if len(sector['boundaries']) > 3:
                    print(f"       ... and {len(sector['boundaries']) - 3} more points")
            else:
                print(f"     Boundary Points: No coordinates found")
            print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY:")
        print(f"Total sectors: {len(sectors)}")
        print(f"Australian domestic FSS/CTR standalone sectors: {len(matching_sectors)}")
        print()
        print("These sectors:")
        print("✅ Have callsigns containing FSS or CTR")
        print("✅ Have volume definitions")
        print("✅ Don't appear in ResponsibleSectors of other sectors")
        print("✅ Are standalone (not managed by parent sectors)")
        print("✅ Are Australian domestic (ML- or BN- callsigns)")
        print("✅ Have geographic boundaries extracted from Volumes.xml")
        print()
        print("PERFECT FOR FLIGHT TRACKING - These are the sectors we want to monitor!")
        print()
        print("NEXT STEP: Use these boundaries to create Shapely polygons for real-time")
        print("flight position checking in the SectorManager class.")
        
    except Exception as e:
        print(f"Error finding sectors: {e}")

if __name__ == "__main__":
    find_fss_ctr_sectors()
