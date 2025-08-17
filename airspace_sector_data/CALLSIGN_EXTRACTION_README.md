# Controller Callsigns Extraction for VATSIM API Filtering

## Purpose

This script (`extract_controller_callsigns_from_positions.py`) extracts controller callsigns from the VATSIM `Positions.xml` file to create a simple text file that can be loaded into memory and used to filter callsigns from the VATSIM API.

## Background

The VATSIM API provides real-time data about air traffic controllers, but it doesn't include information about which callsigns are valid for specific positions or airspace. The `Positions.xml` file contains the complete configuration of all VATSIM positions, including the explicit callsigns that controllers can use.

## What the Script Does

1. **Parses** the `Positions.xml` file
2. **Extracts** all explicit controller callsigns from `ControllerInfo` elements
3. **Creates** a simple text file (`controller_callsigns_list.txt`) with one callsign per line
4. **Outputs** 88 unique callsigns in alphabetical order

## Output File

- **Filename**: `controller_callsigns_list.txt`
- **Format**: Plain text, one callsign per line
- **Content**: 88 unique controller callsigns
- **Example**:
  ```
  AD-W_APP
  AD_DEL
  AD_FMP
  AD_GND
  AF_GND
  AMB_DEL
  AMB_GND
  AV_APP
  AY_GND
  BK_GND
  BN-C_APP
  ...
  ```

## Usage for API Filtering

### 1. Load the Callsigns into Memory

```python
def load_valid_callsigns(file_path):
    """Load valid callsigns from the extracted list."""
    with open(file_path, 'r') as f:
        return set(line.strip() for line in f if line.strip())

# Load the callsigns
valid_callsigns = load_valid_callsigns('controller_callsigns_list.txt')
```

### 2. Filter VATSIM API Data

```python
def filter_vatsim_controllers(api_data, valid_callsigns):
    """Filter VATSIM API data to only include valid controller callsigns."""
    filtered_controllers = []
    
    for controller in api_data.get('controllers', []):
        callsign = controller.get('callsign', '')
        if callsign in valid_callsigns:
            filtered_controllers.append(controller)
    
    return filtered_controllers

# Example usage
api_response = get_vatsim_data()  # Your API call
filtered_data = filter_vatsim_controllers(api_response, valid_callsigns)
```

### 3. Validate Individual Callsigns

```python
def is_valid_controller_callsign(callsign, valid_callsigns):
    """Check if a callsign is valid for VATSIM controllers."""
    return callsign in valid_callsigns

# Example usage
if is_valid_controller_callsign('SY_TWR', valid_callsigns):
    print("Valid Sydney Tower callsign")
else:
    print("Invalid callsign")
```

## Callsign Categories

The extracted callsigns fall into several categories:

- **Tower positions**: `SY_TWR`, `ML_GND`, `BN_GND`
- **Approach control**: `SY-N_APP`, `ML_DEP`, `BN-S_APP`
- **Ground control**: `SY_GND`, `ML_GND`, `BN_GND`
- **Flow management**: `SY_FMP`, `ML_FMP`, `BN_FMP`
- **Delivery**: `SY_DEL`, `ML_DEL`, `BN_DEL`

## File Structure

```
airspace_sector_data/
├── Positions.xml                                    # Source VATSIM configuration
├── extract_controller_callsigns_from_positions.py   # Extraction script
├── controller_callsigns_list.txt                    # Output: callsigns list
└── CALLSIGN_EXTRACTION_README.md                   # This documentation
```

## Running the Script

```bash
cd airspace_sector_data
python extract_controller_callsigns_from_positions.py
```

## Benefits

1. **Performance**: Loading callsigns into memory is faster than parsing XML each time
2. **Reliability**: Ensures only valid VATSIM controller callsigns are processed
3. **Maintenance**: Easy to update when VATSIM adds new positions
4. **Integration**: Simple text format works with any programming language
5. **Validation**: Can be used to validate user input or API responses

## Maintenance

- **Update frequency**: Run whenever VATSIM updates their `Positions.xml`
- **Version control**: Track changes to the callsign list
- **Validation**: Periodically verify the extracted callsigns against the source XML

## Example Integration

```python
import requests

class VATSIMControllerFilter:
    def __init__(self, callsign_file):
        self.valid_callsigns = self.load_callsigns(callsign_file)
    
    def load_callsigns(self, file_path):
        with open(file_path, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    
    def get_active_controllers(self):
        """Get VATSIM data and filter to valid controller callsigns."""
        response = requests.get('https://data.vatsim.net/v3/vatsim-data.json')
        data = response.json()
        
        # Filter to only valid controller callsigns
        controllers = []
        for controller in data.get('controllers', []):
            if controller.get('callsign') in self.valid_callsigns:
                controllers.append(controller)
        
        return controllers

# Usage
filter = VATSIMControllerFilter('controller_callsigns_list.txt')
active_controllers = filter.get_active_controllers()
print(f"Found {len(active_controllers)} active controllers with valid callsigns")
```

This approach provides a clean, efficient way to filter VATSIM API data based on the official position configuration.
