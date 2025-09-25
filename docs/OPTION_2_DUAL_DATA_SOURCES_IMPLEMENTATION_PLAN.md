# Option 2: Dual Data Sources Implementation Plan

**Date**: January 2025  
**Issue**: GitHub Issue #82 - Fix the Airborne Time Percentage Calculation  
**Approach**: Use flight data for airborne time calculation, transceiver data for controller contacts

---

## Status

- **Current state**: Implementation work in progress. Core Option 2 logic has been implemented in `app/services/atc_detection_service.py` (helpers for `_get_airborne_time_from_flights`, `_count_airborne_controller_contacts`, and updated metrics calculation). Controller type canonicalization to short codes (`TMA`, `CTR`, `FSS`, etc.) has been applied across services and tests. Some async DB lifecycle and integration tests are still failing and under active triage.
- **What passed**: Controller type detector unit tests and proximity-related integration tests passed after canonicalization. Targeted ATC proximity tests passed.
- **What remains**: Fix async engine/session lifecycle errors, stabilize integration tests, run full test suite, run staging validation and controlled recalculation/backfill.

## To-do (short)

- **Completed**: Reproduce and fix initial async loop errors; run full test suite to collect failures.  
- **In progress**: Triage top integration/data-mismatch failures caused by metric changes; implement fixes for async/session lifecycle.  
- **Pending**: Deploy to staging and run validation queries; run small smoke recalculation and performance/load tests; deploy to production with monitoring and rollback plan.


## 📋 **Option 2 Overview**

**Approach**: Use flight data for airborne time calculation, transceiver data for controller contacts.

**Key Changes**:
1. **Modify airborne time calculation** to use `flights` table instead of `transceivers` table
2. **Keep controller contact detection** using filtered transceiver data
3. **Add altitude tracking to flights table** (if not already present)

---

## 🔍 **Data Source Analysis**

### **Current Data Sources**

#### **Flights Table** (`flights`)
- **Purpose**: Live flight data with real-time position updates
- **Altitude Data**: `altitude` (INTEGER) - Current altitude from VATSIM API
- **Update Frequency**: `VATSIM_POLLING_INTERVAL` (60 seconds)
- **Data Coverage**: ALL flights, including those on 122.8 MHz
- **Filtering**: No frequency filtering applied

#### **Transceivers Table** (`transceivers`)
- **Purpose**: Radio frequency and communication data
- **Altitude Data**: `height_msl` (FLOAT) - Height above mean sea level in meters
- **Update Frequency**: `VATSIM_TRANSCEIVERS_POLLING_INTERVAL` (120 seconds)
- **Data Coverage**: Filtered transceivers (122.8 MHz excluded)
- **Filtering**: 122.8 MHz frequencies filtered out during ingestion

### **Key Differences**

| Aspect | Flights Table | Transceivers Table |
|--------|---------------|-------------------|
| **Altitude Field** | `altitude` (INTEGER, feet) | `height_msl` (FLOAT, meters) |
| **Data Coverage** | All flights | Filtered (no 122.8) |
| **Update Frequency** | `VATSIM_POLLING_INTERVAL` (60s) | `VATSIM_TRANSCEIVERS_POLLING_INTERVAL` (120s) |
| **Altitude Units** | Feet (VATSIM API) | Meters (VATSIM API) |
| **Data Integrity** | Complete flight data | Filtered communication data |

---

## ⚙️ **Polling Interval Configuration**

### **Environment Variables**
```yaml
# docker-compose.yml
VATSIM_POLLING_INTERVAL: 60    # Flights + controllers (60 seconds)
VATSIM_TRANSCEIVERS_POLLING_INTERVAL: 120  # Transceivers (120 seconds)
```

### **Polling Interval Usage in Option 2**

