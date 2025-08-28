# Frequency Filter Implementation Plan

## Overview
This document captures the investigation and implementation plan for adding frequency-based filtering to the VATSIM transceiver system, specifically to exclude transceivers with frequency 122.8 MHz.

## Investigation Findings

### Current Transceiver Filter Architecture
The system currently has two transceiver filters:
1. **Callsign Pattern Filter** (`CallsignPatternFilter`) - filters by callsign text (currently unused for transceivers)
2. **Geographic Boundary Filter** (`GeographicBoundaryFilter`) - filters by position (currently active)

### Frequency Format Analysis
Based on live database data, frequencies are stored consistently:

#### Database Storage Format
- **Storage**: `BigInteger` column storing frequency in **Hertz (Hz)**
- **Example**: 122.8 MHz = `122800000` Hz

#### Real Examples from Database

**Flight Transceivers (122.8 MHz)**
```
JST900: 122800020 Hz (122.800020 MHz)
MJX617: 122800020 Hz (122.800020 MHz)  
UAE1DP: 122800020 Hz (122.800020 MHz)
STV4: 122800020 Hz (122.800020 MHz)
MAS140: 122800020 Hz (122.800020 MHz)
```

**ATC Transceivers (122.8 MHz)**
```
BAW59: 122800020 Hz (122.800020 MHz) - entity_type: 'atc'
```

**SY_GND (Sydney Ground) - 121.7 MHz**
```
SY_GND: 121700000 Hz (121.700 MHz) - entity_type: 'atc'
- Position: -33.945337°, 151.18073° (Sydney Airport)
- Controllers: Noah Juno, Sunny Gao
```

### Key Findings
1. **Same Format**: Both flights and ATC use **identical frequency storage format**
2. **Precision**: Frequencies are stored with high precision (e.g., `122800020` Hz)
3. **No Difference**: There's no distinction between flight vs ATC frequency formats
4. **VATSIM API**: The `122800020` format comes directly from VATSIM API (not rounded)

## Implementation Options

### Option 1: Extend Existing Callsign Pattern Filter
**Modify `CallsignPatternFilter` to handle frequency patterns**

**Pros:**
- Reuses existing filter infrastructure
- Minimal code changes
- Consistent with current pattern-based approach
- Easy to configure via environment variables

**Cons:**
- Filter name becomes misleading (handles both callsigns and frequencies)

### Option 2: Create New Frequency Filter (RECOMMENDED)
**Create `FrequencyPatternFilter` class**

**Pros:**
- Clean separation of concerns
- Easy to extend for other frequency exclusions
- Clear naming
- Consistent with existing filter architecture

**Cons:**
- More code to maintain
- Additional filter initialization

### Option 3: Extend Geographic Boundary Filter
**Add frequency filtering to existing filter**

**Pros:**
- Single filter handles both frequency and location
- No new filter classes

**Cons:**
- Mixes frequency logic with geographic logic
- Less flexible for future frequency exclusions

## Recommended Implementation: Option 2

### Step 1: Create Frequency Pattern Filter

```python
# app/filters/frequency_pattern_filter.py
#!/usr/bin/env python3
"""
Frequency Pattern Filter Module

This module provides filtering for transceivers based on frequency patterns
that should be excluded from the system.
"""

import os
import logging
from typing import Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FrequencyPatternConfig:
    """Frequency pattern filter configuration"""
    enabled: bool = True
    excluded_frequencies: List[int] = None

class FrequencyPatternFilter:
    """
    Frequency Pattern Filter
    
    Filters out transceivers based on frequencies that should be excluded.
    Uses exact Hz matching for precise frequency filtering.
    """
    
    def __init__(self):
        """Initialize frequency pattern filter with configuration."""
        self.config = self._get_filter_config()
        self._setup_logging()
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'transceivers_included': 0,
            'transceivers_excluded': 0,
            'frequencies_configured': len(self.config.excluded_frequencies) if self.config.excluded_frequencies else 0
        }
        
        logger.info(f"Frequency pattern filter initialized - enabled: {self.config.enabled}")
        if self.config.excluded_frequencies:
            logger.info(f"Configured excluded frequencies: {', '.join(map(str, self.config.excluded_frequencies))}")
    
    def _get_filter_config(self) -> FrequencyPatternConfig:
        """Get filter configuration from environment variables"""
        # Get excluded frequencies from environment variable
        excluded_freqs_str = os.getenv("EXCLUDED_FREQUENCIES", "122800000")
        
        # Split by comma and convert to integers
        excluded_frequencies = []
        for freq_str in excluded_freqs_str.split(","):
            try:
                excluded_frequencies.append(int(freq_str.strip()))
            except ValueError:
                logger.warning(f"Invalid frequency value: {freq_str}")
        
        return FrequencyPatternConfig(
            enabled=True,  # Always enabled
            excluded_frequencies=excluded_frequencies
        )
    
    def _setup_logging(self):
        """Setup logging for the filter"""
        logger.setLevel(logging.INFO)
    
    def _should_exclude_frequency(self, frequency: int) -> bool:
        """
        Check if a frequency should be excluded.
        
        Args:
            frequency: The frequency in Hz to check
            
        Returns:
            True if frequency should be excluded, False otherwise
        """
        if not frequency or not self.config.excluded_frequencies:
            return False
        
        return frequency in self.config.excluded_frequencies
    
    def filter_transceivers_list(self, transceivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter transceivers list to exclude those with excluded frequencies.
        
        Args:
            transceivers: List of transceiver data dictionaries
            
        Returns:
            Filtered list of transceivers
        """
        if not self.config.enabled or not transceivers:
            return transceivers
        
        original_count = len(transceivers)
        
        # Use list comprehension for better performance
        filtered_transceivers = [
            transceiver for transceiver in transceivers
            if not self._should_exclude_frequency(transceiver.get('frequency'))
        ]
        
        excluded_count = original_count - len(filtered_transceivers)
        
        # Update statistics
        self.stats['total_processed'] += original_count
        self.stats['transceivers_included'] += len(filtered_transceivers)
        self.stats['transceivers_excluded'] += excluded_count
        
        if excluded_count > 0:
            logger.info(f"Frequency filter: {original_count} transceivers -> {len(filtered_transceivers)} transceivers (excluded {excluded_count})")
        
        return filtered_transceivers
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter statistics."""
        return {
            'enabled': self.config.enabled,
            'frequencies_configured': self.stats['frequencies_configured'],
            'total_processed': self.stats['total_processed'],
            'transceivers_included': self.stats['transceivers_included'],
            'transceivers_excluded': self.stats['transceivers_excluded'],
            'excluded_frequencies': self.config.excluded_frequencies
        }
    
    def get_filter_status(self) -> Dict[str, Any]:
        """Get filter status information."""
        return {
            'enabled': self.config.enabled,
            'excluded_frequencies': self.config.excluded_frequencies,
            'frequencies_configured': self.stats['frequencies_configured']
        }
```

