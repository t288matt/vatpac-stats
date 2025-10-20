# QFA842 Fix Validation - Proposed Code Test

**Flight:** QFA842 (YSSY → YPDN)  
**Date:** October 7, 2025  
**Test:** Running proposed fix against actual historical data  

---

## Historical Context

### What Actually Happened (BUGGY CODE)

**Timeline:**
- **09:12:29** - First record captured
- **14:07:13** - Last record captured (actual flight end)
- **17:12:29** - First record becomes 8 hours old (dangerous window opens)
- **17:12:43** - Canonical processor runs (14 seconds into dangerous window)
- **Result:** Processed with 1 record, created broken flight summary

**Buggy Query Result at 17:12:43:**
```
Records Found: 1
Session Start: 09:11:19 (logon_time)
Session End:   09:12:29 (first record only!)
Time Calculation:
  - Query: BETWEEN 09:11:19 AND 09:12:29
  - Found: 1 record
  - MIN = 09:12:29, MAX = 09:12:29
  - time_online_minutes = 0
```

---

## Proposed Fix Test Results

### Test 1: At Bug Time (17:12:43) - During Dangerous Window

**Query:** Check if flight is eligible when dangerous window just opened

```sql
WITH flight_completion_times AS (
    SELECT 
        callsign, cid, departure, arrival,
        MAX(last_updated) AS latest_record_time
    FROM (
        SELECT callsign, cid, departure, arrival, last_updated FROM flights
        UNION ALL
        SELECT callsign, cid, departure, arrival, last_updated FROM flights_archive
    ) all_records
    WHERE callsign = 'QFA842' AND cid = 1627668 
      AND departure = 'YSSY' AND arrival = 'YPDN'
    GROUP BY callsign, cid, departure, arrival
),
eligible_flights AS (
    SELECT callsign, cid, departure, arrival
    FROM flight_completion_times
    WHERE '2025-10-07 17:12:43' >= latest_record_time + INTERVAL '8 hours'
)
SELECT COUNT(*) FROM eligible_flights;
```

**Result:**
```
Flights Eligible: 0
Latest Record: 14:07:13
Becomes Eligible At: 22:07:13 (8 hours after latest)
Check Time: 17:12:43
Decision: CORRECTLY SKIPPED ✅
```

**Why Skipped:**
- Latest record: 14:07:13
- Becomes eligible: 14:07:13 + 8h = 22:07:13
- Current time: 17:12:43
- **17:12:43 < 22:07:13 → NOT ELIGIBLE**

---

### Test 2: After Dangerous Window (22:08:00) - Should Process

**Query:** Check if flight is eligible after all records are 8+ hours old

```sql
WITH flight_completion_times AS (
    SELECT 
        callsign, cid, departure, arrival,
        MAX(last_updated) AS latest_record_time
    FROM (
        SELECT callsign, cid, departure, arrival, last_updated FROM flights
        UNION ALL
        SELECT callsign, cid, departure, arrival, last_updated FROM flights_archive
    ) all_records
    WHERE callsign = 'QFA842' AND cid = 1627668 
      AND departure = 'YSSY' AND arrival = 'YPDN'
    GROUP BY callsign, cid, departure, arrival
),
eligible_flights AS (
    SELECT callsign, cid, departure, arrival
    FROM flight_completion_times
    WHERE '2025-10-07 22:08:00' >= latest_record_time + INTERVAL '8 hours'
),
base AS (
    SELECT f.last_updated
    FROM flights f
    INNER JOIN eligible_flights ef USING (callsign, cid, departure, arrival)
    WHERE f.callsign = 'QFA842' AND f.cid = 1627668 
      AND f.departure = 'YSSY' AND f.arrival = 'YPDN'
    UNION ALL
    SELECT fa.last_updated
    FROM flights_archive fa
    INNER JOIN eligible_flights ef USING (callsign, cid, departure, arrival)
    WHERE fa.callsign = 'QFA842' AND fa.cid = 1627668 
      AND fa.departure = 'YSSY' AND fa.arrival = 'YPDN'
)
SELECT 
    COUNT(*) AS records_found,
    MIN(last_updated) AS first_record,
    MAX(last_updated) AS session_end,
    EXTRACT(EPOCH FROM (MAX(last_updated) - MIN(last_updated)))/60 AS time_online_minutes
FROM base;
```

**Result:**
```
Records Found: 292
First Record: 09:12:29
Session End: 14:07:13
Time Online Minutes: 294.73
Decision: CORRECTLY PROCESSED ✅
```

**Why Processed:**
- Latest record: 14:07:13
- Becomes eligible: 14:07:13 + 8h = 22:07:13
- Current time: 22:08:00
- **22:08:00 > 22:07:13 → ELIGIBLE**
- ALL 292 records included in base CTE

---

## Side-by-Side Comparison

| Time | Event | Buggy Code | Fixed Code |
|------|-------|------------|------------|
| **09:12:29** | First record captured | ✅ Stored | ✅ Stored |
| **14:07:13** | Last record captured | ✅ Stored | ✅ Stored |
| **17:12:29** | First record → 8h old | ⚠️ Becomes eligible | ✅ Check latest: 14:07:13 not 8h old yet |
| **17:12:43** | Scheduler runs | ❌ PROCESSES (1 record) | ✅ SKIPS (not eligible) |
| **17:12:43** | Session end calculated | ❌ 09:12:29 (wrong!) | N/A (skipped) |
| **17:12:43** | Time calculated | ❌ 0 minutes | N/A (skipped) |
| **17:12:43** | Flight summary created | ❌ YES (broken) | ✅ NO (correctly skipped) |
| **22:07:13** | Last record → 8h old | Too late (already processed) | ✅ Now eligible! |
| **22:12:42** | Next scheduler run | Skipped (already exists) | ✅ PROCESSES (ALL 292 records) |
| **22:12:42** | Session end calculated | N/A (skipped) | ✅ 14:07:13 (correct!) |
| **22:12:42** | Time calculated | N/A (skipped) | ✅ 295 minutes |
| **22:12:42** | Flight summary created | N/A (skipped) | ✅ YES (correct) |