| Data Source | Polling Interval | Usage | Time Calculation |
|-------------|------------------|-------|------------------|
| **Flights Table** | `VATSIM_POLLING_INTERVAL` (60s) | Airborne time calculation (denominator) | `records * (60/60) = records minutes` |
| **Transceivers Table** | `VATSIM_TRANSCEIVERS_POLLING_INTERVAL` (120s) | Controller contact calculation (numerator) | `records * (120/60) = records * 2 minutes` |

### **Why Different Intervals Matter**
- **Flights**: More frequent updates (60s) provide better time resolution for airborne calculations
- **Transceivers**: Less frequent updates (120s) reduce API load while maintaining adequate controller contact detection
- **Accuracy**: Using the correct interval for each data source ensures accurate time calculations

---

## 🎯 **Implementation Strategy**

### **Core Concept**

**Before Fix**:
```
Numerator: Controller contacts (from filtered transceivers - excludes 122.8)
Denominator: Airborne time (from filtered transceivers - excludes 122.8)
```

**After Fix (Option 2)**:
```
Numerator: Controller contacts (from filtered transceivers - excludes 122.8)
Denominator: Airborne time (from flights table - includes 122.8)
```

### **Data Flow Changes**

1. **Controller Contact Detection**: Unchanged
   - Use filtered transceiver data
   - Exclude 122.8 MHz frequencies
   - Calculate controller time percentage

2. **Airborne Time Calculation**: Modified
   - Use flights table data
   - Include ALL flight time (including 122.8)
   - Calculate total airborne time

---

## 🔧 **Implementation Plan**

### **Phase 1: Data Source Analysis & Validation**

#### **1.1 Validate Flight Data Sufficiency**
```sql
-- Check flight data coverage and altitude data quality
SELECT 
    COUNT(*) as total_flights,
    COUNT(altitude) as flights_with_altitude,
    COUNT(CASE WHEN altitude > 1500 THEN 1 END) as flights_above_1500ft,
    AVG(altitude) as avg_altitude,
    MIN(altitude) as min_altitude,
    MAX(altitude) as max_altitude
FROM flights 
WHERE last_updated >= NOW() - INTERVAL '24 hours';
```

#### **1.2 Compare Data Sources**
```sql
-- Compare flight vs transceiver altitude data for same time period
WITH flight_altitudes AS (
    SELECT callsign, altitude, last_updated
    FROM flights 
    WHERE last_updated >= NOW() - INTERVAL '1 hour'
    AND altitude IS NOT NULL
),
transceiver_altitudes AS (
    SELECT callsign, height_msl, timestamp
    FROM transceivers 
    WHERE entity_type = 'flight'
    AND timestamp >= NOW() - INTERVAL '1 hour'
    AND height_msl IS NOT NULL
)
SELECT 
    f.callsign,
    f.altitude as flight_altitude_ft,
    t.height_msl as transceiver_altitude_m,
    (t.height_msl * 3.28084) as transceiver_altitude_ft,
    ABS(f.altitude - (t.height_msl * 3.28084)) as altitude_diff_ft
FROM flight_altitudes f
JOIN transceiver_altitudes t ON f.callsign = t.callsign
WHERE ABS(EXTRACT(EPOCH FROM (f.last_updated - t.timestamp))) <= 60
ORDER BY altitude_diff_ft DESC;
```

### **Phase 2: Code Implementation**

#### **2.1 Modify ATC Detection Service**

**File**: `app/services/atc_detection_service.py`

