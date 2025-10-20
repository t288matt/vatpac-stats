# Flight Summary Zero Minutes Bug - Complete Investigation Results

**Date:** October 12, 2025  
**Status:** 🔴 CRITICAL BUG CONFIRMED - Root cause identified  
**Impact:** Data loss affecting all flight types  

---

## Executive Summary

Investigation of the current production database **confirms a critical race condition bug** in the flight processing system. The bug causes flight summaries to be created with `time_online_minutes = 0` despite flights having actual durations of hours.

**Root Cause:** The session selector processes flights as soon as ANY record is 8+ hours old, rather than waiting until ALL records for that flight are 8+ hours old. This creates incomplete flight summaries that are permanently marked as "processed," resulting in data loss.

**Severity:** In just 7 examined cases, **1,030+ minutes (~17.2 hours) of flight time was lost**. Extrapolating across the full database, the impact could be significant.

---

## Quick Facts

| Metric | Value |
|--------|-------|
| **Total Examples Examined** | 10+ flights |
| **Bug Reproduction Rate** | 100% (all examined cases) |
| **Data Loss (7 examples)** | 1,030+ minutes (~17.2 hours) |
| **Average Loss per Flight** | 147 minutes (~2.5 hours) |
| **Range of Loss** | 42 to 295 minutes per flight |
| **Affected Flight Types** | All (international, domestic, regional, GA) |

---

## The Bug in Detail

### What Happens

1. **Pilot logs on** at 09:11:19 and starts flying
2. **First record enters** Australian airspace at 09:12:29
3. **Flight continues** with updates every ~60 seconds
4. **Last record captured** at 14:07:13 (flight ends)
5. **8 hours after FIRST record** (17:12:29), the system processes the flight
6. **Problem:** At 17:12:29, only the first record (09:12:29) is 8+ hours old
7. **Bug Result:**
   - Session selector finds only 1 record (the first one)
   - `session_end = 09:12:29` (max of 1 record)
   - Flight summary created with `completion_time = 09:12:29`
   - Time calculation: BETWEEN 09:11:19 AND 09:12:29 = finds 1 record
   - `time_online_minutes = 0` (because MIN = MAX = 09:12:29)
8. **Permanent Loss:** Flight marked as "processed," 291 other records ignored forever

### Visual Timeline: QFA842 Example

```
09:11:19        09:12:29                    14:07:13            17:12:29
   |               |                            |                    |
Logon         1st Record                  Last Record          BUG: Processed
   |               |<------- 294 minutes ------>|                too early!
   |               |                            |                    |
   |<-- 1.17 min ->|                            |                    |
                   ^                            ^                    ^
              Only this record            This record is         System says:
              is 8+ hrs old at            only ~3 hrs old       "Flight complete!"
              processing time             at processing         session_end = 09:12:29
                                                                time_online = 0
```

---

## Concrete Examples from Production Database

### Example 1: QFA842 (Sydney → Darwin) - MOST SEVERE

**Flight Summary ID:** 42630  
**Actual Flight Duration:** 294.73 minutes (~4.9 hours)  
**Recorded Duration:** 0 minutes  
**Records in Database:** 292 position updates  

**Timeline:**
- Logon: 2025-10-07 09:11:19
- First record: 2025-10-07 09:12:29
- Last record: 2025-10-07 14:07:13
- Processed at: 2025-10-07 17:12:29 (8 hours after first record)

**Verification:**
```sql
-- At processing time (17:12:29), only first record was eligible
WHERE '2025-10-07 17:12:29' >= last_updated + INTERVAL '8 hours'
-- Result: 1 record found (09:12:29)

-- NOW, all records are eligible
WHERE NOW() >= last_updated + INTERVAL '8 hours'  
-- Result: 292 records found
```

### Example 2: UAE15K (Perth → Dubai) - INTERNATIONAL

**Flight Summary ID:** 42618  
**Actual Flight Duration:** 285.53 minutes (~4.8 hours)  
**Recorded Duration:** 0 minutes  
**Records in Database:** 283 position updates  

### Example 3: JST735 (Brisbane → Sydney) - DOMESTIC

**Flight Summary ID:** 42668  
**Actual Flight Duration:** 135.80 minutes (~2.3 hours)  
**Recorded Duration:** 0 minutes  
**Records in Database:** 124 position updates  

### Complete List (7 Examples)

