#!/usr/bin/env python3
"""
Simple script to remove BOM and null bytes from the test file.
"""

def simple_fix():
    # Read as binary
    with open('tests/atc_detection_performance/test_atc_identical_input_validation.py', 'rb') as f:
        content = f.read()
    
    # Remove BOM if present
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
        print("Removed BOM")
    
    # Remove null bytes
    if b'\x00' in content:
        content = content.replace(b'\x00', b'')
        print("Removed null bytes")
    
    # Write back
    with open('tests/atc_detection_performance/test_atc_identical_input_validation.py', 'wb') as f:
        f.write(content)
    
    print("File fixed!")

if __name__ == "__main__":
    simple_fix()
