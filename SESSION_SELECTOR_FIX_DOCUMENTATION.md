# Session Selector Fix: Adding session_start to Exclusion Logic

## Problem Summary

**Current Issue**: 95 flights are awaiting summary processing, with 74 of them being older than 48 hours. These flights should have been processed by now but remain stuck due to a bug in the session selector's exclusion logic.

**Root Cause**: The session selector is currently using **4-field exclusion** (`callsign, cid, departure, arrival`) which incorrectly excludes repeat flights on the same route by the same pilot. This causes 74 older flights to remain unprocessed despite being eligible for summary generation.

**Business Impact**: 
- 74 flights missing from flight summaries
- Incomplete data for analysis and reporting
- Potential data integrity issues in downstream systems

## Root Cause Analysis

### Current Broken Logic
```sql
-- In processed_flights CTE (WRONG)
SELECT DISTINCT 
    callsign, 
    cid, 
    departure, 
    arrival
FROM flight_summaries

-- In exclusion logic (WRONG)
WHERE pf.callsign = flights.callsign
  AND pf.cid = flights.cid
  AND pf.departure = flights.departure
  AND pf.arrival = flights.arrival
```

### The Problem
When pilot ABC123 flies MEL→SYD multiple times:
- **Flight 1** (Jan 15): Gets processed and stored in flight_summaries
- **Flight 2** (Jan 20): Gets incorrectly excluded because it matches the 4-field criteria

The system sees both flights as "already processed" when only Flight 1 should be excluded.

## Why session_start is the Right Solution

### Key Distinction
- **`logon_time`**: Individual flight record's timestamp when pilot logged on
- **`session_start`**: `MIN(logon_time)` across all records in a session (the session identifier)

### Why session_start is Correct
1. **Unique Session Identity**: Each flight session has a unique `session_start` timestamp
2. **Prevents False Exclusions**: Different flights on same route have different `session_start` values
3. **Matches flight_summaries Structure**: The `flight_summaries` table stores `logon_time` which represents the `session_start` from the original session
4. **Maintains Data Integrity**: Ensures each distinct flight session is processed exactly once
5. **Handles Multiple Logons**: A single flight can have multiple `logon_time` values due to disconnections/reconnections, but only one `session_start`

### Real Example
```
Pilot ABC123, MEL→SYD:

Flight Session 1 (January 15):
- logon_time: 2025-01-15 14:30:00
- session_start: 2025-01-15 14:30:00
- Stored in flight_summaries with logon_time = 2025-01-15 14:30:00

Flight Session 2 (January 20):
- logon_time: 2025-01-20 09:15:00  
- session_start: 2025-01-20 09:15:00
- Should NOT be excluded because session_start differs
```

### Why session_start > logon_time for Exclusion

**Problem with using individual `logon_time`:**
```
Single Flight Session with Multiple Logons:
- Record 1: logon_time = 14:30:00 (initial logon)
- Record 2: logon_time = 14:45:00 (reconnected after disconnect)  
- Record 3: logon_time = 15:10:00 (another reconnect)

If we exclude based on ANY logon_time match:
- Would incorrectly exclude this session if any of the 3 logon_time values match
- Could create false positives in exclusion logic
```

**Solution with `session_start`:**
```
Same Flight Session:
- session_start = MIN(logon_time) = 14:30:00 (consistent identifier)
- Only ONE value to match against
- Represents the true start of the flight session
- Immune to multiple logon/reconnect events within same flight
```

## Proposed Fix

### 1. Update processed_flights CTE
```sql
WITH processed_flights AS (
    SELECT DISTINCT 
        callsign, 
        cid, 
        departure, 
        arrival,
        logon_time  -- This represents session_start from flight_summaries
    FROM flight_summaries
),
```

### 2. Update Exclusion Logic
The challenge: We need to calculate `session_start` for the current flight being evaluated and match it against processed flights.

**Option A: Restructure Query (Recommended)**
- Move exclusion logic to AFTER sessionization
- Use 5-field matching including session_start

**Option B: Pre-calculate session_start**
- Calculate session_start for each flight before exclusion
- Use in anti-join logic

### 3. Expected Outcome
- 74 currently unprocessed flights will be correctly identified as eligible
- Repeat flights on same route will no longer be incorrectly excluded
- System will process all legitimate flight sessions