```python
async def _calculate_atc_metrics(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime, frequency_matches: List[Dict], completion_time: datetime) -> Dict[str, Any]:
    """Calculate ATC interaction metrics for a flight."""
    try:
        if not frequency_matches:
            return self._create_empty_atc_data()
        
        # Get total flight records for percentage calculation (unchanged)
        total_records = await self._get_flight_record_count(flight_callsign, departure, arrival, logon_time)
        if total_records == 0:
            return self._create_empty_atc_data()
        
        # Group matches by ATC callsign and calculate timing (unchanged)
        controller_data = {}
        for match in frequency_matches:
            # ... existing controller data logic ...
        
        # Calculate total controller time percentage (unchanged)
        total_controller_time = sum(ctrl["time_minutes"] for ctrl in controller_data.values())
        controller_time_percentage = min(100.0, (total_controller_time / total_records) * 100) if total_records > 0 else 0.0
        
        # FIXED: Calculate airborne controller time percentage using FLIGHTS table
        # This includes 122.8 time in the denominator
        AIRBORNE_ALT_FT = 1500
        
        # Get total airborne time from flights table (includes 122.8 time)
        total_airborne_time_minutes = await self._get_airborne_time_from_flights(
            flight_callsign, departure, arrival, logon_time, completion_time
        )
        
        # Count airborne controller contacts (from filtered transceiver data)
        airborne_contact_count = await self._count_airborne_controller_contacts(
            flight_callsign, frequency_matches, completion_time
        )
        
        # Use TRANSCEIVERS polling interval for controller contact time calculation
        # Transceivers use VATSIM_TRANSCEIVERS_POLLING_INTERVAL (120 seconds)
        transceivers_polling_interval = int(os.getenv("VATSIM_TRANSCEIVERS_POLLING_INTERVAL", "120"))
        poll_min = (transceivers_polling_interval / 60.0)
        total_airborne_controller_time_minutes = airborne_contact_count * poll_min
        
        if total_airborne_time_minutes <= 0:
            airborne_controller_time_percentage = 0.0
        else:
            airborne_controller_time_percentage = min(100.0, (total_airborne_controller_time_minutes / total_airborne_time_minutes) * 100.0)
        
        return {
            "controller_callsigns": controller_data,
            "controller_time_percentage": round(controller_time_percentage, 1),
            "airborne_controller_time_percentage": round(airborne_controller_time_percentage, 1),
            "total_controller_time_minutes": total_controller_time,
            "total_flight_records": total_records,
            "interactions_detected": len(frequency_matches)
        }
        
    except Exception as e:
        self.logger.error(f"Error calculating ATC metrics: {e}")
        return self._create_empty_atc_data()

async def _get_airborne_time_from_flights(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime, completion_time: datetime) -> float:
    """Get total airborne time from flights table (includes 122.8 time)."""
    try:
        # Count flight records where altitude > 1500ft
        query = """
            SELECT COUNT(*) as airborne_records
            FROM flights 
            WHERE callsign = :callsign
            AND departure = :departure
            AND arrival = :arrival
            AND logon_time = :logon_time
            AND last_updated >= :flight_start
            AND last_updated <= :flight_end
            AND altitude IS NOT NULL
            AND altitude > :altitude_threshold_ft
        """
        
        async with get_database_session() as session:
            result = await session.execute(text(query), {
                "callsign": flight_callsign,
                "departure": departure,
                "arrival": arrival,
                "logon_time": logon_time,
                "flight_start": logon_time,
                "flight_end": completion_time,
                "altitude_threshold_ft": 1500
            })
            
            row = result.fetchone()
            airborne_records = row.airborne_records if row else 0
        
        # Convert to minutes using FLIGHTS polling interval (VATSIM_POLLING_INTERVAL)
        # Flights and controllers use the same polling interval (60 seconds)
        flights_polling_interval = int(os.getenv("VATSIM_POLLING_INTERVAL", "60"))
        poll_min = (flights_polling_interval / 60.0)
        return airborne_records * poll_min
        
    except Exception as e:
        self.logger.error(f"Error getting airborne time from flights: {e}")
        return 0.0

async def _count_airborne_controller_contacts(self, flight_callsign: str, frequency_matches: List[Dict], completion_time: datetime) -> int:
    """Count controller contacts that occurred while aircraft was airborne."""
    try:
        airborne_contact_count = 0
        
        async with get_database_session() as session:
            for match in frequency_matches:
                match_time = match.get("flight_time")
                atc_callsign = match.get("atc_callsign")
                
                # Find the closest flight altitude record at match_time
                q = text("""
                    SELECT altitude FROM flights
                    WHERE callsign = :callsign 
                    AND altitude IS NOT NULL
                    AND last_updated <= :t
                    ORDER BY last_updated DESC
                    LIMIT 1
                """)
                res = await session.execute(q, {"callsign": flight_callsign, "t": match_time})
                r = res.fetchone()
                
                # Check both altitude AND controller type
                is_airborne_altitude = r and r[0] is not None and r[0] > 1500
                controller_type = self._detect_controller_type(atc_callsign)
                is_airborne_controller = controller_type in ["TMA", "CTR", "FSS"]
                
                if is_airborne_altitude and is_airborne_controller:
                    airborne_contact_count += 1
        
        return airborne_contact_count
        
    except Exception as e:
        self.logger.error(f"Error counting airborne controller contacts: {e}")
        return 0
```

