# Flight Summary Zero Minutes Bug Fix

## Issue Summary

Many flight summaries have `time_online_minutes = 0` despite having actual flight duration. This affects data quality and downstream analytics.

Example: SIA223 had `time_online_minutes = 0` while its actual flight duration was 257 minutes (logon→completion).

## Root Cause Analysis

After extensive investigation, we identified that flight summaries are being created prematurely with incorrect completion times:

1. The session selector is finding only the first record when a flight enters Australian airspace
2. It sets `session_end` to that timestamp (e.g., 09:06:03 for SIA223)
3. The canonical processor creates a flight summary with:
   - `completion_time = session_end` (09:06:03)
   - `time_online_minutes = 0` because when querying for records between `session_start` and `session_end`, it only finds one record, so `MIN(last_updated) = MAX(last_updated)`

Evidence from database analysis:

```sql
-- Flights with 0 time_online_minutes all show this pattern:
SELECT id, callsign, logon_time, completion_time, time_online_minutes, 
       EXTRACT(EPOCH FROM (completion_time - logon_time))/60 AS actual_minutes 
FROM flight_summaries 
WHERE time_online_minutes = 0 
ORDER BY created_at DESC LIMIT 10;
```

For flights with multiple records, the `completion_time` always matches the timestamp of the first record in Australian airspace, not the last record when the flight left airspace or landed.

The 8-hour inactivity requirement is being bypassed because the session selector is only looking at individual records, not the entire flight history.

## Fix Implementation

1. **Modify `app/services/session_selector.py` to respect the 8-hour inactivity requirement:**

```python
async def select_canonical_sessions(
    completion_hours: int,
    gap_minutes: int,
    max_span_hours: int = 24,
) -> List[Dict[str, Any]]:
    # ...existing code...
    
    query = text(
        """
        WITH processed_flights AS (
            -- First get all the processed flights (any flight summary record exists)
            SELECT DISTINCT 
                callsign, 
                cid, 
                departure, 
                arrival
            FROM flight_summaries
            -- No enrichment status filter - canonical only cares if record exists
        ),
        base AS (
            SELECT 
                callsign,
                cid,
                departure,
                arrival,
                COALESCE(logon_time, last_updated) AS logon_time,
                last_updated,
                deptime,
                route,
                aircraft_type,
                aircraft_faa,
                aircraft_short,
                flight_rules,
                planned_altitude,
                name,
                server,
                pilot_rating,
                military_rating
            FROM flights
            WHERE NOW() >= last_updated + ((:completion_hours)::int * INTERVAL '1 hour')
            -- More efficient anti-join using the processed_flights CTE
            AND NOT EXISTS (
                SELECT 1
                FROM processed_flights pf
                WHERE pf.callsign = flights.callsign
                AND pf.cid = flights.cid
                AND pf.departure = flights.departure
                AND pf.arrival = flights.arrival
            )
            UNION ALL
            -- Similar for flights_archive
        ),
        flight_groups AS (
            -- Group flights by callsign, cid, departure, arrival
            SELECT 
                callsign,
                cid,
                departure,
                arrival,
                MIN(logon_time) AS min_logon_time,
                MIN(last_updated) AS min_last_updated,
                MAX(last_updated) AS max_last_updated
            FROM base
            GROUP BY callsign, cid, departure, arrival
        ),
        inactive_flights AS (
            -- Only select flights that have been inactive for at least completion_hours
            SELECT *
            FROM flight_groups
            WHERE NOW() >= max_last_updated + ((:completion_hours)::int * INTERVAL '1 hour')
        )
        -- Rest of the query remains the same, but uses inactive_flights instead of base
        """
    )
    # ...rest of the function...
```

2. **Modify `app/services/data_service.py` to use the full range of records when calculating `time_online_minutes`:**

```python
async def _process_completed_flights_canonical(self, limit: Optional[int] = None) -> Dict[str, Any]:
    # ...existing code...
    
    # When calculating time_online_minutes, use the full range of records
    first_last_sql = text("""
        SELECT MIN(last_updated) AS first_updated, MAX(last_updated) AS last_updated
        FROM (
            SELECT last_updated FROM flights 
            WHERE callsign = :callsign 
            AND cid = :cid
            AND departure = :departure 
            AND arrival = :arrival
            UNION ALL
            SELECT last_updated FROM flights_archive 
            WHERE callsign = :callsign 
            AND cid = :cid
            AND departure = :departure 
            AND arrival = :arrival
        ) combined
    """)
    
    # ...rest of the function...
```

3. **Ensure `completion_time` is always set to the latest record's timestamp:**

```python
# In the INSERT statement
INSERT INTO flight_summaries (
    ...
    completion_time,
    ...
) VALUES (
    ...
    :actual_completion_time,  -- Use the actual completion time, not session_end
    ...
)
```

4. **Add a validation check to ensure `time_online_minutes` is calculated correctly:**

```python
# After calculating time_online_minutes
if time_online_minutes == 0 and fl_row.first_updated != fl_row.last_updated:
    # If first_updated and last_updated are different but time_online_minutes is 0,
    # there's likely a calculation error
    self.logger.warning(f"Possible time_online_minutes calculation error for {callsign}: first={fl_row.first_updated}, last={fl_row.last_updated}")
    # Recalculate using the actual difference
    time_online_minutes = int((fl_row.last_updated - fl_row.first_updated).total_seconds() / 60)
```

## Validation

To validate the fix:

1. Remove all flight summaries with `time_online_minutes = 0`
2. Apply the fix
3. Wait for the canonical processor to recreate the summaries
4. Verify that the recreated summaries have correct `time_online_minutes` values

For SIA223, we confirmed that after removing the incorrect summary and allowing the canonical processor to recreate it:
- `completion_time` changed from 09:06:03 to 13:23:39 (the actual time the flight left Australian airspace)
- `time_online_minutes` changed from 0 to 257 minutes

## Benefits

This fix ensures:
1. Only flights that have been truly inactive for the required period are processed
2. The `completion_time` is set to the actual last record's timestamp
3. `time_online_minutes` is calculated correctly using the full range of records
4. Data quality is improved for downstream analytics and reporting
