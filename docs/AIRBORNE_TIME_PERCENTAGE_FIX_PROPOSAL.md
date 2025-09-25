# Airborne Time Percentage Calculation Fix Proposal

**Date**: January 2025  
**Issue**: GitHub Issue #82 - Fix the Airborne Time Percentage Calculation  
**Status**: Analysis Complete - Implementation Proposal Ready

---

## 📋 **Issue Summary**

The `airborne_controller_time_percentage` field in `flight_summaries` is incorrectly calculated due to inconsistent handling of 122.8 MHz (UNICOM) frequency data. The current implementation excludes 122.8 time from both the numerator (controller contacts) and denominator (airborne time), creating an inconsistent percentage calculation.

### **The Core Problem**

- **122.8 MHz frequencies are filtered out** during data ingestion (`data_service.py:459`)
- **Both numerator and denominator** use the same filtered transceiver data
- **Result**: 122.8 time is missing from both calculations, but the question is whether 122.8 time should count as "airborne time"

---

## 🔍 **Current Data Flow Analysis**

### **1. Data Ingestion** (`app/services/data_service.py`)
```python
# Line 459: Apply frequency filtering (exclude UNICOM frequencies like 122.800 MHz)
filtered_transceivers = self.frequency_pattern_filter.filter_transceivers_list(filtered_transceivers)
```
- Raw VATSIM transceiver data comes in
- **122.8 MHz frequencies are filtered out** by `frequency_pattern_filter`
- Only filtered transceiver data is stored in database

### **2. ATC Detection** (`app/services/atc_detection_service.py`)
```python
# Loads flight transceivers using load_transceivers_for_callsign()
# This data is already filtered (no 122.8 records exist in DB)
flight_transceivers = await self._get_flight_transceivers(flight_callsign, departure, arrival, logon_time)
```
- Loads flight transceivers using `load_transceivers_for_callsign()`
- **This data is already filtered** (no 122.8 records exist in DB)
- Uses this filtered data for both:
  - **Numerator**: Controller contact detection (correctly excludes 122.8)
  - **Denominator**: Airborne time calculation (incorrectly excludes 122.8)

### **3. The Problem**
- **Numerator**: Controller contacts exclude 122.8 ✅ (correct)
- **Denominator**: Airborne time excludes 122.8 ❌ (incorrect)
- **Result**: Inconsistent percentage calculation

---

## 🎯 **Root Cause**

The issue is that **122.8 time is missing from the denominator** (airborne time calculation) because:

1. 122.8 transceiver records are filtered out during data ingestion
2. The airborne time calculation queries the same filtered transceiver data
3. This creates an inconsistent calculation where 122.8 time is excluded from both numerator and denominator

**Current Calculation**:
```
airborne_controller_time_percentage = (controller_time_excluding_122.8 / airborne_time_excluding_122.8) * 100
```

**Desired Calculation**:
```
airborne_controller_time_percentage = (controller_time_excluding_122.8 / total_airborne_time_including_122.8) * 100
```

---

## 💡 **Proposed Solutions**

### **Option 1: Modify Data Ingestion (Recommended)**

**Approach**: Store ALL transceiver data (including 122.8) but apply frequency filtering only during ATC detection.

#### **Changes Required**:

1. **Remove frequency filtering from data ingestion** (`data_service.py:459`)
2. **Add frequency filtering to ATC detection** (only for controller contact detection)
3. **Use unfiltered data for airborne time calculation**

#### **Pros**:
- Clean separation of concerns
- Maintains data integrity
- Allows flexible filtering strategies
- Fixes the core issue at the source

#### **Cons**:
- Increases database storage (122.8 records stored)
- Requires data migration for existing data

### **Option 2: Dual Data Sources (Alternative)**

**Approach**: Use flight data for airborne time calculation, transceiver data for controller contacts.

#### **Changes Required**:
1. **Modify airborne time calculation** to use `flights` table instead of `transceivers` table
2. **Keep controller contact detection** using filtered transceiver data
3. **Add altitude tracking to flights table** (if not already present)

#### **Pros**:
- No data migration needed
- Maintains current filtering approach

#### **Cons**:
- Flights table may not have sufficient altitude data
- Creates data source inconsistency
- More complex logic

### **Option 3: Post-Processing Fix (Quick Fix)**

**Approach**: Estimate 122.8 time and add it to the denominator calculation.

#### **Changes Required**:
1. **Query for 122.8 frequency usage** from raw VATSIM data (if available)
2. **Estimate 122.8 airborne time** based on flight duration
3. **Add estimated time to denominator** in percentage calculation

#### **Pros**:
- Minimal code changes
- No data migration

#### **Cons**:
- Estimation-based (not accurate)
- Complex logic
- May not be reliable

---

## 🚀 **Recommended Solution: Option 1**

### **Implementation Plan**

