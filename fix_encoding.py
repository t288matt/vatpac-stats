#!/usr/bin/env python3
"""
Script to fix encoding issues in the ATC test file.
Replaces problematic characters with proper UTF-8 equivalents.
"""

import re

def fix_encoding():
    # Read the problematic file
    with open('tests/atc_detection_performance/test_atc_identical_input_validation.py', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
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
    
    # Write the fixed content back
    with open('tests/atc_detection_performance/test_atc_identical_input_validation.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Encoding issues fixed!")
    print("Replaced problematic characters with proper UTF-8 equivalents")

if __name__ == "__main__":
    fix_encoding()