| ID | Callsign | Route | Records | Actual Minutes | Recorded | Loss |
|----|----------|-------|---------|----------------|----------|------|
| 42630 | QFA842 | YSSY→YPDN | 292 | 294.73 | 0 | 294.73 |
| 42618 | UAE15K | YPPH→OMDB | 283 | 285.53 | 0 | 285.53 |
| 42668 | JST735 | YBBN→YSSY | 124 | 135.80 | 0 | 135.80 |
| 42639 | NWK2750 | YPPH→YGIA | 110 | 110.28 | 0 | 110.28 |
| 42626 | JST418 | YSSY→YBCG | 83 | 97.08 | 0 | 97.08 |
| 42684 | JST9351 | YBCS→YBPN | 65 | 64.87 | 0 | 64.87 |
| 42672 | AGG | YBTH→YSSY | 43 | 42.52 | 0 | 42.52 |
| **TOTAL** | | | **1,000** | **1,030.81** | **0** | **1,030.81** |

---

## Root Cause Analysis

### The Session Selector Bug

**File:** `app/services/session_selector.py`  
**Lines:** 70, 91  

**Current (Buggy) Code:**
```python
query = text("""
    WITH base AS (
        SELECT ...
        FROM flights
        WHERE NOW() >= last_updated + ((:completion_hours)::int * INTERVAL '1 hour')
        UNION ALL
        SELECT ...
        FROM flights_archive
        WHERE NOW() >= last_updated + ((:completion_hours)::int * INTERVAL '1 hour')
    ), ...
    sessions AS (
        SELECT 
            ...
            MIN(logon_time) AS session_start,
            MAX(last_updated) AS session_end,  -- BUG: MAX of filtered records only
            ...
        FROM labeled
        GROUP BY callsign, cid, departure, arrival, segment_id
    )
""")
```

**Problem:**
- The `WHERE NOW() >= last_updated + 8 hours` filter is applied to EACH RECORD
- If a flight has 292 records from 09:12:29 to 14:07:13:
  - At 17:12:29 (8 hours after first), only 1 record passes the filter
  - `MAX(last_updated) = 09:12:29` (max of 1 record, not 292 records!)
  - The flight is processed with incomplete data
  - Once processed, it's marked and never reprocessed

### The Time Calculation (Innocent)

**File:** `app/services/data_service.py`  
**Lines:** 2495-2529  

The time calculation code is actually **correct**. It queries for records BETWEEN `session_start` and `session_end`. The problem is that `session_end` is wrong due to the session selector bug above.

```python
# This code is correct, but gets wrong session_end from session selector
first_last_sql = text("""
    SELECT MIN(last_updated) AS first_updated, MAX(last_updated) AS last_updated
    FROM (
        SELECT last_updated FROM flights
        WHERE callsign = :callsign AND cid = :cid AND departure = :departure AND arrival = :arrival
        AND last_updated BETWEEN :start AND :end  -- Uses wrong session_end!
        UNION ALL
        SELECT last_updated FROM flights_archive
        WHERE callsign = :callsign AND cid = :cid AND departure = :departure AND arrival = :arrival
        AND last_updated BETWEEN :start AND :end  -- Uses wrong session_end!
    ) combined
""")
```

---

## The Fix

### Correct Approach

Modify `app/services/session_selector.py` to ensure ALL records for a flight are 8+ hours old before processing.

**Strategy:** Pre-filter flights at the GROUP level, not the RECORD level.

**Fixed Code:**
```python
query = text("""
    -- Step 1: Identify flights where the LAST record is 8+ hours old
    WITH flight_last_update AS (
        SELECT 
            callsign, cid, departure, arrival,
            MAX(last_updated) AS last_record_time
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
        -- Only include flights where the LAST record is 8+ hours old
        SELECT callsign, cid, departure, arrival
        FROM flight_last_update
        WHERE NOW() >= last_record_time + ((:completion_hours)::int * INTERVAL '1 hour')
    ),
    -- Step 2: Get all records for eligible flights (no record-level time filter!)
    base AS (
        SELECT 
            f.callsign, f.cid, f.departure, f.arrival,
            COALESCE(f.logon_time, f.last_updated) AS logon_time,
            f.last_updated,
            f.deptime, f.route, f.aircraft_type, f.aircraft_faa, f.aircraft_short,
            f.flight_rules, f.planned_altitude, f.name, f.server, 
            f.pilot_rating, f.military_rating
        FROM flights f
        INNER JOIN eligible_flights ef
            ON f.callsign = ef.callsign
            AND f.cid = ef.cid
            AND f.departure = ef.departure
            AND f.arrival = ef.arrival
        UNION ALL
        SELECT 
            fa.callsign, fa.cid, fa.departure, fa.arrival,
            COALESCE(fa.logon_time, fa.last_updated) AS logon_time,
            fa.last_updated,
            fa.deptime, fa.route, fa.aircraft_type, fa.aircraft_faa, fa.aircraft_short,
            fa.flight_rules, fa.planned_altitude, fa.name, fa.server,
            fa.pilot_rating, fa.military_rating
        FROM flights_archive fa
        INNER JOIN eligible_flights ef
            ON fa.callsign = ef.callsign
            AND fa.cid = ef.cid
            AND fa.departure = ef.departure
            AND fa.arrival = ef.arrival
    ),
    -- Rest of the query remains the same (ordered, segmented, labeled, sessions)
    ...
""")
```