#### **Phase 1: Data Ingestion Changes**

1. **Modify `app/services/data_service.py`**:
   ```python
   # Remove this line:
   # filtered_transceivers = self.frequency_pattern_filter.filter_transceivers_list(filtered_transceivers)
   
   # Replace with:
   # Store all transceiver data - filtering applied later during ATC detection
   ```

2. **Update `app/filters/frequency_pattern_filter.py`**:
   - Add method to filter transceivers for ATC detection only
   - Keep existing filtering for other use cases

#### **Phase 2: ATC Detection Changes**

1. **Modify `app/services/atc_detection_service.py`**:
   ```python
   # Add frequency filtering for controller contact detection only
   def _filter_controller_contacts(self, frequency_matches: List[Dict]) -> List[Dict]:
       """Filter out 122.8 frequencies from controller contact detection"""
       return [match for match in frequency_matches 
               if not self._is_unicom_frequency(match.get("frequency_mhz"))]
   
   # Use unfiltered data for airborne time calculation
   async def _get_airborne_time_records(self, flight_callsign: str, logon_time: datetime, completion_time: datetime) -> int:
       """Get ALL airborne transceiver records (including 122.8) for denominator calculation"""
       # Query without frequency filtering
   ```

2. **Update transceiver loading**:
   - Add parameter to `load_transceivers_for_callsign()` for filtering
   - Create separate methods for filtered vs unfiltered data

#### **Phase 3: Data Migration**

1. **Backfill missing 122.8 data**:
   - Re-process historical VATSIM data
   - Add 122.8 transceiver records to database

2. **Update existing flight summaries**:
   - Re-run ATC detection for affected flights
   - Recalculate airborne percentages

### **Code Changes Required**

#### **1. Data Service (`app/services/data_service.py`)**
```python
async def _process_transceivers(self, transceivers_data: List[Dict[str, Any]]) -> int:
    """
    Process and store transceiver data with geographic boundary filtering.
    """
    if not transceivers_data:
        return 0
    
    processed_count = 0
    
    # Apply geographic boundary filtering
    if self.geographic_boundary_filter.config.enabled:
        filtered_transceivers = self.geographic_boundary_filter.filter_transceivers_list(transceivers_data)
    else:
        filtered_transceivers = transceivers_data
    
    # REMOVED: Frequency filtering at ingestion level
    # filtered_transceivers = self.frequency_pattern_filter.filter_transceivers_list(filtered_transceivers)
    
    # Store all transceiver data - frequency filtering applied during ATC detection
    # Log only summary, not individual transceiver details
    if len(transceivers_data) != len(filtered_transceivers):
        self.logger.info(f"Transceivers: {len(transceivers_data)} → {len(filtered_transceivers)} (geographic filtered)")
    else:
        self.logger.debug(f"Transceivers: {len(transceivers_data)} → {len(filtered_transceivers)}")
```

