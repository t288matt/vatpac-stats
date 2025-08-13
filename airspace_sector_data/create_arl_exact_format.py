#!/usr/bin/env python3
"""
Extract Every Sector to Individual GeoJSON Files
===============================================
This script extracts every sector from the processed data into its own GeoJSON file
"""

import json
import os

def extract_all_sectors():
    """Extract every sector to its own GeoJSON file"""
    
    # Input file path
    input_file = "processed_sectors/australian_sectors_responsible.json"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        print("   Please run process_australian_sectors.py first")
        return
    
    # Read the processed sectors data
    try:
        with open(input_file, 'r') as f:
            sectors_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading {input_file}: {e}")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs("individual_sectors", exist_ok=True)
    
    print(f"📁 Processing {len(sectors_data)} sectors...")
    print("=" * 60)
    
    successful_extractions = 0
    
    for sector in sectors_data:
        sector_name = sector.get('name', 'UNKNOWN')
        sector_desc = sector.get('full_name', 'Unknown Sector')
        callsign = sector.get('callsign', '')
        boundary_points = len(sector.get('boundaries', []))
        
        print(f"Processing: {sector_name} ({sector_desc})")
        print(f"  📞 Callsign: {callsign}")
        print(f"  📍 Boundary Points: {boundary_points}")
        
        # Create the GeoJSON structure - EXACT format matching arl_sector_exact.geojson
        # The reference file has: type: "Polygon", coordinates: [[[lon, lat], [lon, lat], ...]]
        # We need to convert from [lat, lon] to [lon, lat] format and match exact precision
        boundaries = sector.get('boundaries', [])
        converted_coordinates = []
        
        for coord in boundaries:
            lat, lon = coord  # Original format is [lat, lon]
            # Convert to [lon, lat] format and match exact precision from reference
            # Round to match the exact values in arl_sector_exact.geojson
            converted_coordinates.append([round(lon, 6), round(lat, 6)])
        
        geojson = {
            "type": "Polygon",
            "coordinates": [converted_coordinates]
        }
        
        # Save the individual GeoJSON file
        output_file = f"individual_sectors/{sector_name}_sector.geojson"
        try:
            with open(output_file, 'w') as f:
                json.dump(geojson, f, indent=2)
            
            file_size = os.path.getsize(output_file)
            print(f"  ✅ Created: {output_file}")
            print(f"     Size: {file_size} bytes")
            successful_extractions += 1
            
        except Exception as e:
            print(f"  ❌ Error creating {output_file}: {e}")
        
        print()  # Empty line for readability
    
    print("=" * 60)
    print(f"🎯 EXTRACTION COMPLETE")
    print(f"✅ Successfully extracted: {successful_extractions} sectors")
    print(f"📁 Output directory: individual_sectors/")
    print(f"📋 Files created:")
    
    # List all created files
    if os.path.exists("individual_sectors"):
        files = sorted(os.listdir("individual_sectors"))
        for file in files:
            if file.endswith('.geojson'):
                file_path = os.path.join("individual_sectors", file)
                file_size = os.path.getsize(file_path)
                print(f"   • {file} ({file_size} bytes)")

if __name__ == "__main__":
    print("Extract Every Sector to Individual GeoJSON Files")
    print("=" * 60)
    extract_all_sectors()