#### **2.2 Add Helper Methods**

**File**: `app/services/atc_detection_service.py`

```python
async def _get_flight_altitude_at_time(self, flight_callsign: str, target_time: datetime) -> Optional[int]:
    """Get flight altitude at a specific time from flights table."""
    try:
        query = """
            SELECT altitude 
            FROM flights 
            WHERE callsign = :callsign 
            AND altitude IS NOT NULL
            AND last_updated <= :target_time
            ORDER BY last_updated DESC
            LIMIT 1
        """
        
        async with get_database_session() as session:
            result = await session.execute(text(query), {
                "callsign": flight_callsign,
                "target_time": target_time
            })
            
            row = result.fetchone()
            return row.altitude if row else None
            
    except Exception as e:
        self.logger.error(f"Error getting flight altitude at time: {e}")
        return None

async def _validate_flight_data_coverage(self, flight_callsign: str, logon_time: datetime, completion_time: datetime) -> Dict[str, Any]:
    """Validate that flight data has sufficient coverage for calculations."""
    try:
        query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(altitude) as records_with_altitude,
                COUNT(CASE WHEN altitude > 1500 THEN 1 END) as airborne_records,
                MIN(altitude) as min_altitude,
                MAX(altitude) as max_altitude,
                AVG(altitude) as avg_altitude
            FROM flights 
            WHERE callsign = :callsign
            AND last_updated >= :flight_start
            AND last_updated <= :flight_end
        """
        
        async with get_database_session() as session:
            result = await session.execute(text(query), {
                "callsign": flight_callsign,
                "flight_start": logon_time,
                "flight_end": completion_time
            })
            
            row = result.fetchone()
            if row:
                return {
                    "total_records": row.total_records,
                    "records_with_altitude": row.records_with_altitude,
                    "airborne_records": row.airborne_records,
                    "min_altitude": row.min_altitude,
                    "max_altitude": row.max_altitude,
                    "avg_altitude": row.avg_altitude,
                    "coverage_percentage": (row.records_with_altitude / row.total_records * 100) if row.total_records > 0 else 0
                }
            else:
                return {"error": "No flight data found"}
                
    except Exception as e:
        self.logger.error(f"Error validating flight data coverage: {e}")
        return {"error": str(e)}
```

### **Phase 3: Testing & Validation**

#### **3.1 Unit Tests**

**File**: `tests/test_atc_detection_service_option2.py`

