# Processing Australian Sector Files - Technical Documentation

## Overview
This document explains how the `extract_australian_sector_boundaries.py` script processes VATSYS XML sector files to extract geographic coordinates for Australian airspace sectors. The process involves parsing two key XML files and converting coordinate formats to produce usable geographic boundaries.

## Input Files

### 1. `Sectors.xml` - Sector Metadata
**Location**: `external-data/Sectors.xml`
**Source**: VATSYS software installation directory
**Purpose**: Contains sector definitions, properties, and relationships

**Note**: These files are obtained from the VATSYS software installation. After installing VATSYS, the sector definition files are typically located in the VATSYS installation directory and should be copied to the `external-data/` folder for processing.

**Key Elements**:
- `<Sector>`: Individual sector definitions
- `Name`: Short sector identifier (e.g., "ASP", "ARL")
- `FullName`: Human-readable name (e.g., "Alice Springs", "Armidale")
- `Callsign`: ATC callsign (e.g., "ML-ASP_CTR", "BN-ARL_CTR")
- `Frequency`: Radio frequency (e.g., "128.850", "130.900")
- `Volumes`: Reference to volume definitions in Volumes.xml
- `ResponsibleSectors`: Comma-separated list of sectors this sector is responsible for

**Example Sector Entry**:
```xml
<Sector Name="ASP" FullName="Alice Springs" Callsign="ML-ASP_CTR" Frequency="128.850" Volumes="ASP">
    <ResponsibleSectors>FOR,WAR,ASW,WRA,BKE,ESP</ResponsibleSectors>
</Sector>
```

### 2. `Volumes.xml` - Geographic Boundaries
**Location**: `external-data/Volumes.xml`
**Source**: VATSYS software installation directory
**Purpose**: Contains actual geographic coordinate data for sector boundaries

**Note**: Like Sectors.xml, this file is also obtained from the VATSYS software installation. It contains the 3D airspace volume definitions and coordinate data that define the actual geographic boundaries of each sector.

**Key Elements**:
- `<Volume>`: Volume definitions referenced by sectors
- `Name`: Volume identifier (matches Volumes attribute in Sectors.xml)
- `<Boundaries>`: Reference to boundary definition
- `<Boundary>`: Actual coordinate data
- Coordinate format: DDMMSS.SSSS (Degrees, Minutes, Seconds with decimal seconds)

**Example Volume Entry**:
```xml
<Volume Name="ASP">
    <Boundaries>ASP_BOUNDARY</Boundaries>
</Volume>
<Boundary Name="ASP_BOUNDARY">
    -342011.000+1382231.000/
    -340756.000+1381815.000/
    -340123.000+1382345.000/
    <!-- ... more coordinates ... -->
</Boundary>
```

## Coordinate Processing Flow

### Step 1: Sector Filtering
The script filters sectors based on specific criteria:

1. **Callsign Type**: Must contain "FSS" or "CTR"
2. **Geographic Scope**: Must be Australian domestic (callsigns starting with "ML-" or "BN-")
3. **Standalone Check**: Sector must not appear in the `ResponsibleSectors` of other sectors

### Step 2: Volume Resolution
For each matching sector:
1. Extract volume names from the `Volumes` attribute
2. Look up each volume in `Volumes.xml`
3. Find the corresponding boundary definition

### Step 3: Coordinate Parsing
The `parse_coordinate()` function converts VATSYS coordinate format to decimal degrees:

**Input Format**: `-342011.000+1382231.000`
- **Latitude**: `-342011.000` (negative, indicating South)
- **Longitude**: `+1382231.000` (positive, indicating East)

**Parsing Logic**:
1. **Remove signs**: Strip `-` and `+` for processing
2. **Format Detection**: 
   - 7 digits before decimal = DDDMMSS format
   - 6 digits before decimal = DDMMSS format
3. **Extract Components**:
   - Degrees: First 2-3 digits
   - Minutes: Next 2 digits
   - Seconds: Next 2 digits + decimal portion
4. **Convert to Decimal**: `degrees + (minutes/60) + (seconds/3600)`
5. **Apply Sign**: Restore negative for South latitude

**Example Conversion**:
```
Input: -342011.000
Format: DDMMSS.SSSS
- Degrees: 34
- Minutes: 20
- Seconds: 11.000
- Decimal: 34 + (20/60) + (11/3600) = 34.336389°
- Result: -34.336389° (South)
```

### Step 4: Boundary Assembly
For each sector:
1. Parse all coordinate pairs from the boundary text
2. Convert each coordinate to decimal degrees
3. Create a list of (latitude, longitude) tuples
4. Store complete boundary data with sector metadata

## Output Data Structure

The script produces a list of sector objects with the following structure:

```python
{
    'name': 'ASP',                           # Short identifier
    'callsign': 'ML-ASP_CTR',               # ATC callsign
    'frequency': '128.850',                  # Radio frequency
    'full_name': 'Alice Springs',            # Human-readable name
    'volumes': 'ASP',                        # Volume references
    'responsible_sectors': 'FOR,WAR,ASW,WRA,BKE,ESP',  # Dependencies
    'boundaries': [                          # Geographic coordinates
        (-34.336389, 138.372528),           # (lat, lon) pairs
        (-34.126000, 138.302500),
        # ... more coordinates ...
    ]
}
```