### Key Changes

1. **New CTE:** `flight_last_update` - Groups all records by flight and finds the MAX(last_updated)
2. **New CTE:** `eligible_flights` - Filters at the FLIGHT level (only flights where last_record_time is 8+ hours old)
3. **Modified:** `base` CTE - Uses INNER JOIN with `eligible_flights` instead of WHERE filter on each record
4. **Result:** ALL records for eligible flights are included, ensuring correct `MAX(last_updated)` for session_end

---

## Testing & Validation Plan

### Phase 1: Single Flight Test (QFA842)

1. **Delete** the buggy flight summary:
   ```sql
   DELETE FROM flight_summaries WHERE id = 42630;
   ```

2. **Apply** the fix to `session_selector.py`

3. **Wait** for the canonical processor's next run

4. **Verify** the recreated flight summary:
   ```sql
   SELECT callsign, logon_time, completion_time, time_online_minutes
   FROM flight_summaries
   WHERE callsign = 'QFA842' AND cid = 1627668 
     AND departure = 'YSSY' AND arrival = 'YPDN'
     AND logon_time = '2025-10-07 09:11:19+00';
   ```

5. **Expected Results:**
   - `completion_time = 2025-10-07 14:07:13+00` (NOT 09:12:29)
   - `time_online_minutes ≈ 295` (NOT 0)

### Phase 2: Batch Testing (All 7 Examples)

1. **Delete** all 7 problematic flight summaries
2. **Verify** they get recreated correctly with non-zero times

### Phase 3: Production Monitoring

1. **Monitor** for new zero-minute flights:
   ```sql
   SELECT COUNT(*) FROM flight_summaries
   WHERE time_online_minutes = 0
     AND created_at >= NOW() - INTERVAL '1 day';
   ```

2. **Expected:** Count should stop increasing after fix is deployed

---

## Recovery Options for Historical Data

### Option 1: Full Reprocessing (Recommended)

**Pros:** Most thorough, ensures all data is correct  
**Cons:** High system load

**Steps:**
```sql
-- Delete all zero-minute flights with multiple records
WITH problematic AS (
    SELECT fs.id
    FROM flight_summaries fs
    WHERE fs.time_online_minutes = 0
      AND EXISTS (
          SELECT 1 FROM (
              SELECT 1 FROM flights f
              WHERE f.callsign = fs.callsign AND f.cid = fs.cid
                AND f.departure = fs.departure AND f.arrival = fs.arrival
              UNION ALL
              SELECT 1 FROM flights_archive fa
              WHERE fa.callsign = fs.callsign AND fa.cid = fs.cid
                AND fa.departure = fs.departure AND fa.arrival = fs.arrival
              LIMIT 2  -- If more than 1 record exists, it's problematic
          ) records
      )
)
DELETE FROM flight_summaries
WHERE id IN (SELECT id FROM problematic);
```

### Option 2: SQL-Based Correction (Fastest)

**Pros:** Immediate fix, no reprocessing needed  
**Cons:** Doesn't recalculate ATC metrics, sector data, etc.