```python
import pytest
from datetime import datetime, timezone
from app.services.atc_detection_service import ATCDetectionService

class TestATCDetectionServiceOption2:
    """Test ATC detection service with dual data sources approach."""
    
    @pytest.fixture
    def atc_service(self):
        return ATCDetectionService()
    
    @pytest.mark.asyncio
    async def test_airborne_time_calculation_with_flights_table(self, atc_service):
        """Test that airborne time calculation uses flights table data."""
        # Mock flight data with 122.8 time included
        flight_callsign = "TEST123"
        departure = "YMEL"
        arrival = "YSSY"
        logon_time = datetime.now(timezone.utc)
        completion_time = logon_time + timedelta(hours=2)
        
        # Test the new method
        airborne_time = await atc_service._get_airborne_time_from_flights(
            flight_callsign, departure, arrival, logon_time, completion_time
        )
        
        # Verify it returns a positive value
        assert airborne_time >= 0
    
    @pytest.mark.asyncio
    async def test_airborne_controller_contacts_counting(self, atc_service):
        """Test counting of airborne controller contacts."""
        # Mock frequency matches
        frequency_matches = [
            {
                "flight_time": datetime.now(timezone.utc),
                "atc_callsign": "SY_CTR",
                "frequency_mhz": 125.500
            }
        ]
        
        # Test the new method
        contact_count = await atc_service._count_airborne_controller_contacts(
            "TEST123", frequency_matches, datetime.now(timezone.utc)
        )
        
        # Verify it returns a non-negative value
        assert contact_count >= 0
    
    @pytest.mark.asyncio
    async def test_flight_data_coverage_validation(self, atc_service):
        """Test flight data coverage validation."""
        flight_callsign = "TEST123"
        logon_time = datetime.now(timezone.utc)
        completion_time = logon_time + timedelta(hours=2)
        
        # Test the validation method
        coverage = await atc_service._validate_flight_data_coverage(
            flight_callsign, logon_time, completion_time
        )
        
        # Verify it returns coverage information
        assert "total_records" in coverage
        assert "coverage_percentage" in coverage
```

#### **3.2 Integration Tests**

**File**: `tests/test_airborne_calculation_option2_integration.py`

```python
import pytest
from datetime import datetime, timezone, timedelta
from app.services.atc_detection_service import ATCDetectionService

class TestAirborneCalculationOption2Integration:
    """Integration tests for Option 2 airborne calculation."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_airborne_calculation(self):
        """Test complete airborne calculation with dual data sources."""
        atc_service = ATCDetectionService()
        
        # Test with a known flight that has 122.8 time
        flight_callsign = "QFA123"
        departure = "YMEL"
        arrival = "YSSY"
        logon_time = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # Run ATC detection
        result = await atc_service.detect_flight_atc_interactions(
            flight_callsign, departure, arrival, logon_time
        )
        
        # Verify results
        assert "airborne_controller_time_percentage" in result
        assert result["airborne_controller_time_percentage"] >= 0
        assert result["airborne_controller_time_percentage"] <= 100
        
        # Verify that 122.8 time is included in calculation
        # (This would need to be validated with actual test data)
```

### **Phase 4: Data Migration & Backfill**

#### **4.1 Flight Summaries Table Impact**

**Important**: No schema changes required to the `flight_summaries` table.

**Current Table Structure** (unchanged):
```sql
-- Existing fields remain the same
airborne_controller_time_percentage DECIMAL(5,2)  -- Field we're fixing
total_enroute_time_minutes INTEGER               -- Total time in enroute sectors (will be updated)
completion_time TIMESTAMP(0) WITH TIME ZONE      -- Used for flight time window
-- All other existing fields remain unchanged
```

**Fields That Will Be Updated**:
- **`airborne_controller_time_percentage`** - Recalculated with dual data sources
- **`total_enroute_time_minutes`** - Will be higher (includes 122.8 time)

**What Changes**:
- **Calculation logic only** - No database schema modifications
- **Two field values updated** - Both airborne-related fields will be recalculated
- **More accurate data** - Includes 122.8 time in calculations
- **No new fields** - All existing columns remain the same
- **No data loss** - All existing data is preserved

**Expected Impact on Data**:
```sql
-- Before Fix (Current)
total_enroute_time_minutes = 40 minutes (excludes 122.8)
airborne_controller_time_percentage = 75% (30/40)

-- After Fix (Option 2)
total_enroute_time_minutes = 60 minutes (includes 122.8)
airborne_controller_time_percentage = 50% (30/60)
```

#### **4.2 Validate Existing Data**

