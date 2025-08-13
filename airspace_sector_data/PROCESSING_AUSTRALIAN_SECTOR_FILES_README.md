# Processing Australian Sector Files - Responsible Sectors Approach

## Overview
This document explains how the `process_australian_sectors.py` script processes VATSYS XML sector files using the new **ResponsibleSectors approach**. The script identifies sectors with responsibility relationships and combines their geographic boundaries to create unified sector coverage areas.

## New Approach: Responsible Sectors

### What Changed
The script now uses a **ResponsibleSectors-based approach** instead of the old standalone sector method:

- **OLD**: Processed standalone sectors that didn't appear in other sectors' ResponsibleSectors
- **NEW**: Processes sectors that HAVE a `<ResponsibleSectors>` section and combines them with their responsible sectors

### Why This Approach
This method creates **unified sector coverage areas** by combining:
1. **Main sector** (e.g., MUN - Mungo)
2. **All responsible sectors** (e.g., YWE, OXL, GTH)
3. **Result**: Single polygon representing the complete coverage area

## Input Files

### 1. `Sectors.xml` - Sector Metadata and Relationships
**Location**: `Sectors.xml` (same directory as script)
**Purpose**: Contains sector definitions, properties, and responsibility relationships

**Key Elements**:
- `<Sector>`: Individual sector definitions
- `Name`: Short sector identifier (e.g., "MUN", "ARL")
- `FullName`: Human-readable name (e.g., "Mungo", "Armidale")
- `Callsign`: ATC callsign (e.g., "ML-MUN_CTR", "BN-ARL_CTR")
- `Frequency`: Radio frequency (e.g., "132.600", "130.900")
- `Volumes`: Reference to volume definitions in Volumes.xml
- `ResponsibleSectors`: Comma-separated list of sectors this sector is responsible for

**Example Sector Entry**:
```xml
<Sector Name="MUN" FullName="Mungo" Callsign="ML-MUN_CTR" Frequency="132.600">
    <Volumes>MUN</Volumes>
    <ResponsibleSectors>YWE,OXL,GTH</ResponsibleSectors>
</Sector>
```

### 2. `Volumes.xml` - Geographic Boundaries
**Location**: `Volumes.xml` (same directory as script)
**Purpose**: Contains actual geographic coordinate data for sector boundaries

**Key Elements**:
- `<Volume>`: Volume definitions referenced by sectors
- `Name`: Volume identifier (matches Volumes attribute in Sectors.xml)
- `<Boundaries>`: Reference to boundary definition
- `<Boundary>`: Actual coordinate data
- Coordinate format: DDMMSS.SSSS (Degrees, Minutes, Seconds with decimal seconds)

**Example Volume Entry**:
```xml
<Volume Name="MUN">
    <Boundaries>MUN</Boundaries>
</Volume>
<Boundary Name="MUN">
    -342011.000+1382231.000/
    -340756.000+1381815.000/
    -340123.000+1382345.000/
    <!-- ... more coordinates ... -->
</Boundary>
```

## Sector Filtering Criteria

The script now processes sectors based on these criteria:

1. **Must have `<ResponsibleSectors>` section** - This is the key requirement
2. **Callsign Pattern**: Must start with "ML-" or "BN-" (Australian domestic)
3. **Callsign Type**: Must end with "_CTR" or "_FSS" (Control or Flight Service)

**Examples of sectors that WILL be processed**:
- ✅ `ML-MUN_CTR` with ResponsibleSectors: YWE, OXL, GTH
- ✅ `BN-ARL_CTR` with ResponsibleSectors: MDE, MLD, OCN, MNN, CNK
- ✅ `ML-IND_FSS` with ResponsibleSectors: INE, INS

**Examples of sectors that will be SKIPPED**:
- ❌ No ResponsibleSectors section
- ❌ Callsign doesn't start with ML- or BN-
- ❌ Callsign doesn't end with _CTR or _FSS

## Processing Flow