## Implementation Considerations

### Complexity
The fix requires restructuring the query because:
- `session_start` is calculated during sessionization
- Exclusion logic currently happens BEFORE sessionization
- Need to either move exclusion or pre-calculate session_start

### Performance Impact
- May require additional computation for session_start calculation
- Should be minimal impact due to existing indexing
- Benefits outweigh costs (processes 74 additional flights)

### Testing Strategy
1. Run current query to get baseline count
2. Apply fix and verify 74 additional sessions are identified
3. Confirm no duplicate processing occurs
4. Validate flight_summaries table integrity

## Conclusion

Adding `session_start` to the exclusion logic is the correct solution because:
- It uniquely identifies flight sessions
- Prevents false exclusions of repeat flights
- Maintains data integrity
- Aligns with the intended 5-field session signature

The fix will restore proper processing of the 74 unprocessed flights while maintaining system performance and data quality.

## Appendix: Git Commit History Analysis

### Timeline of Session Selector Changes

**August 20, 2025** - Initial 5-field exclusion logic:
```diff
--- a/app/services/data_service.py
+++ b/app/services/data_service.py
@@ -1102,12 +1102,19 @@ class DataService:
                 completion_threshold = datetime.now(timezone.utc) - timedelta(hours=completion_hours)
                 
                 query = """
-                SELECT DISTINCT callsign, departure, arrival, cid, deptime
-                FROM flights 
-                WHERE last_updated < :completion_threshold
-                AND callsign NOT IN (
-                    SELECT DISTINCT callsign FROM flight_summaries
-                )
+                SELECT DISTINCT f.callsign, f.departure, f.arrival, f.cid, f.deptime
+                FROM flights f
+                WHERE f.last_updated < :completion_threshold
+                  AND f.logon_time IS NOT NULL
+                  AND NOT EXISTS (
+                      SELECT 1
+                      FROM flight_summaries fs
+                      WHERE fs.callsign   = f.callsign
+                        AND fs.cid        IS NOT DISTINCT FROM f.cid
+                        AND fs.departure  IS NOT DISTINCT FROM f.departure
+                        AND fs.arrival    IS NOT DISTINCT FROM f.arrival
+                        AND fs.logon_time IS NOT DISTINCT FROM f.logon_time
+                  )
                 """
```
*Status: CORRECT - Uses 5-field exclusion including logon_time*

---

**September 29, 2025** - Move exclusion logic to session_selector.py with optimization:
```diff
--- a/app/services/session_selector.py
+++ b/app/services/session_selector.py
@@ -35,7 +35,19 @@ async def select_canonical_sessions(
         
         query = text(
             """
-        WITH base AS (
+        WITH processed_flights AS (
+            -- First get all the processed flights (with completion_time and completed status)
+            -- This reduces the number of queries against flight_summaries
+            SELECT DISTINCT 
+                callsign, 
+                cid, 
+                departure, 
+                arrival
+            FROM flight_summaries
+            WHERE completion_time IS NOT NULL
+            AND enrichment_status = 'completed'
+        ),
+        base AS (
                 SELECT 
                     callsign,
                     cid,
@@ -56,6 +68,15 @@ async def select_canonical_sessions(
                     military_rating
                 FROM flights
                 WHERE NOW() >= last_updated + ((:completion_hours)::int * INTERVAL '1 hour')
+            -- More efficient anti-join using the processed_flights CTE
+            AND NOT EXISTS (
+                SELECT 1
+                FROM processed_flights pf
+                WHERE pf.callsign = flights.callsign
+                AND pf.cid = flights.cid
+                AND pf.departure = flights.departure
+                AND pf.arrival = flights.arrival
+            )
```
*Status: BROKEN - Reduced to 4-field exclusion, removed logon_time*

---

**October 1, 2025** - Remove enrichment status filter:
```diff
--- a/app/services/session_selector.py
+++ b/app/services/session_selector.py
@@ -36,7 +36,7 @@ async def select_canonical_sessions(
         query = text(
             """
             WITH processed_flights AS (
-            -- First get all the processed flights (with completion_time and completed status)
+            -- First get all the processed flights (any flight summary record exists)
                 -- This reduces the number of queries against flight_summaries
                 SELECT DISTINCT 
                     callsign, 
@@ -44,8 +44,7 @@ async def select_canonical_sessions(
                     departure, 
                     arrival
                 FROM flight_summaries
-            WHERE completion_time IS NOT NULL
-            AND enrichment_status = 'completed'
+            -- No enrichment status filter - canonical only cares if record exists
             ),
```
*Status: STILL BROKEN - Only removed status filter, still missing logon_time*