```sql
-- Check if existing flight data has sufficient altitude coverage
SELECT 
    callsign,
    COUNT(*) as total_records,
    COUNT(altitude) as records_with_altitude,
    COUNT(CASE WHEN altitude > 1500 THEN 1 END) as airborne_records,
    (COUNT(altitude)::float / COUNT(*) * 100) as altitude_coverage_percentage
FROM flights 
WHERE last_updated >= NOW() - INTERVAL '7 days'
GROUP BY callsign
HAVING COUNT(*) > 10
ORDER BY altitude_coverage_percentage DESC;
```

#### **4.3 Identify Summaries for Recalculation**

```sql
-- Identify flight summaries that need recalculation
SELECT 
    fs.callsign,
    fs.departure,
    fs.arrival,
    fs.logon_time,
    fs.airborne_controller_time_percentage,
    fs.total_enroute_time_minutes,
    fs.completion_time
FROM flight_summaries fs
WHERE fs.completion_time >= NOW() - INTERVAL '30 days'
AND (fs.airborne_controller_time_percentage = 0.0 OR fs.total_enroute_time_minutes IS NULL)
ORDER BY fs.completion_time DESC;

-- Count affected summaries
SELECT 
    COUNT(*) as total_summaries,
    COUNT(CASE WHEN airborne_controller_time_percentage = 0.0 THEN 1 END) as zero_percentage_summaries,
    COUNT(CASE WHEN airborne_controller_time_percentage IS NULL THEN 1 END) as null_percentage_summaries,
    COUNT(CASE WHEN total_enroute_time_minutes IS NULL THEN 1 END) as null_enroute_time_summaries
FROM flight_summaries 
WHERE completion_time >= NOW() - INTERVAL '30 days';

-- Check current data quality
SELECT 
    AVG(airborne_controller_time_percentage) as avg_airborne_percentage,
    AVG(total_enroute_time_minutes) as avg_enroute_time,
    COUNT(CASE WHEN airborne_controller_time_percentage > 0 THEN 1 END) as summaries_with_airborne_data,
    COUNT(CASE WHEN total_enroute_time_minutes > 0 THEN 1 END) as summaries_with_enroute_data
FROM flight_summaries 
WHERE completion_time >= NOW() - INTERVAL '7 days';
```

#### **4.4 Migration Strategy**

**Step 1: Deploy New Calculation Logic**
- Deploy updated ATC detection service with dual data sources
- New calculations will use flights table for airborne time

**Step 2: Recalculate Affected Summaries**
```python
# Pseudo-code for recalculation process
async def recalculate_airborne_data():
    """Recalculate airborne percentages and enroute time for affected flight summaries."""
    
    # Get summaries that need recalculation
    affected_summaries = await get_affected_summaries()
    
    for summary in affected_summaries:
        # Re-run ATC detection with new dual data source logic
        atc_data = await atc_detection_service.detect_flight_atc_interactions(
            summary.callsign,
            summary.departure,
            summary.arrival,
            summary.logon_time
        )
        
        # Get total enroute time from flights table (includes 122.8)
        # Uses VATSIM_POLLING_INTERVAL (60 seconds) for flights data
        total_enroute_time = await atc_detection_service._get_airborne_time_from_flights(
            summary.callsign,
            summary.departure,
            summary.arrival,
            summary.logon_time,
            summary.completion_time
        )
        
        # Update both fields in flight_summaries table
        await update_airborne_data(
            summary.id,
            {
                'airborne_controller_time_percentage': atc_data['airborne_controller_time_percentage'],
                'total_enroute_time_minutes': int(total_enroute_time)
            }
        )
```

