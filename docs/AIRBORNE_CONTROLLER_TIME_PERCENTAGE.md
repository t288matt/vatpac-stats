# Airborne Controller Time Percentage

## Overview

The `airborne_controller_time_percentage` field provides a more accurate measure of ATC contact by calculating the percentage of time a flight was in contact with ATC **while airborne in sectors**, rather than during the entire flight including ground operations.

## Key Differences from Existing Field

| Field | Description | Calculation Method |
|-------|-------------|-------------------|
| `controller_time_percentage` | Percentage of flight records with ATC contact (anywhere) | Based on all flight data records |
| `airborne_controller_time_percentage` | Percentage of airborne time with ATC contact (sectors only) | Based on sector occupancy + ATC contact validation |

## Implementation Details

### Data Sources
1. **`transceivers` table** - Frequency matches between flights and ATC
2. **`flight_sector_occupancy` table** - Validates aircraft is airborne in sectors
3. **`controllers` table** - ATC session data and facility information

### Calculation Logic

#### Numerator: Airborne ATC Contact Time
- **Frequency Matching**: Flight and ATC on same frequency
- **Proximity Filter**: Within 300nm geographic distance
- **Timing Filter**: Within 180 seconds (3 minutes) of each other
- **Contact Counting**: Each matching record counts as 1 minute
- **Airborne Validation**: Aircraft must be in a sector from `flight_sector_occupancy`

#### Denominator: Total Airborne Time
- Sum of `duration_seconds` from `flight_sector_occupancy` table
- Only includes sectors with positive duration
- Converted to minutes for percentage calculation

#### Final Calculation
```
airborne_controller_time_percentage = (airborne_atc_time / total_airborne_time) * 100
```

### Function Signature

```python
async def calculate_airborne_controller_time_percentage(
    self, 
    flight_callsign: str, 
    departure: str, 
    arrival: str, 
    logon_time: datetime
) -> Dict[str, Any]
```

### Return Data

```python
{
    "airborne_controller_time_percentage": float,      # 0-100 percentage
    "total_airborne_atc_time_minutes": int,           # Total ATC contact time
    "total_airborne_time_minutes": int,               # Total airborne time
    "airborne_atc_contacts_detected": int             # Count of contacts
}
```

## Database Schema

### New Field Added
```sql
-- flight_summaries table
airborne_controller_time_percentage DECIMAL(5,2)  -- Percentage of airborne time with ATC contact

-- flights_archive table  
airborne_controller_time_percentage DECIMAL(5,2)  -- Percentage of airborne time with ATC contact
```

### Constraints
```sql
CHECK (airborne_controller_time_percentage >= 0 AND airborne_controller_time_percentage <= 100)
```

## Usage

### During Flight Summary Creation
The field is automatically calculated and populated when flight summaries are created in the `data_service.py`:

```python
# Calculate airborne ATC time percentage
airborne_atc_data = await self.atc_detection_service.calculate_airborne_controller_time_percentage(
    callsign, departure, arrival, first_record.logon_time
)

# Include in summary data
summary_data["airborne_controller_time_percentage"] = airborne_atc_data["airborne_controller_time_percentage"]
```

### Manual Calculation
```python
from app.services.atc_detection_service import ATCDetectionService

atc_service = ATCDetectionService()
result = await atc_service.calculate_airborne_controller_time_percentage(
    "QFA123", "YSSY", "YMML", logon_time
)

percentage = result["airborne_controller_time_percentage"]
```

## Migration

### For New Deployments
The field is automatically included in new database initializations via `config/init.sql`.

### For Existing Deployments
Run the migration script to add the field to existing tables:

```bash
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data \
  -f scripts/add_airborne_controller_time_percentage.sql
```

## Testing

### Test Script
Use the provided test script to verify functionality:

```bash
python scripts/test_airborne_controller_time.py
```

### Test Coverage
- Database schema validation
- Function calculation accuracy
- Comparison with existing `controller_time_percentage`
- Error handling and edge cases

## Benefits

1. **More Accurate ATC Coverage**: Only counts ATC time while actually airborne
2. **Excludes Ground Operations**: Eliminates departure/arrival phase ATC contact
3. **Sector Validation**: Ensures aircraft is in controlled airspace
4. **Better Analytics**: Provides cleaner data for sector-based analysis
5. **Performance Insights**: Helps identify true airborne ATC coverage patterns

## Limitations

1. **Sector Dependency**: Requires complete sector occupancy data
2. **Contact Granularity**: Uses 1-minute per contact approximation (same as existing field)
3. **Data Availability**: Depends on transceiver and sector data quality

## Future Enhancements

1. **Real-time Duration**: Calculate actual contact duration instead of 1-minute per contact
2. **Sector Type Filtering**: Differentiate between terminal and enroute sectors
3. **Weather Conditions**: Factor in weather-related ATC contact requirements
4. **Performance Metrics**: Track calculation performance and optimization opportunities