#### **2. ATC Detection Service (`app/services/atc_detection_service.py`)**
```python
async def _calculate_atc_metrics(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime, frequency_matches: List[Dict], completion_time: datetime) -> Dict[str, Any]:
    """Calculate ATC interaction metrics for a flight."""
    try:
        if not frequency_matches:
            return self._create_empty_atc_data()
        
        # Apply frequency filtering to controller contacts (numerator)
        filtered_frequency_matches = self._filter_controller_contacts(frequency_matches)
        
        # Get total flight records for percentage calculation
        total_records = await self._get_flight_record_count(flight_callsign, departure, arrival, logon_time)
        if total_records == 0:
            return self._create_empty_atc_data()
        
        # Group matches by ATC callsign and calculate timing (using filtered matches)
        controller_data = {}
        for match in filtered_frequency_matches:  # Use filtered matches for controller data
            # ... existing controller data logic ...
        
        # Calculate airborne controller time percentage using ALL transceiver data (denominator)
        # Use transceiver height_msl (meters) converted to feet for the threshold
        AIRBORNE_ALT_FT = 1500
        AIRBORNE_ALT_M = AIRBORNE_ALT_FT / 3.28084

        # FIXED: Use ALL flight transceiver records (including 122.8) for airborne time calculation
        async with get_database_session() as session:
            enroute_count_res = await session.execute(text("""
                SELECT COUNT(*) FROM transceivers t
                WHERE t.entity_type = 'flight'
                  AND t.callsign = :callsign
                  AND t.timestamp >= :flight_start
                  AND t.timestamp <= :flight_end
                  AND t.height_msl IS NOT NULL
                  AND t.height_msl > :alt_m
                  -- Note: This query includes ALL frequencies (including 122.8) for airborne time calculation
                  -- Controller contacts (numerator) use filtered transceiver data
            """), {
                "callsign": flight_callsign,
                "flight_start": logon_time,
                "flight_end": completion_time,
                "alt_m": AIRBORNE_ALT_M
            })
            enroute_count_row = enroute_count_res.fetchone()
            enroute_records = enroute_count_row[0] if enroute_count_row else 0

        # Classify each frequency match as airborne if flight is above 1500ft AND controller is airborne type
        # Use filtered matches for airborne contact counting
        airborne_contact_count = 0
        async with get_database_session() as session:
            for match in filtered_frequency_matches:  # Use filtered matches
                match_time = match.get("flight_time")
                atc_callsign = match.get("atc_callsign")
                
                # Find the closest transceiver height record for this flight at match_time
                q = text("""
                    SELECT height_msl FROM transceivers
                    WHERE entity_type = 'flight' AND callsign = :callsign AND height_msl IS NOT NULL
                      AND timestamp <= :t
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                res = await session.execute(q, {"callsign": flight_callsign, "t": match_time})
                r = res.fetchone()
                
                # Check both altitude AND controller type
                is_airborne_altitude = r and r[0] is not None and r[0] > AIRBORNE_ALT_M
                controller_type = self._detect_controller_type(atc_callsign)
                is_airborne_controller = controller_type in ["TMA", "CTR", "FSS"]
                
                if is_airborne_altitude and is_airborne_controller:
                    airborne_contact_count += 1

        poll_min = (self.vatsim_polling_interval_seconds / 60.0)
        total_airborne_controller_time_minutes = airborne_contact_count * poll_min
        total_enroute_time_minutes = enroute_records * poll_min

        if total_enroute_time_minutes <= 0:
            airborne_controller_time_percentage = 0.0
        else:
            airborne_controller_time_percentage = min(100.0, (total_airborne_controller_time_minutes / total_enroute_time_minutes) * 100.0)
        
        return {
            "controller_callsigns": controller_data,
            "controller_time_percentage": round(controller_time_percentage, 1),
            "airborne_controller_time_percentage": round(airborne_controller_time_percentage, 1),
            "total_controller_time_minutes": total_controller_time,
            "total_flight_records": total_records,
            "interactions_detected": len(filtered_frequency_matches)
        }
        
    except Exception as e:
        self.logger.error(f"Error calculating ATC metrics: {e}")
        return self._create_empty_atc_data()

def _filter_controller_contacts(self, frequency_matches: List[Dict]) -> List[Dict]:
    """Filter out 122.8 frequencies from controller contact detection."""
    if not frequency_matches:
        return []
    
    filtered_matches = []
    for match in frequency_matches:
        frequency_mhz = match.get("frequency_mhz")
        if not self._is_unicom_frequency(frequency_mhz):
            filtered_matches.append(match)
    
    return filtered_matches

def _is_unicom_frequency(self, frequency_mhz: float) -> bool:
    """Check if frequency is UNICOM (122.8 MHz)."""
    if not frequency_mhz:
        return False
    
    # Round to 3 decimal places for comparison
    rounded_freq = round(frequency_mhz, 3)
    return rounded_freq == 122.800
```

#### **3. Transceiver Loader (`app/services/transceiver_loader.py`)**
```python
async def load_transceivers_for_callsign(
    start: datetime,
    end: datetime, 
    entity_type: str,
    callsign: str,
    apply_frequency_filter: bool = False,  # New parameter
    page_size: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load transceivers for a specific callsign and entity_type within [start, end].
    Uses keyset pagination.
    
    Args:
        apply_frequency_filter: If True, exclude 122.8 MHz frequencies
    """
    results: List[Dict[str, Any]] = []
    use_page_size = _get_page_size(page_size)

    last_ts = start.replace(microsecond=0) if start is not None else datetime.min.replace(tzinfo=timezone.utc)
    last_id = 0

    while True:
        base = (
            "SELECT id as transceiver_id, callsign, frequency, position_lat, position_lon, height_msl, height_agl, timestamp, entity_type "                                            
            "FROM transceivers WHERE timestamp >= :start AND timestamp <= :end AND entity_type = :entity_type AND callsign = :callsign"                        
        )
        
        # Add frequency filtering if requested
        if apply_frequency_filter:
            base += " AND (frequency IS NULL OR ROUND(frequency/1000000.0, 3) != 122.800)"
        
        base += " AND (timestamp > :last_ts OR (timestamp = :last_ts AND id > :last_id)) ORDER BY timestamp, id LIMIT :limit"

        async with get_database_session() as session:
            params = {
                "start": start,
                "end": end,
                "entity_type": entity_type,
                "callsign": callsign,
                "last_ts": last_ts,
                "last_id": last_id,
                "limit": use_page_size,
            }
            res = await session.execute(text(base), params)
            rows = res.fetchall()

        if not rows:
            break

        for row in rows:
            results.append(
                {
                    "transceiver_id": row.transceiver_id,
                    "callsign": row.callsign,
                    "frequency": row.frequency,
                    "frequency_mhz": (row.frequency / 1000000.0) if row.frequency is not None else None,                                                       
                    "position_lat": row.position_lat,
                    "position_lon": row.position_lon,
                    "height_msl": row.height_msl,
                    "height_agl": row.height_agl,
                    "timestamp": row.timestamp,
                    "entity_type": row.entity_type,
                }
            )

        last_row = rows[-1]
        last_ts = last_row.timestamp
        last_id = last_row.transceiver_id

        if len(rows) < use_page_size:
            break

    return results
```

