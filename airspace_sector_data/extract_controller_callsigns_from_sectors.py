#!/usr/bin/env python3
"""
Extract Controller Callsigns List from VATSIM Sectors.xml

This script extracts callsigns with frequencies as a list with filtering rules:
- For callsigns ending 'CTR' or 'FSS', only keep those starting 'ML' or 'BN'
- Retain everything else from the callsign field
- Output format: "CALLSIGN, FREQUENCY" (e.g., "ML-BIK_CTR, 125.000")
"""

import xml.etree.ElementTree as ET
import sys
from pathlib import Path


def extract_callsigns_list(xml_file_path: str) -> list:
    """Extract callsigns with frequencies as a list with filtering rules."""
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
    
    callsigns_with_freq = []
    
    # Process all sectors
    for sector in root.findall('.//Sector'):
        callsign = sector.get('Callsign', '')
        frequency = sector.get('Frequency', '')
        
        if callsign and frequency:
            # Apply filtering rules
            if callsign.endswith('_CTR') or callsign.endswith('_FSS'):
                # Only keep CTR/FSS callsigns starting with ML or BN
                if callsign.startswith('ML-') or callsign.startswith('BN-'):
                    entry = f"{callsign}, {frequency}"
                    if entry not in callsigns_with_freq:
                        callsigns_with_freq.append(entry)
            else:
                # Retain all other callsigns
                entry = f"{callsign}, {frequency}"
                if entry not in callsigns_with_freq:
                    callsigns_with_freq.append(entry)
    
    return sorted(callsigns_with_freq)


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
    
    # Print all callsigns with frequencies to console
    print(f"\nAll callsigns with frequencies:")
    for entry in callsigns:
        print(f"  {entry}")


if __name__ == "__main__":
    main()