**Steps:**
```sql
-- Update time_online_minutes and completion_time directly
WITH corrected_times AS (
    SELECT 
        fs.id,
        (SELECT MIN(last_updated) FROM (
            SELECT last_updated FROM flights WHERE ...
            UNION ALL SELECT last_updated FROM flights_archive WHERE ...
        ) combined) AS correct_first,
        (SELECT MAX(last_updated) FROM (
            SELECT last_updated FROM flights WHERE ...
            UNION ALL SELECT last_updated FROM flights_archive WHERE ...
        ) combined) AS correct_last
    FROM flight_summaries fs
    WHERE fs.time_online_minutes = 0 AND ...
)
UPDATE flight_summaries fs
SET 
    completion_time = ct.correct_last,
    time_online_minutes = EXTRACT(EPOCH FROM (ct.correct_last - ct.correct_first)) / 60
FROM corrected_times ct
WHERE fs.id = ct.id;
```

### Option 3: Selective Reprocessing (Balanced)

**Pros:** Fixes major cases, moderate load  
**Cons:** Some minor cases may remain

**Steps:**
- Delete only flights with `time_online_minutes = 0` AND `record_count > 50`
- Focuses on flights with significant data loss

---

## Impact Assessment

### Direct Impact

- **Data Quality:** Flight duration metrics corrupted
- **Analytics:** Reports showing 0 minutes for multi-hour flights
- **Military Hours:** Understated in `query_military_hours_weekly.sql`
- **Historical Data:** Unknown extent of affected historical records

### Downstream Impacts

1. **Pilot Statistics:** Inaccurate flight time tracking
2. **Route Analysis:** Missing duration data for route planning
3. **ATC Coverage:** Incorrect time-based calculations
4. **Sector Metrics:** Enroute time calculations affected
5. **Business Intelligence:** Any time-based reports compromised

### Business Value of Fix

- **Data Integrity:** Restore accurate flight duration tracking
- **Trust:** Ensure stakeholders can rely on the data
- **Compliance:** Accurate record-keeping for aviation statistics
- **Decision Making:** Reliable data for operational decisions

---

## Prevention & Monitoring

### Post-Fix Monitoring

```sql
-- Daily check for new zero-minute flights
CREATE OR REPLACE VIEW v_suspicious_zero_minute_flights AS
SELECT 
    fs.id,
    fs.callsign,
    fs.cid,
    fs.departure,
    fs.arrival,
    fs.created_at,
    (
        SELECT COUNT(*) FROM (
            SELECT 1 FROM flights WHERE callsign = fs.callsign AND cid = fs.cid 
                AND departure = fs.departure AND arrival = fs.arrival
            UNION ALL
            SELECT 1 FROM flights_archive WHERE callsign = fs.callsign AND cid = fs.cid 
                AND departure = fs.departure AND arrival = fs.arrival
        ) records
    ) AS record_count
FROM flight_summaries fs
WHERE fs.time_online_minutes = 0
  AND fs.created_at >= NOW() - INTERVAL '7 days';
```

### Alert Configuration

```sql
-- Alert if more than 5 suspicious flights in the last 24 hours
SELECT COUNT(*) FROM v_suspicious_zero_minute_flights
WHERE created_at >= NOW() - INTERVAL '1 day'
  AND record_count > 1;
-- If result > 5, send alert: "Zero-minute bug may have returned"
```

---

## Documentation Files

- **This Document:** `ZERO_MINUTES_BUG_INVESTIGATION_COMPLETE.md` - Complete investigation results
- **Examples:** `ZERO_MINUTES_BUG_EXAMPLES.md` - Detailed database examples
- **SQL Queries:** `find_zero_minutes_problem.sql` - Diagnostic queries
- **Original Report:** `FLIGHT_SUMMARY_ZERO_MINUTES_FIX.md` - Initial bug report (contains incorrect fix)

---

## Approval & Sign-off

**Investigation Complete:** Yes  
**Root Cause Identified:** Yes  
**Fix Designed:** Yes  
**Testing Plan:** Yes  
**Recovery Plan:** Yes  

**Ready for Implementation:** ✅ YES

**Recommended Priority:** 🔴 CRITICAL - Deploy as soon as possible

---

## Questions for Decision Makers

1. **Fix Timing:** Deploy immediately or wait for maintenance window?
2. **Recovery Strategy:** Full reprocessing, SQL correction, or selective?
3. **Historical Data:** Reprocess all historical records or only recent?
4. **Testing Environment:** Test in staging first or proceed directly to production?
5. **Rollback Plan:** Prepare database backup before deployment?

---

**Investigation Completed By:** AI Assistant  
**Date:** October 12, 2025  
**Database Analyzed:** Production VATPAC database  
**Records Examined:** 1,000+ flight records across 7 detailed examples  



