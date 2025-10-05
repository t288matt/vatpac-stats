# Flight Duration Calculation Issue Analysis

## Problem Statement
The system was incorrectly calculating flight duration metrics by using controller interaction time instead of actual flight time. This caused flights with minimal or no ATC interaction to show incorrectly short durations, even though they actually flew for much longer periods.

## Detailed Findings

### Issue 1: Enrichment Overwriting Core Flight Metrics

**Location**: `app/services/summary_enrichment_worker.py` 

The enrichment process (which focuses on ATC interactions) was incorrectly modifying core flight metrics:

```python
# Complete the enrichment in the same transaction
await session.execute(text("""
    UPDATE flight_summaries
    SET controller_callsigns = :controller_callsigns,
        controller_time_percentage = :ctp,
        airborne_controller_time_percentage = :actp,
        time_online_minutes = :time_online,        # <-- Problematic field
        total_enroute_time_minutes = :enroute,     # <-- Problematic field
        enrichment_status = 'completed',
        enrichment_completed_at = now(),
        enrichment_last_error = NULL,
        updated_at = now()
    WHERE id = :id
"""), {
    "controller_callsigns": controller_callsigns_json,
    "ctp": atc_data.get("controller_time_percentage", None),
    "actp": atc_data.get("airborne_controller_time_percentage", None),
    "time_online": atc_data.get("total_controller_time_minutes", None),  # Using controller time!
    "enroute": total_enroute_minutes,
    "id": fs_id
})
```

**Impact**: Flight `THY3PT` showed 0 minutes duration despite actually flying for 139 minutes because it had no controller interaction (UNICOM frequency 122.8).

### Issue 2: Canonical Processing Resetting Duration Values

**Location**: `app/services/data_service.py`

The canonical processing's update statement had a COALESCE function that could potentially overwrite existing values:

```sql
time_online_minutes = COALESCE(time_online_minutes, :time_online_minutes),
```

**Impact**: When flight lookup failed or returned no data, the parameter `:time_online_minutes` was set to NULL, and the COALESCE function would erase any existing value.

## Testing Process

After implementing the initial fix to the enrichment process, we conducted testing to verify the solution:

1. **Manual Data Setting**: We set a specific flight (FJI910) to have `time_online_minutes = 139`
   ```sql
   UPDATE flight_summaries SET time_online_minutes = 139, 
     enrichment_status = 'pending' WHERE callsign = 'FJI910';
   ```

2. **Forced Re-enrichment**: Reset the enrichment status to 'pending' to trigger the enrichment worker

3. **Verification Check**: After enrichment completed, we queried to check if the value was preserved:
   ```sql
   SELECT callsign, time_online_minutes, enrichment_status 
   FROM flight_summaries WHERE callsign = 'FJI910';
   ```

4. **Discovery**: Despite fixing enrichment, the value was reset to 0
   ```
   callsign | time_online_minutes | enrichment_status 
   ---------+--------------------+-------------------
   FJI910   |                  0 | completed
   ```

This testing revealed that even with the enrichment fix, something else was resetting the values, which led us to discover the second issue in canonical processing.

## Solutions Implemented

### Fix 1: Remove Flight Duration Fields from Enrichment

Modified `summary_enrichment_worker.py` to stop updating flight duration metrics:

```python
# Complete the enrichment in the same transaction
await session.execute(text("""
    UPDATE flight_summaries
    SET controller_callsigns = :controller_callsigns,
        controller_time_percentage = :ctp,
        airborne_controller_time_percentage = :actp,
        enrichment_status = 'completed',          # Removed problematic fields
        enrichment_completed_at = now(),
        enrichment_last_error = NULL,
        updated_at = now()
    WHERE id = :id
"""), {
    "controller_callsigns": controller_callsigns_json,
    "ctp": atc_data.get("controller_time_percentage", None),
    "actp": atc_data.get("airborne_controller_time_percentage", None),
    "id": fs_id                                   # Removed problematic parameters
})
```

### Fix 2: Preserve Existing Duration Values in Canonical Processing

Modified `data_service.py` to use CASE statements instead of COALESCE to explicitly preserve existing values:

```sql
-- Do not update time_online_minutes if it already has a value
time_online_minutes = CASE
    WHEN time_online_minutes IS NULL THEN :time_online_minutes
    ELSE time_online_minutes
END,
```

Same approach was applied to `total_enroute_time_minutes`.

## Expected Impact

With these changes:

1. Flight durations will be correctly calculated based on actual flight time (from login to completion)
2. Flights without ATC interaction will still show their correct flight duration
3. Analytics and reporting based on flight duration will be accurate
4. Once a proper duration value is set, it won't be accidentally reset by either system

This ensures all flights show their true duration regardless of whether they talked to controllers or not.
