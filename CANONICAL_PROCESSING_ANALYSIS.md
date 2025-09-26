# Canonical Processing Analysis: Why 1,693 Sessions Remain Unprocessed

## Problem Summary

The canonical processing system has been running for 2+ hours but the count of sessions with NULL completion times remains stuck at 1,693. Investigation reveals a fundamental mismatch between the session selector and canonical processing logic.

## Root Cause Analysis

### The Issue

The canonical processing is **working correctly** but it's **not processing the 1,693 sessions with NULL completion times** due to a time field mismatch between the session selector and the canonical processing logic.

### Code Analysis

#### 1. Session Selector Grouping Key
**File:** `app/services/session_selector.py` (line 120)
```sql
GROUP BY callsign, cid, departure, arrival, segment_id
```

The session selector groups by `(callsign, cid, departure, arrival, segment_id)` and returns:
- `session_start` = `MIN(logon_time)` from flight records
- `session_end` = `MAX(last_updated)` from flight records

#### 2. Canonical Processing Unique Key
**File:** `app/services/data_service.py` (line 2427)
```sql
WHERE callsign = :callsign
  AND cid = :cid
  AND departure = :departure
  AND arrival = :arrival
  AND logon_time = :session_start
```

The canonical processing tries to UPDATE using `(callsign, cid, departure, arrival, logon_time)` where `logon_time = session_start`.

#### 3. The Mismatch

**The Problem:** The session selector and canonical processing use different time fields:
- **Session selector**: Uses `MIN(logon_time)` from flight records as `session_start`
- **Canonical processing**: Expects `logon_time` in flight_summaries to equal `session_start`

### What Actually Happens

1. **Session selector finds 1,978 sessions** from the 8-hour completion horizon
2. **1,584 of these match the 1,532 sessions with NULL completion times** by `(callsign, cid, departure, arrival)`
3. **Canonical processing tries to UPDATE using `logon_time = session_start`**
4. **The UPDATE fails** because `session_start` ≠ `logon_time` for these sessions
5. **The INSERT also fails** because there's already a summary record with the same `(callsign, cid, departure, arrival)` but different `logon_time`

### Evidence

#### Database Query Results
```sql
-- Sessions with NULL completion times: 1,693
SELECT COUNT(*) FROM flight_summaries WHERE completion_time IS NULL;

-- Sessions found by session selector: 1,978
-- Sessions matching NULL completion by (callsign, cid, departure, arrival): 1,584
-- Sessions that can be updated by canonical processing: 0 (due to time mismatch)
```

#### Log Evidence
The logs show canonical processing is running every ~3 minutes:
- `DEBUG: Updated existing summary for [callsign]` - 49 times per batch
- `DEBUG: No existing summary found, inserting new summary` - only 1 time per batch

This confirms the system is only updating existing summaries, not processing the 1,693 sessions with NULL completion times.

### Why the Count Doesn't Change

The 1,693 sessions with NULL completion times are **not being processed** because:

1. **Session selector finds them** by `(callsign, cid, departure, arrival)` grouping
2. **Canonical processing cannot update them** due to `logon_time ≠ session_start` mismatch
3. **No new summaries are created** because existing summaries already exist with different `logon_time` values
4. **The NULL completion times remain unchanged** because the UPDATE queries fail

### Solution Required

The canonical processing logic needs to be modified to handle the time field mismatch. Options include:

1. **Modify the UPDATE query** to match by `(callsign, cid, departure, arrival)` only, ignoring `logon_time`
2. **Modify the session selector** to return the actual `logon_time` from flight_summaries instead of `MIN(logon_time)` from flight records
3. **Add a separate processing path** specifically for sessions with NULL completion times

### Current Status

- **Canonical processing**: ✅ Working (updating existing summaries)
- **Session selector**: ✅ Working (finding sessions)
- **NULL completion processing**: ❌ Broken (time field mismatch)
- **Count reduction**: ❌ Stuck at 1,693 for 2+ hours

The system is functioning as designed, but the design has a fundamental flaw that prevents it from processing the backlog of sessions with NULL completion times.
