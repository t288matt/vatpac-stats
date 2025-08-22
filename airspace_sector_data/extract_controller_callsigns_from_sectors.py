#!/usr/bin/env python3
"""
Extract Controller Callsigns List from VATSIM Sectors.xml

This script extracts callsigns as a simple list with filtering rules:
- For callsigns ending 'CTR' or 'FSS', only keep those starting 'ML' or 'BN'
- Retain everything else from the callsign field
- Output is a list of callsigns as text
"""

import xml.etree.ElementTree as ET
import sys
from pathlib import Path


def extract_callsigns_list(xml_file_path: str) -> list:
    """Extract callsigns as a simple list with filtering rules."""
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"File not found: {xml_file_path}")
        sys.exit(1)
    
    # Remove namespace for easier parsing
    for elem in root.iter():
        if elem.tag.startswith('{'):
            elem.tag = elem.tag.split('}', 1)[1]
    
    callsigns = []
    
    # Process all sectors
    for sector in root.findall('.//Sector'):
        callsign = sector.get('Callsign', '')
        if callsign:
            # Apply filtering rules
            if callsign.endswith('_CTR') or callsign.endswith('_FSS'):
                # Only keep CTR/FSS callsigns starting with ML or BN
                if callsign.startswith('ML-') or callsign.startswith('BN-'):
                    if callsign not in callsigns:
                        callsigns.append(callsign)
            else:
                # Retain all other callsigns
                if callsign not in callsigns:
                    callsigns.append(callsign)
    
    return sorted(callsigns)


def main():
    """Main function."""
    script_dir = Path(__file__).parent
    xml_file = script_dir / "Sectors.xml"
    
    if not xml_file.exists():
        print(f"Error: Sectors.xml not found at {xml_file}")
        sys.exit(1)
    
    print(f"Extracting callsigns from {xml_file}...")
    
    callsigns = extract_callsigns_list(str(xml_file))
    
    # Output as simple text file
    output_file = script_dir / "controller_callsigns_list.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for callsign in callsigns:
            f.write(f"{callsign}\n")
    
    print(f"Extraction complete!")
    print(f"Total callsigns: {len(callsigns)}")
    print(f"Output saved to: {output_file}")
    
    # Print all callsigns to console
    print(f"\nAll callsigns:")
    for callsign in callsigns:
        print(f"  {callsign}")


if __name__ == "__main__":
    main()