### Step 1: Sector Identification
1. Parse `Sectors.xml` to find all sectors
2. Filter sectors based on criteria above
3. Extract primary volume and responsible sector lists

### Step 2: Volume Processing
For each qualifying sector:
1. **Primary Volume**: Extract first volume from comma-separated list
   - Example: `"HUO,HUO_TMA_CAP"` → only use `"HUO"`
2. **Responsible Sectors**: Parse comma-separated list
   - Example: `"YWE,OXL,GTH"` → process YWE, OXL, and GTH

### Step 3: Coordinate Extraction
1. Look up each sector name in `Volumes.xml`
2. Parse coordinate strings in DDMMSS.SSSS format
3. Convert to decimal degrees using the `parse_coordinate()` function
4. Create Shapely Polygon objects for each sector

### Step 4: Polygon Combination
1. **Main Sector**: Get polygon from primary volume
2. **Responsible Sectors**: Get polygons from all responsible sectors
3. **Combine**: Use Shapely's `unary_union()` to merge all polygons
4. **Extract Perimeter**: Get only the outer boundary coordinates
5. **Result**: Single unified polygon representing complete coverage area

## Coordinate Processing

### Input Format
**VATSYS Format**: `-342011.000+1382231.000`
- **Latitude**: `-342011.000` (negative = South)
- **Longitude**: `+1382231.000` (positive = East)

### Conversion Process
The `parse_coordinate()` function converts DDMMSS.SSSS to decimal degrees:

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

## Output Data Structure

The script produces a list of sector objects with the following structure:

```python
{
    'name': 'MUN',                           # Short identifier
    'full_name': 'Mungo',                    # Human-readable name
    'callsign': 'ML-MUN_CTR',               # ATC callsign
    'primary_volume': 'MUN',                 # Primary volume name
    'responsible_sectors': [                 # List of responsible sectors
        'YWE', 'OXL', 'GTH'
    ],
    'boundaries': [                          # Combined geographic coordinates
        (-34.336389, 138.372528),           # (lat, lon) pairs
        (-34.126000, 138.302500),
        # ... more coordinates ...
    ],
    'boundary_count': 54                    # Total coordinate points
}
```

## Data Flow Diagram

```
Sectors.xml → Filter by Criteria → Extract Relationships → Volumes.xml
     ↓              ↓                    ↓              ↓
Metadata      Has ResponsibleSectors  Volume Names    Boundary Text
     ↓              ↓                    ↓              ↓
Properties    ML-/BN- + _CTR/_FSS    Primary + Resp   Coordinate Data
     ↓              ↓                    ↓              ↓
Responsible   Qualifying Sectors      Polygon Creation  Decimal Degrees
Sectors       Only                    Shapely Objects   Geographic Data
     ↓              ↓                    ↓              ↓
Combine       Unified Coverage        Outer Perimeter   Final Boundaries
Polygons      Areas                   Only              Ready for Use
```

## Results Summary

### Successfully Processed Sectors (20 total)
The script successfully processed **20 sectors** that meet the new criteria:

1. **ASP** (Alice Springs): 64 points - ASP + FOR, WAR, ASW, WRA, BKE, ESP
2. **ARL** (Armidale): 63 points - ARL + MDE, MLD, OCN, MNN, CNK
3. **BLA** (Benalla): 44 points - BLA + ELW, MAE, MAV
4. **ELW** (Eildon Weir): 26 points - ELW + MAE
5. **GUN** (Gundagai): 35 points - GUN + KAT, BIK, SAS
6. **HUO** (Huon): 79 points - HUO + WON, HBA, LTA
7. **HYD** (Hyden): 25 points - HYD + JAR, PIY, CRS, GVE, GEL, LEA, PHA
8. **INL** (Inverell): 43 points - INL + DOS, SDY, BUR, GOL, NSA
9. **ISA** (Isa): 107 points - ISA + WEG, ARA, STR
10. **KEN** (Kennedy): 37 points - KEN + KPL, MNN, NSA
11. **KPL** (Keppel): 43 points - KPL + MNN, NSA
12. **MNN** (Manning): 14 points - MNN + NSA
13. **MUN** (Mungo): 54 points - MUN + YWE, OXL, GTH
14. **NSA** (Noosa): 22 points - NSA only
15. **OLW** (Onslow): 29 points - OLW + POT, PAR, MEK, MTK, NEW, MZI
16. **TBD** (Tailem Bend): 34 points - TBD + AUG, AAW
17. **TRT** (Territory North): 37 points - TRT + KIY, DAE, ASH, TRS
18. **WOL** (Wollongong): 64 points - WOL + SNO, CAE, CAW
19. **IND** (Brisbane Radio Indian): 38 points - IND + INE, INS
20. **TSN** (Brisbane Radio Tasman): 75 points - TSN + HWE, FLD, COL