---

## 📊 **Expected Results**

After implementing this fix:

1. **Numerator (Controller Contacts)**: Still excludes 122.8 ✅
2. **Denominator (Airborne Time)**: Includes 122.8 time ✅
3. **Percentage Calculation**: `(controller_time / total_airborne_time) * 100` ✅
4. **Data Consistency**: Both calculations use appropriate data sources ✅

### **Example Calculation**

**Before Fix**:
```
Flight spends 60 minutes airborne:
- 30 minutes on ATC frequencies (controller contact)
- 20 minutes on 122.8 MHz (UNICOM)
- 10 minutes on other frequencies

Current calculation: (30 / 40) * 100 = 75%
- Denominator excludes 122.8 time (40 minutes instead of 60)
```

**After Fix**:
```
Same flight data:
- 30 minutes on ATC frequencies (controller contact)
- 20 minutes on 122.8 MHz (UNICOM) - included in denominator
- 10 minutes on other frequencies

Fixed calculation: (30 / 60) * 100 = 50%
- Denominator includes all airborne time (60 minutes)
```

---

## 🧪 **Validation Strategy**

### **1. Test with Sample Flight**
- Select a flight with significant 122.8 time
- Compare before/after percentages
- Verify 122.8 time is included in denominator

### **2. Verify Controller Contacts**
- Ensure controller contact detection still excludes 122.8 frequencies
- Validate frequency matching logic works correctly

### **3. Regression Testing**
- Run tests on existing flight summaries
- Compare results with expected values
- Ensure no breaking changes to other functionality

### **4. Data Integrity Checks**
- Verify all transceiver data is stored (including 122.8)
- Check that filtering works correctly during ATC detection
- Validate percentage calculations are mathematically correct

---

## 📋 **Implementation Checklist**

### **Phase 1: Data Ingestion**
- [ ] Remove frequency filtering from `data_service.py`
- [ ] Update logging to reflect new filtering approach
- [ ] Test data ingestion with 122.8 frequencies

### **Phase 2: ATC Detection**
- [ ] Add frequency filtering to ATC detection service
- [ ] Update transceiver loader with filtering parameter
- [ ] Modify airborne time calculation to use unfiltered data
- [ ] Add unit tests for new filtering logic

### **Phase 3: Data Migration**
- [ ] Backfill missing 122.8 data from historical sources
- [ ] Re-run ATC detection for affected flights
- [ ] Update existing flight summaries
- [ ] Validate percentage calculations

### **Phase 4: Testing & Validation**
- [ ] Run comprehensive test suite
- [ ] Validate with sample flights
- [ ] Performance testing with larger datasets
- [ ] Documentation updates

---

## 🔧 **Configuration Changes**

### **Environment Variables**
No new environment variables required. The existing `EXCLUDED_FREQUENCIES_MHZ` will be used for ATC detection filtering instead of data ingestion filtering.

### **Database Schema**
No schema changes required. The existing `transceivers` table will store additional 122.8 frequency records.

---

## 📈 **Performance Impact**

### **Storage Impact**
- **Increase**: ~20-30% more transceiver records (122.8 frequencies)
- **Mitigation**: 122.8 records are typically short-duration, minimal impact

### **Query Performance**
- **ATC Detection**: Slightly faster (no filtering during data loading)
- **Airborne Calculation**: Same performance (direct database query)
- **Overall**: Minimal impact, potentially improved due to reduced filtering overhead

---

## 🚨 **Risk Assessment**

### **Low Risk**
- Data integrity maintained
- Backward compatibility preserved
- Rollback possible if issues arise

### **Mitigation Strategies**
- Implement feature flags for gradual rollout
- Monitor performance metrics during deployment
- Maintain backup of current implementation
- Comprehensive testing before production deployment

---

## 📝 **Conclusion**

This fix addresses the root cause of the airborne time percentage calculation issue by ensuring that 122.8 MHz time is properly included in the denominator while maintaining the correct exclusion from controller contact calculations. The solution provides a clean, maintainable approach that preserves data integrity and calculation accuracy.

**Next Steps**:
1. Review and approve this proposal
2. Implement Phase 1 (Data Ingestion changes)
3. Test with sample data
4. Proceed with Phases 2-4 as outlined above