---

## Key Differences

### Buggy Code Behavior

1. **Filters records individually:** `WHERE NOW() >= last_updated + 8 hours`
2. **At 17:12:43:** Only 1 record passes filter (09:12:29)
3. **Calculates:** `MAX(last_updated)` from 1 record = 09:12:29
4. **Result:** Processes immediately with incomplete data

### Fixed Code Behavior

1. **Filters flights as a whole:** Checks if `MAX(last_updated)` for entire flight is 8+ hours old
2. **At 17:12:43:** Checks 14:07:13 + 8h = 22:07:13 > 17:12:43 → NOT ELIGIBLE
3. **Skips:** Flight not processed
4. **At 22:12:42:** Checks 14:07:13 + 8h = 22:07:13 < 22:12:42 → ELIGIBLE
5. **Processes:** Gets ALL 292 records via INNER JOIN
6. **Calculates:** `MAX(last_updated)` from 292 records = 14:07:13
7. **Result:** Processes only when ALL records are available

---

## Mathematical Proof

### Buggy Code Logic
```
For each record r in flights:
  IF NOW() >= r.last_updated + 8h THEN include r
  
Result: session_end = MAX(included_records.last_updated)
```

**Problem:** If only first record is 8h old, `MAX = first_record_time`

### Fixed Code Logic
```
latest = MAX(all_records.last_updated) for flight
IF NOW() >= latest + 8h THEN
  include ALL records for this flight
  
Result: session_end = MAX(all_records.last_updated)
```

**Guarantee:** When flight is eligible, ALL records are included, so `MAX = actual_last_record`

---

## Dangerous Window Elimination

### Buggy Code
```
Dangerous Window:
  Start: first_record + 8h (some records eligible)
  End: last_record + 8h (all records eligible)
  Duration: (last_record - first_record) = flight duration
  
  For QFA842: 4h 54m dangerous window
  Probability of bug: ~100% (scheduler runs every 15 min)
```

### Fixed Code
```
No Dangerous Window:
  Before: last_record + 8h (flight not eligible)
  After: last_record + 8h (flight eligible, ALL records included)
  
  No partial eligibility state exists!
  Bug probability: 0%
```

---

## Validation Queries Run

### Query 1: Buggy Code Simulation
```sql
SELECT COUNT(*), MAX(last_updated)
FROM flights
WHERE callsign = 'QFA842' AND cid = 1627668 
  AND departure = 'YSSY' AND arrival = 'YPDN'
  AND '2025-10-07 17:12:43' >= last_updated + INTERVAL '8 hours';
```
**Result:** 1 record, MAX = 09:12:29

### Query 2: Fixed Code Simulation (Dangerous Window)
```sql
WITH max_time AS (
  SELECT MAX(last_updated) AS latest
  FROM flights
  WHERE callsign = 'QFA842' AND cid = 1627668 
    AND departure = 'YSSY' AND arrival = 'YPDN'
)
SELECT 
  latest,
  latest + INTERVAL '8 hours' AS becomes_eligible,
  '2025-10-07 17:12:43'::timestamptz >= latest + INTERVAL '8 hours' AS is_eligible
FROM max_time;
```
**Result:** latest = 14:07:13, becomes_eligible = 22:07:13, is_eligible = FALSE

### Query 3: Fixed Code Simulation (After Window)
```sql
WITH max_time AS (
  SELECT MAX(last_updated) AS latest
  FROM flights
  WHERE callsign = 'QFA842' AND cid = 1627668 
    AND departure = 'YSSY' AND arrival = 'YPDN'
)
SELECT 
  latest,
  latest + INTERVAL '8 hours' AS becomes_eligible,
  '2025-10-07 22:08:00'::timestamptz >= latest + INTERVAL '8 hours' AS is_eligible
FROM max_time;
```
**Result:** latest = 14:07:13, becomes_eligible = 22:07:13, is_eligible = TRUE

### Query 4: Record Count When Eligible
```sql
SELECT COUNT(*)
FROM flights
WHERE callsign = 'QFA842' AND cid = 1627668 
  AND departure = 'YSSY' AND arrival = 'YPDN';
```
**Result:** 292 records (all would be included)

---

## Conclusion

✅ **The proposed fix COMPLETELY prevents the bug for QFA842**

**Evidence:**
1. At bug time (17:12:43): Fixed code correctly identifies flight as NOT eligible
2. After safe time (22:08:00): Fixed code correctly identifies flight as eligible
3. When eligible: ALL 292 records are included, not just 1
4. Result: `session_end = 14:07:13`, `time_online_minutes = 295` ✅

**The dangerous window is eliminated entirely** - there is no state where the flight is "partially eligible".

---

**Test Date:** October 12, 2025  
**Test Status:** ✅ PASSED  
**Recommendation:** DEPLOY FIX IMMEDIATELY