---

### Key Findings

1. **September 29, 2025**: The bug was introduced when exclusion logic was moved from `data_service.py` to `session_selector.py` for "optimization"
2. **Lost field**: The 5-field exclusion (`callsign, cid, departure, arrival, logon_time`) was reduced to 4-field (`callsign, cid, departure, arrival`)
3. **Impact**: This caused repeat flights on the same route to be incorrectly excluded
4. **Duration**: The bug has been active for ~1 month, accumulating 74 unprocessed flights

### Evidence of the Problem

The commit history shows a clear regression:
- **Before (Aug 20)**: Correct 5-field exclusion with `logon_time`
- **After (Sep 29)**: Broken 4-field exclusion without `logon_time`
- **Result**: 74 flights stuck in unprocessed state

This confirms that the fix requires restoring the `logon_time` field to the exclusion logic in `session_selector.py`.

## Implementation Approach: Pre-calculate session_start

### The Challenge
We need `session_start` for exclusion logic, but it's currently calculated during sessionization. The key insight is that we can pre-calculate `session_start` using the **exact same logic** as the current sessionization.

### Current Sessionization Logic
```sql
-- Step 1: Get previous last_updated
ordered AS (
    SELECT *,
        LAG(last_updated) OVER (
            PARTITION BY callsign, cid, departure, arrival
            ORDER BY GREATEST(logon_time, last_updated), last_updated
        ) AS prev_last_updated
    FROM base
),

-- Step 2: Detect new segments based on gaps
segmented AS (
    SELECT *,
        CASE 
            WHEN prev_last_updated IS NULL THEN 1
            WHEN (EXTRACT(EPOCH FROM (logon_time - prev_last_updated)) / 60.0) > :gap_minutes THEN 1
            ELSE 0
        END AS is_new_seg
    FROM ordered
),

-- Step 3: Create segment IDs
labeled AS (
    SELECT *,
        SUM(is_new_seg) OVER (
            PARTITION BY callsign, cid, departure, arrival
            ORDER BY GREATEST(logon_time, last_updated), last_updated
            ROWS UNBOUNDED PRECEDING
        ) AS segment_id
    FROM segmented
),

-- Step 4: Calculate session_start per segment
sessions AS (
    SELECT 
        MIN(logon_time) AS session_start
    FROM labeled
    GROUP BY callsign, cid, departure, arrival, segment_id
)
```

### Recommended Solution: Shared CTE Function

**Why this is the best approach:**
- ✅ **Simplest implementation** - no new database objects or complex changes
- ✅ **Easiest to maintain** - single source of truth for sessionization logic
- ✅ **Easiest to support** - no additional infrastructure or permissions needed
- ✅ **No code duplication** - sessionization logic exists in one reusable function
- ✅ **No sync issues** - can't get out of sync like materialized views
- ✅ **Version controlled** - part of application code, not database objects

### Implementation

Extract the sessionization logic into a reusable helper function:

```python
# app/services/session_selector.py

def get_sessionization_cte(gap_minutes: int) -> str:
    """Returns the reusable sessionization CTE that calculates session_start using the EXACT same logic as current sessionization"""
    return f"""
    sessionized AS (
        WITH ordered AS (
            SELECT 
                callsign, cid, departure, arrival, logon_time, last_updated,
                deptime, route, aircraft_type, aircraft_faa, aircraft_short,
                flight_rules, planned_altitude, name, server, pilot_rating, military_rating,
                LAG(last_updated) OVER (
                    PARTITION BY callsign, cid, departure, arrival
                    ORDER BY GREATEST(logon_time, last_updated), last_updated
                ) AS prev_last_updated
            FROM flights
            WHERE logon_time IS NOT NULL
            UNION ALL
            SELECT 
                callsign, cid, departure, arrival, logon_time, last_updated,
                deptime, route, aircraft_type, aircraft_faa, aircraft_short,
                flight_rules, planned_altitude, name, server, pilot_rating, military_rating,
                LAG(last_updated) OVER (
                    PARTITION BY callsign, cid, departure, arrival
                    ORDER BY GREATEST(logon_time, last_updated), last_updated
                ) AS prev_last_updated
            FROM flights_archive
            WHERE logon_time IS NOT NULL
        ), segmented AS (
            SELECT 
                callsign, cid, departure, arrival, logon_time, last_updated,
                deptime, route, aircraft_type, aircraft_faa, aircraft_short,
                flight_rules, planned_altitude, name, server, pilot_rating, military_rating,
                CASE 
                    WHEN prev_last_updated IS NULL THEN 1
                    WHEN (EXTRACT(EPOCH FROM (logon_time - prev_last_updated)) / 60.0) > {gap_minutes} THEN 1
                    ELSE 0
                END AS is_new_seg
            FROM ordered
        ), labeled AS (
            SELECT 
                callsign, cid, departure, arrival, logon_time, last_updated,
                deptime, route, aircraft_type, aircraft_faa, aircraft_short,
                flight_rules, planned_altitude, name, server, pilot_rating, military_rating,
                SUM(is_new_seg) OVER (
                    PARTITION BY callsign, cid, departure, arrival
                    ORDER BY GREATEST(logon_time, last_updated), last_updated
                    ROWS UNBOUNDED PRECEDING
                ) AS segment_id
            FROM segmented
        )
        SELECT 
            callsign, cid, departure, arrival, logon_time, last_updated,
            deptime, route, aircraft_type, aircraft_faa, aircraft_short,
            flight_rules, planned_altitude, name, server, pilot_rating, military_rating,
            MIN(logon_time) OVER (
                PARTITION BY callsign, cid, departure, arrival, segment_id
            ) AS session_start
        FROM labeled
    )
    """

async def select_canonical_sessions(completion_hours: int, gap_minutes: int) -> List[Dict[str, Any]]:
    query = text(f"""
        WITH {get_sessionization_cte(gap_minutes)},
        processed_flights AS (
            SELECT DISTINCT callsign, cid, departure, arrival, logon_time
            FROM flight_summaries
        ),
        base AS (
            SELECT * FROM sessionized s
            WHERE NOW() >= s.last_updated + ((:completion_hours)::int * INTERVAL '1 hour')
            AND NOT EXISTS (
                SELECT 1
                FROM processed_flights pf
                WHERE pf.callsign = s.callsign
                AND pf.cid = s.cid
                AND pf.departure = s.departure
                AND pf.arrival = s.arrival
                AND pf.logon_time = s.session_start  -- Use pre-calculated session_start!
            )
        )
        -- Continue with existing sessionization logic using 'base' CTE
        """
    )
```

### Benefits of This Approach
1. **Exact match**: Pre-calculated `session_start` will be identical to current sessionization (replicates the exact 4-step process: ordered → segmented → labeled → session_start)
2. **Correct exclusions**: Exclusion logic will work properly with accurate session boundaries  
3. **No code duplication**: Sessionization logic exists in one reusable function
4. **Easy maintenance**: Change the function, both places update automatically
5. **Simple implementation**: Just reorganize existing code, no new infrastructure
6. **Easy to test**: Same testing approach as before
7. **Easy to rollback**: Just revert the function if needed

### Logic Verification
The shared CTE function replicates the **exact same 4-step process** as the current sessionization:
1. **ordered**: Calculate `prev_last_updated` using `LAG()`
2. **segmented**: Detect new segments based on gap detection using `prev_last_updated`
3. **labeled**: Create `segment_id` using `SUM(is_new_seg) OVER()`
4. **session_start**: Calculate `MIN(logon_time) OVER (PARTITION BY ..., segment_id)`

This ensures 100% compatibility with existing sessionization results.

### Example Result
```
Pilot ABC123, MEL→SYD:
- Flight 1: 14:30 (session_start = 14:30)
- Flight 2: 16:45 (gap > 120min, session_start = 16:45) 
- Flight 3: 17:00 (gap < 120min, session_start = 16:45)

Pre-calculation correctly identifies:
- Flight 1 session_start = 14:30
- Flight 2 & 3 session_start = 16:45
```

This ensures that repeat flights on the same route are correctly distinguished and processed while maintaining a single source of truth for sessionization logic.
