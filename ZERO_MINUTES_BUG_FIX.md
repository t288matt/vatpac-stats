# Flight Summary Zero Minutes Bug - Fix Documentation

**Date:** October 12, 2025  
**Priority:** 🔴 CRITICAL  
**Status:** Root cause identified, fix designed  

---

## Symptom

Flight summaries are being created with `time_online_minutes = 0` despite flights having actual durations of hours.

### Observable Behavior

```sql
SELECT id, callsign, logon_time, completion_time, time_online_minutes,
       EXTRACT(EPOCH FROM (completion_time - logon_time))/60 AS expected_minutes
FROM flight_summaries 
WHERE time_online_minutes = 0 
AND completion_time > logon_time
LIMIT 5;

-- Example Results:
-- QFA842:  time_online_minutes = 0, expected = 295 minutes (4.9 hours)
-- UAE15K:  time_online_minutes = 0, expected = 285 minutes (4.8 hours)
-- JST735:  time_online_minutes = 0, expected = 136 minutes (2.3 hours)
```

### Key Indicators

1. **`time_online_minutes = 0`** despite non-zero logon-to-completion duration
2. **Affects all flight types** (international, domestic, regional, GA)
3. **`completion_time`** matches timestamp of FIRST record, not LAST
4. **Multiple records exist** in flights table for the affected flight
5. **Bug only occurs during initial processing** - reprocessing after deletion produces correct values

### Impact Metrics

From 7 examined cases:
- **Total data loss:** 1,030+ minutes (~17.2 hours)
- **Average loss per flight:** 147 minutes (~2.5 hours)
- **Reproduction rate:** 100% for flights processed during "dangerous window"

---

## Root Cause

The session selector applies the completion_hours filter at the **RECORD level** instead of the **FLIGHT level**, causing flights to be processed prematurely when only some of their records are old enough.

### The "Dangerous Window"

A time window exists between when the **first** record becomes eligible and when the **last** record becomes eligible:

```
Flight Timeline (QFA842 example):
09:11:19 - Pilot logs on
09:12:29 - First record captured
14:07:13 - Last record captured (actual end)

Eligibility Timeline (8 hours later):
17:12:29 - First record becomes eligible  ← Dangerous window STARTS
22:07:13 - Last record becomes eligible   ← Dangerous window ENDS

Duration: 4 hours 54 minutes (dangerous window)
```

If the canonical processor runs **during this window**, it processes the flight with incomplete data.

### The Bug Chain

**1. Session Selector (lines 70, 91 in `session_selector.py`)**

```sql
-- Filters each RECORD individually
WHERE NOW() >= last_updated + (8 * INTERVAL '1 hour')
```

At 17:12:43 (14 seconds into dangerous window):
- Only 1 record (09:12:29) passes the filter
- Other 291 records excluded (not yet 8 hours old)

**2. Session Calculation (line 173)**

```sql
MAX(last_updated) AS session_end
-- MAX of 1 record = 09:12:29 (WRONG! Should be 14:07:13)
```

**3. Canonical Processor Receives Wrong Data**

```python
session_start = 09:11:19
session_end = 09:12:29  # Only includes first record!
```

**4. Time Calculation (lines 2496-2529 in `data_service.py`)**

```sql
SELECT MIN(last_updated), MAX(last_updated)
FROM flights
WHERE last_updated BETWEEN 09:11:19 AND 09:12:29  -- Only finds 1 record
```

Result:
```python
MIN = 09:12:29
MAX = 09:12:29  # Same as MIN!
time_online_minutes = (MAX - MIN) / 60 = 0 minutes
```

**5. Permanent Lock**

Flight summary created and marked as "processed" → future runs exclude it via `NOT EXISTS` clause → the 291 later records are NEVER processed.

### Why It Works After Deletion

When you delete and reprocess days later:
- **ALL** records are now 8+ hours old
- Session selector includes **ALL** 292 records
- `MAX(last_updated) = 14:07:13` ✅ Correct
- `time_online_minutes = 295` ✅ Correct

### Timing Analysis

**Bad Timing:** QFA842 processed at 17:12:43

```
17:11:43  Scheduler completed previous run, started 60s sleep
17:12:29  First record becomes eligible (dangerous window opens)
17:12:43  Scheduler wakes up (14 seconds into dangerous window) ← BUG OCCURS
17:13:29  Second record becomes eligible (46 seconds too late)
```