### Skipped Sectors (270 total)
**270 sectors were skipped** because they don't meet the new criteria:
- No ResponsibleSectors section
- Wrong callsign pattern
- Wrong callsign type

## Usage

### Running the Script
```bash
cd airspace_sector_data
python process_australian_sectors.py
```

### What It Produces
1. **Console Output**: Detailed processing information for each sector
2. **Processed Sectors**: 20 sectors with combined boundaries
3. **Output Files**:
   - `processed_sectors/australian_sectors_responsible.json` - Main results
   - `processed_sectors/skipped_sectors.json` - Analysis of skipped sectors

### Output Example
```
Processing sector: MUN (Mungo)
  Callsign: ML-MUN_CTR
  📍 Primary volume: MUN
  🔗 Responsible sectors: YWE, OXL, GTH
  ✅ Main sector MUN: 11 points
  ✅ Responsible sector YWE: 14 points
  ✅ Responsible sector OXL: 12 points
  ✅ Responsible sector GTH: 17 points
  🎯 Combined polygon: 54 outer perimeter points
  ✅ Successfully processed with 54 boundary points
```

## Technical Implementation Details

### Key Functions
- **`should_process_sector()`**: Determines if sector meets criteria
- **`get_primary_volume()`**: Extracts first volume from comma-separated list
- **`get_responsible_sectors()`**: Parses responsible sectors list
- **`get_volume_boundaries()`**: Creates Shapely polygon from volume coordinates
- **`combine_sector_polygons()`**: Merges polygons and extracts outer perimeter

### Dependencies
- **Python Libraries**: `xml.etree.ElementTree`, `shapely.geometry`, `shapely.ops`
- **File Requirements**: `Sectors.xml` and `Volumes.xml` in same directory
- **Coordinate Processing**: Custom `parse_coordinate()` function for VATSYS format

### Performance
- **Processing**: Linear time complexity O(n) for sector processing
- **Memory**: Loads XML files and creates Shapely objects
- **Polygon Operations**: Efficient geometric union and perimeter extraction

## Benefits of New Approach

### 1. **Unified Coverage Areas**
- Each sector represents its complete responsibility area
- No gaps or overlaps between related sectors
- Clear boundaries for air traffic management

### 2. **Responsibility Relationships**
- Reflects actual ATC sector organization
- Shows which sectors work together
- Better understanding of airspace structure

### 3. **Geometric Accuracy**
- Uses Shapely for robust polygon operations
- Handles complex boundary combinations
- Produces clean, non-overlapping perimeters

### 4. **Data Quality**
- Only processes sectors with complete information
- Combines related sectors automatically
- Maintains coordinate precision from source data

## Conclusion

The new ResponsibleSectors approach provides a more accurate and useful representation of Australian airspace sectors. By combining main sectors with their responsible sectors, the script creates unified coverage areas that better reflect actual ATC operations and airspace management.

The key insight is that sectors don't operate in isolation - they work together as part of larger airspace management systems. This approach captures those relationships and produces geographic boundaries that represent the true scope of each sector's responsibility.
