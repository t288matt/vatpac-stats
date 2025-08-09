# Polygon Testing with Live VATSIM Data - Instructions

## 🧪 Testing Script Created

**File**: `test_polygon_with_live_vatsim_data.py`  
**Purpose**: Test polygon coordinates with live VATSIM aircraft data  
**Status**: Ready for testing

## 🚀 How to Run the Test

### Option 1: Using Docker (Recommended)

1. **Start Docker Desktop** (if not running)
2. **Run the test**:
   ```bash
   # Start Docker services first
   docker-compose up -d
   
   # Run the test script
   docker-compose exec app python test_polygon_with_live_vatsim_data.py sample_polygon_coordinates.json
   ```

### Option 2: Local Python Installation

1. **Install requirements**:
   ```bash
   pip install shapely requests
   ```

2. **Run the test**:
   ```bash
   python test_polygon_with_live_vatsim_data.py sample_polygon_coordinates.json
   ```

### Option 3: Create Custom Polygon

1. **Create your own polygon JSON file**:
   ```json
   {
     "name": "My Test Boundary",
     "description": "Custom polygon for testing",
     "coordinates": [
       [-33.0, 151.0],
       [-33.0, 152.0],
       [-34.0, 152.0],
       [-34.0, 151.0],
       [-33.0, 151.0]
     ]
   }
   ```

2. **Run with your polygon**:
   ```bash
   python test_polygon_with_live_vatsim_data.py your_polygon.json
   ```

## 📊 What the Test Does

1. **Fetches Live Data**: Gets current aircraft positions from VATSIM API
2. **Loads Polygon**: Reads polygon coordinates from JSON file
3. **Tests Each Aircraft**: Checks if aircraft position is inside/outside polygon
4. **Shows Results**: Displays real-time yes/no results for each aircraft
5. **Provides Summary**: Shows counts and percentages

## 📋 Expected Output

```
🧪 TEMPORARY POLYGON TESTING SCRIPT
==================================================
Testing live VATSIM aircraft positions against polygon boundary

✅ Loaded polygon with 5 points
🌐 Fetching live VATSIM data...
✅ Fetched 1247 aircraft from VATSIM API

🧪 Testing 1247 aircraft against polygon boundary...
======================================================================
✅ INSIDE:  QFA123   at (-33.9399, 151.1753) - YSSY → YMML
❌ OUTSIDE: UAL456   at ( 40.7128, -74.0060) - KJFK → EGLL
✅ INSIDE:  JST789   at (-37.6690, 144.8410) - YMML → YSSY
...

======================================================================
📊 POLYGON TEST SUMMARY
======================================================================
Total Aircraft Tested: 1247
✅ Inside Polygon:      23 (1.8%)
❌ Outside Polygon:   1198 (96.1%)
⚠️  No Position Data:   26 (2.1%)

🎯 Aircraft INSIDE polygon:
   QFA123 - YSSY → YMML (Alt: 35000)
   JST789 - YMML → YSSY (Alt: 12000)
   ...

💾 Detailed results saved to: polygon_test_results.json
🎯 Polygon testing complete!
```

## 🔧 Script Features

- **Live VATSIM Data**: Fetches real aircraft positions
- **Shapely Integration**: Uses the same library as the main implementation
- **Clear Output**: Shows each aircraft as INSIDE ✅ or OUTSIDE ❌
- **Detailed Info**: Shows callsign, position, route, altitude
- **Summary Stats**: Counts and percentages
- **Error Handling**: Handles missing position data gracefully
- **JSON Output**: Saves detailed results to file

## 📁 Files Created

1. **`test_polygon_with_live_vatsim_data.py`** - Main testing script
2. **`sample_polygon_coordinates.json`** - Sample Australia boundary
3. **`polygon_test_results.json`** - Generated results (after running)

## 🎯 What This Validates

- ✅ Polygon coordinate format is correct
- ✅ Shapely integration works
- ✅ Geographic calculations are accurate
- ✅ Real-world aircraft positions are handled correctly
- ✅ Performance with live data volumes

## 🚨 Troubleshooting

### Docker Issues
- Ensure Docker Desktop is running
- Try: `docker-compose down` then `docker-compose up -d`

### Network Issues
- Script needs internet access to fetch VATSIM data
- VATSIM API: https://data.vatsim.net/v3/vatsim-data.json

### Polygon Issues
- Ensure JSON format is correct
- Polygon must have at least 3 points
- Coordinates should be [lat, lon] format

## 🎯 Next Steps

After successful testing:
1. Use validated polygon coordinates in the main implementation
2. Continue with Sprint 1, Task 1.2 - Geographic Utilities Module
3. Implement the polygon functions in `app/utils/geographic_utils.py`

---

**Note**: This is a temporary testing script. Delete after validation is complete.
