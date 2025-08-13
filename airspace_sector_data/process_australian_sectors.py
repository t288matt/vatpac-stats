#!/usr/bin/env python3
"""
Australian Sector Processing Script - Save Results Version

This script processes VATSYS XML sector files to extract Australian airspace sector data
and saves the results to files for one-off manual processing and analysis.

Author: VATSIM Data Project Team
Date: January 2025
Status: Production Ready - One-off Processing Version
"""

import xml.etree.ElementTree as ET
import re
import json
import os

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
        volumes_tree = ET.parse('../external-data/Volumes.xml')
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

def save_to_json(sectors, output_file):
    """Save processed sectors to JSON file"""
    try:
        # Convert coordinates to lists for JSON serialization
        json_sectors = []
        for sector in sectors:
            json_sector = sector.copy()
            # Convert coordinate tuples to lists for JSON compatibility
            json_sector['boundaries'] = [[lat, lon] for lat, lon in sector['boundaries']]
            json_sectors.append(json_sector)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_sectors, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(sectors)} sectors to {output_file}")
        return True
    except Exception as e:
        print(f"❌ Error saving to JSON: {e}")
        return False



def process_australian_sectors():
    """Main processing function - find and process Australian sectors"""
    
    print("Processing Australian Sector Files - Save Results Version")
    print("=" * 60)
    print()
    
    try:
        # Load Sectors.xml
        sectors_tree = ET.parse('../external-data/Sectors.xml')
        sectors_root = sectors_tree.getroot()
        
        # Find all Sector elements
        sectors = sectors_root.findall('.//Sector')
        
        print(f"Total sectors found: {len(sectors)}")
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
        
        # Display summary
        print(f"Found {len(matching_sectors)} Australian domestic FSS/CTR standalone sectors")
        print("-" * 60)
        
        for i, sector in enumerate(matching_sectors, 1):
            print(f"{i:2d}. {sector['name']:8} - {sector['full_name']}")
            print(f"     Callsign: {sector['callsign']}")
            print(f"     Frequency: {sector['frequency']}")
            print(f"     Boundary Points: {len(sector['boundaries'])}")
            if sector['responsible_sectors']:
                print(f"     Responsible for: {sector['responsible_sectors']}")
            print()
        
        # Save results to JSON file only
        print("Saving results to JSON file...")
        print("-" * 40)
        
        # Create output directory if it doesn't exist
        output_dir = "processed_sectors"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save to JSON (overwrites existing file)
        json_file = f"{output_dir}/australian_sectors.json"
        
        if save_to_json(matching_sectors, json_file):
            print(f"✅ Successfully saved {len(matching_sectors)} sectors to {json_file}")
        else:
            print(f"❌ Failed to save JSON file")
        
        print()
        
        return matching_sectors
        
    except Exception as e:
        print(f"❌ Error processing sectors: {e}")
        return []

if __name__ == "__main__":
    # Process sectors and save results
    sectors = process_australian_sectors()
    
    if sectors:
        print("🎯 Processing completed successfully!")
        print(f"📊 Total sectors processed: {len(sectors)}")
        print(f"🗺️  Total boundary points: {sum(len(s['boundaries']) for s in sectors)}")
    else:
        print("❌ Processing failed - no sectors found")
