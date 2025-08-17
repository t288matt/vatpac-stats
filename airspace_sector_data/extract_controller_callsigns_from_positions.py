#!/usr/bin/env python3
"""
Extract Controller Callsigns List from VATSIM Positions.xml

This script extracts just the callsigns as a simple list.
"""

import xml.etree.ElementTree as ET
import sys
from pathlib import Path


def extract_callsigns_list(xml_file_path: str) -> list:
    """Extract callsigns as a simple list."""
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
    
    # Process all positions
    for position in root.findall('.//Position'):
        # Extract callsigns from ControllerInfo elements
        controller_infos = position.findall('ControllerInfo')
        for controller_info in controller_infos:
            callsign = controller_info.get('Callsign', '')
            if callsign and callsign not in callsigns:
                callsigns.append(callsign)
    
    return sorted(callsigns)


def main():
    """Main function."""
    script_dir = Path(__file__).parent
    xml_file = script_dir / "Positions.xml"
    
    if not xml_file.exists():
        print(f"Error: Positions.xml not found at {xml_file}")
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