### Step 2: Update Environment Configuration

```yaml
# docker-compose.yml
services:
  vatsim_app:
    environment:
      # ... existing config ...
      EXCLUDED_FREQUENCIES: "122800000"  # 122.8 MHz in Hz
```

### Step 3: Update Data Service

```python
# app/services/data_service.py
from app.filters.frequency_pattern_filter import FrequencyPatternFilter

class DataService:
    def __init__(self):
        # ... existing code ...
        
        # Initialize filters
        self.geographic_boundary_filter = GeographicBoundaryFilter()
        self.callsign_pattern_filter = CallsignPatternFilter()
        self.controller_callsign_filter = ControllerCallsignFilter()
        self.frequency_pattern_filter = FrequencyPatternFilter()  # NEW
    
    async def _process_transceivers(self, transceivers_data: List[Dict[str, Any]]) -> int:
        # ... existing code ...
        
        # Apply geographic boundary filtering
        if self.geographic_boundary_filter.config.enabled:
            filtered_transceivers = self.geographic_boundary_filter.filter_transceivers_list(transceivers_data)
        else:
            filtered_transceivers = transceivers_data
        
        # NEW: Apply frequency filtering
        filtered_transceivers = self.frequency_pattern_filter.filter_transceivers_list(filtered_transceivers)
        
        # ... rest of existing code ...
```

## Configuration Examples

### Single Frequency (122.8 MHz)
```yaml
EXCLUDED_FREQUENCIES: "122800000"
```

### Multiple Frequencies
```yaml
EXCLUDED_FREQUENCIES: "122800000,121700000,118000000"
```

### No Frequencies Excluded
```yaml
EXCLUDED_FREQUENCIES: ""
```

## File Changes Required

### New Files
- `app/filters/frequency_pattern_filter.py` - New frequency filter class

### Modified Files
- `app/services/data_service.py` - Add frequency filter initialization and usage
- `docker-compose.yml` - Add EXCLUDED_FREQUENCIES environment variable

## Benefits of This Approach

1. **Clean separation** - dedicated frequency filtering logic
2. **Easy configuration** - environment variable driven
3. **Performance optimized** - simple integer comparison
4. **Statistics tracking** - monitor filtering effectiveness
5. **Flexible** - easy to add/remove frequencies
6. **Consistent** - follows existing filter patterns
7. **Unified handling** - same logic for flights and ATC

## Testing Strategy

1. **Unit tests** for frequency pattern matching
2. **Integration tests** with real transceiver data
3. **Performance tests** to ensure no degradation
4. **Configuration tests** for different frequency patterns

## Future Enhancements

### Frequency Ranges
```yaml
EXCLUDED_FREQUENCY_RANGES: "122.7-122.9,118.0-118.1"
```

### Pattern Matching
```yaml
EXCLUDED_FREQUENCY_PATTERNS: "122.*,118.*"
```

### Entity Type Specific Filtering
```yaml
EXCLUDED_FREQUENCIES_FLIGHTS: "122800000"
EXCLUDED_FREQUENCIES_ATC: "121700000"
```

## Conclusion

The frequency filter implementation provides a clean, maintainable solution for excluding specific frequencies from transceiver data. By using Option 2 (dedicated frequency filter), the system maintains clear separation of concerns while providing the flexibility to exclude any combination of frequencies through simple environment variable configuration.

The filter will automatically exclude any transceiver with frequency `122800000` Hz (122.8 MHz), whether it's a flight or ATC transceiver, since they use the same frequency format.
