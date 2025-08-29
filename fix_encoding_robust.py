#!/usr/bin/env python3
"""
Robust script to fix encoding issues in the ATC test file.
Handles null bytes, BOM, and problematic characters.
"""

import re

def fix_encoding_robust():
    # Read the file as binary first to handle BOM and null bytes
    with open('tests/atc_detection_performance/test_atc_identical_input_validation.py', 'rb') as f:
        content_bytes = f.read()
    
    # Remove BOM if present
    if content_bytes.startswith(b'\xef\xbb\xbf'):
        content_bytes = content_bytes[3:]
    
    # Remove null bytes
    content_bytes = content_bytes.replace(b'\x00', b'')
    
    # Decode to string, ignoring errors
    try:
        content = content_bytes.decode('utf-8', errors='ignore')
    except UnicodeDecodeError:
        # Try other encodings
        try:
            content = content_bytes.decode('latin-1', errors='ignore')
        except:
            content = content_bytes.decode('cp1252', errors='ignore')
    
    # Define character replacements
    replacements = {
        # Replace problematic characters with proper ones
        '­ƒöì': '🔍',
        '­ƒôè': '📊', 
        '­ƒÜÇ': '🚀',
        '­ƒôê': '📈',
        '­ƒöä': '🔍',
        '­ƒÄ»': '🎯',
        '­ƒÆ¥': '💾',
        'Ô£à': '✅',
        'ÔØî': '❌',
        'ÔåÆ': '→',
        'ÔÅ░': '⏰',
        '­ƒôí': '📡'
    }
    
    # Apply replacements
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Add encoding declaration at the top
    if '# -*- coding: utf-8 -*-' not in content:
        content = content.replace('#!/usr/bin/env python3', '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-')
    
    # Write the fixed content back with proper UTF-8 encoding
    with open('tests/atc_detection_performance/test_atc_identical_input_validation.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    
    print("✅ Robust encoding fix completed!")
    print("Removed BOM, null bytes, and replaced problematic characters")

if __name__ == "__main__":
    fix_encoding_robust()