The scheduler has no coordination with record eligibility - it runs on its own schedule (60-900 second intervals). Pure bad luck it woke up exactly when only 1 record was eligible.

---

## Proposed Fix

### Location

**File:** `app/services/session_selector.py`  
**Lines:** 36-92 (entire query needs modification)

### Strategy

Change from **RECORD-level filtering** to **FLIGHT-level filtering**:
- Identify flights where the **LATEST** record is 8+ hours old
- Include **ALL** records for those flights (no time filter on individual records)

### Code Changes

**Current Code (BUGGY):**

```python
query = text(
    """
    WITH processed_flights AS (
        SELECT DISTINCT callsign, cid, departure, arrival, logon_time
        FROM flight_summaries
    ),
    base AS (
        SELECT ...
        FROM flights
        WHERE NOW() >= last_updated + ((:completion_hours)::int * INTERVAL '1 hour')  ← BUG
        UNION ALL
        SELECT ...
        FROM flights_archive
        WHERE NOW() >= last_updated + ((:completion_hours)::int * INTERVAL '1 hour')  ← BUG
    ),
    ...
```

**Fixed Code:**

```python
query = text(
    """
    WITH processed_flights AS (
        SELECT DISTINCT callsign, cid, departure, arrival, logon_time
        FROM flight_summaries
    ),
    flight_completion_times AS (
        -- NEW: Find when each flight's LATEST record was captured
        SELECT 
            callsign,
            cid,
            departure,
            arrival,
            MAX(last_updated) AS latest_record_time
        FROM (
            SELECT callsign, cid, departure, arrival, last_updated
            FROM flights
            UNION ALL
            SELECT callsign, cid, departure, arrival, last_updated
            FROM flights_archive
        ) all_records
        GROUP BY callsign, cid, departure, arrival
    ),
    eligible_flights AS (
        -- NEW: Only include flights where LATEST record is old enough
        SELECT callsign, cid, departure, arrival
        FROM flight_completion_times
        WHERE NOW() >= latest_record_time + ((:completion_hours)::int * INTERVAL '1 hour')
    ),
    base AS (
        -- MODIFIED: Get ALL records for eligible flights
        SELECT 
            f.callsign,
            f.cid,
            f.departure,
            f.arrival,
            COALESCE(f.logon_time, f.last_updated) AS logon_time,
            f.last_updated,
            f.deptime,
            f.route,
            f.aircraft_type,
            f.aircraft_faa,
            f.aircraft_short,
            f.flight_rules,
            f.planned_altitude,
            f.name,
            f.server,
            f.pilot_rating,
            f.military_rating
        FROM flights f
        INNER JOIN eligible_flights ef
            ON f.callsign = ef.callsign
            AND f.cid = ef.cid
            AND f.departure = ef.departure
            AND f.arrival = ef.arrival
        UNION ALL
        SELECT 
            fa.callsign,
            fa.cid,
            fa.departure,
            fa.arrival,
            COALESCE(fa.logon_time, fa.last_updated) AS logon_time,
            fa.last_updated,
            fa.deptime,
            fa.route,
            fa.aircraft_type,
            fa.aircraft_faa,
            fa.aircraft_short,
            fa.flight_rules,
            fa.planned_altitude,
            fa.name,
            fa.server,
            fa.pilot_rating,
            fa.military_rating
        FROM flights_archive fa
        INNER JOIN eligible_flights ef
            ON fa.callsign = ef.callsign
            AND fa.cid = ef.cid
            AND fa.departure = ef.departure
            AND fa.arrival = ef.arrival
    ),
    -- Rest of query unchanged (ordered, segmented, labeled, sessions)
    ...
```

### What This Fixes

**Before Fix:**
- At 17:12:43, filters records individually
- Finds only 1 record (09:12:29)
- `session_end = 09:12:29`
- Flight processed with incomplete data
- `time_online_minutes = 0`

**After Fix:**
- At 17:12:43, checks if flight's LATEST record (14:07:13) is 8+ hours old
- 14:07:13 + 8 hours = 22:07:13 (not yet reached)
- Flight NOT eligible → skipped
- Next check at 22:08 (after dangerous window)
- ALL 292 records included
- `session_end = 14:07:13`
- `time_online_minutes = 295` ✅