**Step 3: Validation Queries**
```sql
-- Validate recalculation results
SELECT 
    callsign,
    departure,
    arrival,
    logon_time,
    airborne_controller_time_percentage,
    total_enroute_time_minutes,
    completion_time
FROM flight_summaries 
WHERE completion_time >= NOW() - INTERVAL '7 days'
AND airborne_controller_time_percentage > 0.0
ORDER BY airborne_controller_time_percentage DESC;

-- Check for any remaining zero percentages
SELECT COUNT(*) as remaining_zero_percentages
FROM flight_summaries 
WHERE completion_time >= NOW() - INTERVAL '7 days'
AND airborne_controller_time_percentage = 0.0;

-- Validate enroute time data
SELECT 
    COUNT(*) as total_summaries,
    COUNT(total_enroute_time_minutes) as summaries_with_enroute_time,
    AVG(total_enroute_time_minutes) as avg_enroute_time,
    MIN(total_enroute_time_minutes) as min_enroute_time,
    MAX(total_enroute_time_minutes) as max_enroute_time
FROM flight_summaries 
WHERE completion_time >= NOW() - INTERVAL '7 days';

-- Compare before/after data quality
SELECT 
    'Before Fix' as period,
    AVG(airborne_controller_time_percentage) as avg_airborne_percentage,
    AVG(total_enroute_time_minutes) as avg_enroute_time
FROM flight_summaries 
WHERE completion_time >= NOW() - INTERVAL '30 days'
AND completion_time < NOW() - INTERVAL '7 days'
UNION ALL
SELECT 
    'After Fix' as period,
    AVG(airborne_controller_time_percentage) as avg_airborne_percentage,
    AVG(total_enroute_time_minutes) as avg_enroute_time
FROM flight_summaries 
WHERE completion_time >= NOW() - INTERVAL '7 days';
```

#### **4.5 Rollback Strategy**

If issues arise, rollback is simple:
1. **Revert code** to original calculation logic
2. **No database changes** to rollback (schema unchanged)
3. **Existing data preserved** - no data loss

```sql
-- Optional: Reset airborne data to NULL for manual recalculation
UPDATE flight_summaries 
SET 
    airborne_controller_time_percentage = NULL,
    total_enroute_time_minutes = NULL
WHERE completion_time >= NOW() - INTERVAL '7 days'
AND (airborne_controller_time_percentage = 0.0 OR total_enroute_time_minutes IS NULL);
```

---

## 📊 **Expected Results**

### **Before Fix (Current)**
```
Flight spends 60 minutes airborne:
- 30 minutes on ATC frequencies (controller contact)
- 20 minutes on 122.8 MHz (UNICOM) - excluded from both numerator and denominator
- 10 minutes on other frequencies

Current calculation: (30 / 40) * 100 = 75%
- total_enroute_time_minutes = 40 minutes (excludes 122.8)
- airborne_controller_time_percentage = 75% (30/40)
```

### **After Fix (Option 2)**
```
Same flight data:
- 30 minutes on ATC frequencies (controller contact) - from transceivers table
- 20 minutes on 122.8 MHz (UNICOM) - included in denominator from flights table
- 10 minutes on other frequencies - included in denominator from flights table

Fixed calculation: (30 / 60) * 100 = 50%
- total_enroute_time_minutes = 60 minutes (includes 122.8)
- airborne_controller_time_percentage = 50% (30/60)
- More accurate representation of actual flight time
```

---

## ⚖️ **Pros and Cons Analysis**

### **Pros**
- **No data migration needed** - Uses existing flight data
- **Maintains current filtering approach** - 122.8 still excluded from controller contacts
- **Clean separation** - Different data sources for different purposes
- **Minimal code changes** - Only affects airborne time calculation
- **Backward compatible** - No changes to existing data structures

### **Cons**
- **Data source inconsistency** - Numerator and denominator from different tables
- **Potential altitude data differences** - Flights vs transceivers may have different altitude values
- **Update frequency dependency** - Both tables must have similar update frequencies
- **Complex logic** - Need to handle two different data sources
- **Validation complexity** - Need to ensure data consistency between sources

---

## 🧪 **Validation Strategy**