## Data Flow Diagram

```
Sectors.xml → Sector Filtering → Volume Resolution → Volumes.xml
     ↓              ↓                ↓              ↓
Metadata      FSS/CTR Only    Volume Names    Boundary Text
     ↓              ↓                ↓              ↓
Properties    Australian      Coordinate      Decimal Degrees
     ↓              ↓                ↓              ↓
Responsible   Standalone      Geographic      Sector Boundaries
Sectors       Sectors         Boundaries      Ready for Use
```

## Usage for One-Off Manual Processing

### Running the Script
```bash
cd scripts
python extract_australian_sector_boundaries.py
```

### What It Produces
1. **Console Output**: Detailed sector information with sample coordinates
2. **Filtered Results**: Only Australian domestic FSS/CTR standalone sectors
3. **Coordinate Data**: Geographic boundaries in decimal degrees format

### Output Example
```
Found 15 Australian domestic FSS/CTR standalone sectors:
--------------------------------------------------------------------------------
 1. ASP
     Callsign: ML-ASP_CTR
     Frequency: 128.850
     Full Name: Alice Springs
     Volumes: ASP
     Responsible for: FOR,WAR,ASW,WRA,BKE,ESP
     Boundary Points: 12 coordinates
     Sample Coordinates:
       Point 1: -34.336389, 138.372528
       Point 2: -34.126000, 138.302500
       Point 3: -34.020500, 138.390833
       ... and 9 more points
```

## Technical Implementation Details

### Coordinate Format Handling
- **VATSYS Format**: DDMMSS.SSSS (Degrees, Minutes, Seconds)
- **Output Format**: Decimal degrees (standard for GIS applications)
- **Precision**: Maintains sub-second accuracy from source data
- **Sign Handling**: Properly handles negative latitudes (South) and positive longitudes (East)

### Error Handling
- **File Parsing**: Graceful handling of XML parsing errors
- **Coordinate Validation**: Skips invalid coordinate strings
- **Missing Data**: Continues processing even if some sectors lack complete data
- **Format Detection**: Automatically detects coordinate format based on digit count

### Performance Considerations
- **Memory Usage**: Loads entire XML files into memory
- **Processing Speed**: Linear time complexity O(n) for sector processing
- **Coordinate Conversion**: Efficient parsing with minimal string operations
- **Filtering**: Early exit for non-matching sectors

## Dependencies and Requirements

### Python Libraries
- `xml.etree.ElementTree`: XML parsing (standard library)
- `re`: Regular expressions (standard library, though not currently used)

### File Requirements
- `Sectors.xml`: Must be accessible at `../external-data/Sectors.xml`
- `Volumes.xml`: Must be accessible at `../external-data/Volumes.xml`
- Both files must be valid XML with expected structure

**File Acquisition**:
- **VATSYS Installation**: Install VATSYS software on your system
- **File Location**: Locate sector definition files in VATSYS installation directory
- **Copy Files**: Copy `Sectors.xml` and `Volumes.xml` to the `external-data/` folder
- **Verify Structure**: Ensure files maintain their original XML structure and encoding

### Data Quality Assumptions
- Coordinate strings follow VATSYS format consistently
- Volume names in Sectors.xml match Volume names in Volumes.xml
- Boundary names in Volumes.xml are properly referenced
- All required attributes are present in sector definitions

## Future Enhancements

### Potential Improvements
1. **Coordinate Validation**: Add bounds checking for Australian airspace
2. **Output Formats**: Support for GeoJSON, KML, or other GIS formats
3. **Caching**: Save processed results to avoid re-parsing
4. **Error Reporting**: More detailed error messages for debugging
5. **Batch Processing**: Process multiple sector files or regions

### Integration Opportunities
1. **Database Storage**: Save processed sectors to PostgreSQL
2. **API Endpoints**: Expose sector data through REST API
3. **Real-time Updates**: Monitor for changes in source XML files
4. **Visualization**: Generate maps showing sector boundaries

## Troubleshooting

### Common Issues
1. **File Not Found**: Check relative paths from script location
2. **XML Parsing Errors**: Verify XML file integrity and encoding
3. **Coordinate Conversion Failures**: Check for unexpected coordinate formats
4. **No Matching Sectors**: Verify filtering criteria and source data

### Debugging Tips
1. **Enable Verbose Output**: Add print statements for coordinate parsing
2. **Check File Contents**: Verify XML structure matches expected format
3. **Validate Coordinates**: Manually verify a few coordinate conversions
4. **Test Individual Functions**: Run coordinate parsing on sample data

## Conclusion

The sector processing script provides a robust foundation for extracting Australian airspace sector data from VATSYS XML files. By understanding the data flow and coordinate processing, you can effectively use this for one-off manual processing or integrate it into larger systems for real-time sector tracking and analysis.

The key insight is that the script bridges the gap between human-readable sector definitions (Sectors.xml) and machine-readable geographic coordinates (Volumes.xml), producing a unified dataset ready for airspace management applications.