### Why This Works

The dangerous window is eliminated:
- A flight won't be processed until its **LAST** record is 8+ hours old
- When processing begins, **ALL** records are guaranteed to be included
- `MAX(last_updated)` will always be the actual last record
- Time calculations work correctly

---

## Testing Plan

### Phase 1: Single Flight Test

**1. Create a backup:**
```sql
CREATE TABLE flight_summaries_backup_20251012 AS 
SELECT * FROM flight_summaries WHERE time_online_minutes = 0;
```

**2. Delete test flight:**
```sql
DELETE FROM flight_summaries WHERE id = 42630; -- QFA842
```

**3. Apply the fix** to `app/services/session_selector.py`

**4. Restart the application**

**5. Wait for next scheduled run** (60-900 seconds)

**6. Verify recreation:**
```sql
SELECT callsign, cid, departure, arrival, 
       logon_time, completion_time, time_online_minutes
FROM flight_summaries
WHERE callsign = 'QFA842' 
  AND cid = 1627668
  AND departure = 'YSSY' 
  AND arrival = 'YPDN'
  AND logon_time = '2025-10-07 09:11:19+00';
```

**Expected Results:**
- `completion_time = 2025-10-07 14:07:13+00` (NOT 09:12:29)
- `time_online_minutes ≈ 295` (NOT 0)

### Phase 2: Batch Verification

**Delete all 7 test flights:**
```sql
DELETE FROM flight_summaries 
WHERE id IN (42630, 42618, 42668, 42639, 42626, 42684, 42672);
```

**Wait for recreation and verify all have non-zero times**

### Phase 3: Production Monitoring

**Monitor for new zero-minute flights:**
```sql
SELECT COUNT(*) AS new_zero_minute_flights
FROM flight_summaries
WHERE time_online_minutes = 0
  AND created_at >= NOW() - INTERVAL '1 day'
  AND EXISTS (
      SELECT 1 FROM (
          SELECT 1 FROM flights f WHERE f.callsign = flight_summaries.callsign 
            AND f.cid = flight_summaries.cid 
            AND f.departure = flight_summaries.departure 
            AND f.arrival = flight_summaries.arrival
          UNION ALL
          SELECT 1 FROM flights_archive fa WHERE fa.callsign = flight_summaries.callsign 
            AND fa.cid = flight_summaries.cid 
            AND fa.departure = flight_summaries.departure 
            AND fa.arrival = flight_summaries.arrival
          LIMIT 2
      ) records
  );
```

**Expected:** Count should remain at 0 after fix

---

## Recovery Plan for Historical Data

### Option 1: Full Reprocessing (Recommended)

**Pros:** Complete fix, all metrics recalculated correctly  
**Cons:** System load, takes time

```sql
-- Find all problematic flights
WITH problematic AS (
    SELECT fs.id
    FROM flight_summaries fs
    WHERE fs.time_online_minutes = 0
      AND fs.completion_time > fs.logon_time
      AND EXISTS (
          SELECT 1 FROM (
              SELECT 1 FROM flights f 
              WHERE f.callsign = fs.callsign AND f.cid = fs.cid
                AND f.departure = fs.departure AND f.arrival = fs.arrival
              UNION ALL
              SELECT 1 FROM flights_archive fa 
              WHERE fa.callsign = fs.callsign AND fa.cid = fs.cid
                AND fa.departure = fs.departure AND fa.arrival = fs.arrival
              LIMIT 2  -- More than 1 record = problematic
          ) records
      )
)
DELETE FROM flight_summaries
WHERE id IN (SELECT id FROM problematic);

-- Canonical processor will recreate them correctly
```

### Option 2: SQL Update (Fast but Limited)

**Pros:** Immediate fix  
**Cons:** Doesn't recalculate ATC metrics, sectors, etc.