### **1. Data Consistency Validation**
```sql
-- Compare altitude data between flights and transceivers for same time periods
WITH flight_altitudes AS (
    SELECT callsign, altitude, last_updated
    FROM flights 
    WHERE last_updated >= NOW() - INTERVAL '1 hour'
    AND altitude IS NOT NULL
),
transceiver_altitudes AS (
    SELECT callsign, height_msl, timestamp
    FROM transceivers 
    WHERE entity_type = 'flight'
    AND timestamp >= NOW() - INTERVAL '1 hour'
    AND height_msl IS NOT NULL
)
SELECT 
    f.callsign,
    COUNT(*) as comparison_count,
    AVG(ABS(f.altitude - (t.height_msl * 3.28084))) as avg_altitude_diff_ft,
    MAX(ABS(f.altitude - (t.height_msl * 3.28084))) as max_altitude_diff_ft
FROM flight_altitudes f
JOIN transceiver_altitudes t ON f.callsign = t.callsign
WHERE ABS(EXTRACT(EPOCH FROM (f.last_updated - t.timestamp))) <= 60
GROUP BY f.callsign
ORDER BY avg_altitude_diff_ft DESC;
```

### **2. Coverage Validation**
```sql
-- Check flight data coverage for recent flights
SELECT 
    DATE(last_updated) as date,
    COUNT(*) as total_flights,
    COUNT(altitude) as flights_with_altitude,
    (COUNT(altitude)::float / COUNT(*) * 100) as altitude_coverage_percentage
FROM flights 
WHERE last_updated >= NOW() - INTERVAL '7 days'
GROUP BY DATE(last_updated)
ORDER BY date DESC;
```

### **3. Calculation Validation**
```python
# Test with known flight data
def test_airborne_calculation_accuracy():
    """Test that airborne calculation is accurate with known data."""
    # Use a flight with known 122.8 time
    # Verify that 122.8 time is included in denominator
    # Verify that controller contacts exclude 122.8
    pass
```

---

## 🚨 **Risk Assessment**

### **Low Risk**
- No data migration required
- Backward compatible changes
- Existing data structures unchanged

### **Medium Risk**
- Data source inconsistency between flights and transceivers
- Potential altitude data differences
- Complex validation requirements

### **Mitigation Strategies**
- Comprehensive data validation before deployment
- Gradual rollout with monitoring
- Fallback to original calculation if issues arise
- Extensive testing with real flight data

---

## 📋 **Implementation Checklist**

### **Phase 1: Data Analysis**
- [ ] Validate flight data coverage and quality
- [ ] Compare altitude data between flights and transceivers
- [ ] Identify any data consistency issues
- [ ] Document findings and recommendations

### **Phase 2: Code Implementation**
- [ ] Implement `_get_airborne_time_from_flights()` method
- [ ] Implement `_count_airborne_controller_contacts()` method
- [ ] Add flight data validation methods
- [ ] Update `_calculate_atc_metrics()` to use dual data sources
- [ ] Add comprehensive error handling

### **Phase 3: Testing**
- [ ] Write unit tests for new methods
- [ ] Create integration tests
- [ ] Test with sample flight data
- [ ] Validate calculation accuracy
- [ ] Performance testing

### **Phase 4: Deployment**
- [ ] Deploy to staging environment
- [ ] Run validation queries
- [ ] Test with real flight data
- [ ] Monitor for issues
- [ ] Deploy to production

### **Phase 5: Validation**
- [ ] Recalculate existing flight summaries
- [ ] Compare results with expected values
- [ ] Monitor system performance
- [ ] Document any issues or improvements

---

## 📝 **Conclusion**

Option 2 provides a clean solution that uses existing data sources without requiring data migration. By using the flights table for airborne time calculation and the transceivers table for controller contact detection, we can ensure that 122.8 MHz time is properly included in the denominator while maintaining the correct exclusion from controller contacts.

**Key Benefits**:
- No data migration required
- Maintains current filtering approach
- Clean separation of concerns
- Minimal code changes

**Key Considerations**:
- Need to ensure data consistency between sources
- Requires comprehensive validation
- More complex logic than Option 1

**Next Steps**:
1. Validate flight data coverage and quality
2. Implement the dual data source approach
3. Test thoroughly with real data
4. Deploy with monitoring and validation