```sql
-- Update time_online_minutes and completion_time directly
WITH corrections AS (
    SELECT 
        fs.id,
        (SELECT MIN(last_updated) FROM (
            SELECT last_updated FROM flights 
            WHERE callsign = fs.callsign AND cid = fs.cid
              AND departure = fs.departure AND arrival = fs.arrival
            UNION ALL
            SELECT last_updated FROM flights_archive 
            WHERE callsign = fs.callsign AND cid = fs.cid
              AND departure = fs.departure AND arrival = fs.arrival
        ) combined) AS first_record,
        (SELECT MAX(last_updated) FROM (
            SELECT last_updated FROM flights 
            WHERE callsign = fs.callsign AND cid = fs.cid
              AND departure = fs.departure AND arrival = fs.arrival
            UNION ALL
            SELECT last_updated FROM flights_archive 
            WHERE callsign = fs.callsign AND cid = fs.cid
              AND departure = fs.departure AND arrival = fs.arrival
        ) combined) AS last_record
    FROM flight_summaries fs
    WHERE fs.time_online_minutes = 0
      AND fs.completion_time > fs.logon_time
)
UPDATE flight_summaries fs
SET 
    completion_time = c.last_record,
    time_online_minutes = EXTRACT(EPOCH FROM (c.last_record - c.first_record)) / 60
FROM corrections c
WHERE fs.id = c.id;
```

---

## Validation Queries

### Find Currently Affected Flights

```sql
SELECT 
    fs.id,
    fs.callsign,
    fs.departure,
    fs.arrival,
    fs.time_online_minutes,
    (SELECT COUNT(*) FROM (
        SELECT 1 FROM flights WHERE callsign = fs.callsign AND cid = fs.cid 
          AND departure = fs.departure AND arrival = fs.arrival
        UNION ALL
        SELECT 1 FROM flights_archive WHERE callsign = fs.callsign AND cid = fs.cid 
          AND departure = fs.departure AND arrival = fs.arrival
    ) r) AS record_count,
    (SELECT MAX(last_updated) - MIN(last_updated) FROM (
        SELECT last_updated FROM flights WHERE callsign = fs.callsign AND cid = fs.cid 
          AND departure = fs.departure AND arrival = fs.arrival
        UNION ALL
        SELECT last_updated FROM flights_archive WHERE callsign = fs.callsign AND cid = fs.cid 
          AND departure = fs.departure AND arrival = fs.arrival
    ) r) AS actual_duration
FROM flight_summaries fs
WHERE fs.time_online_minutes = 0
  AND fs.completion_time > fs.logon_time
ORDER BY record_count DESC
LIMIT 20;
```

### Verify Fix After Deployment

```sql
-- Should return 0 after fix is deployed and sufficient time has passed
SELECT COUNT(*) AS suspicious_flights
FROM flight_summaries
WHERE time_online_minutes = 0
  AND created_at >= NOW() - INTERVAL '1 day'
  AND completion_time > logon_time;
```

---

## Risk Assessment

### Deployment Risk: LOW

- **Code change:** Single SQL query modification in session selector
- **Scope:** Only affects flight eligibility determination
- **Reversibility:** Easy rollback (revert code change)
- **Testing:** Can be tested on single flight before full deployment

### Impact of NOT Fixing: HIGH

- **Data integrity:** Ongoing corruption of flight duration metrics
- **Analytics:** Incorrect reports and statistics
- **Trust:** Stakeholder confidence in data quality
- **Compliance:** Inaccurate aviation record-keeping

### Mitigation Strategy

1. **Test in non-production first** (if available)
2. **Deploy during low-activity period**
3. **Monitor for 24 hours** after deployment
4. **Have rollback plan ready** (simple code revert)
5. **Keep backup** of affected records before recovery

---

## Success Criteria

✅ **Fix is successful when:**

1. No new flights created with `time_online_minutes = 0` (except valid single-record flights)
2. Reprocessed test flights (QFA842, etc.) show correct times
3. `completion_time` values match last record timestamps
4. Monitoring query returns 0 suspicious flights
5. No performance degradation in session selector

---

## Related Files

- **Bug Report:** `ZERO_MINUTES_BUG_EXAMPLES.md` - Detailed database analysis
- **Investigation:** `ZERO_MINUTES_BUG_INVESTIGATION_COMPLETE.md` - Full investigation
- **Queries:** `find_zero_minutes_problem.sql` - Diagnostic SQL
- **Original Document:** `FLIGHT_SUMMARY_ZERO_MINUTES_FIX.md` - Initial report (incorrect fix)

---

**Document Author:** AI Assistant  
**Date:** October 12, 2025  
**Status:** Ready for Implementation  
**Approval Required:** Yes  



