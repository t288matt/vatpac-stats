# Flight Archive Policy Violation Analysis

**Document Version:** 1.0  
**Date:** September 20, 2025  
**Severity:** HIGH  
**Status:** ACTIVE ISSUE  

## Executive Summary

A critical policy violation has been identified in the VATSIM data processing system where the configured 60-day archive delay policy is being completely bypassed. Analysis of 100,186 archived flight records reveals that **100% of flights are being archived prematurely**, with 84.1% archived within 1 day instead of the required 60-day delay.

**Key Impact:**
- Complete non-compliance with data retention policy
- 100,186 flights archived in violation of configured policy
- Business rules and potential compliance requirements not being met
- Data lifecycle management compromised

## Problem Statement

### Configuration vs. Reality

**Expected Behavior:**
- Flights should be archived only after 60 days from their last activity
- Configuration: `FLIGHT_DAYS_BEFORE_ARCHIVE: "60"` in docker-compose.yml

**Actual Behavior:**
- Flights are being archived immediately after 8-hour completion threshold
- No 60-day delay is being applied
- Archive policy is completely ignored

### Data Analysis Results

**Total Records Analyzed:** 100,186 flights in `flights_archive` table

**Archive Delay Distribution:**
```
Delay Category    | Flight Count | Percentage | Policy Compliance
------------------|--------------|------------|------------------
< 1 day          | 84,242       | 84.1%      | ❌ VIOLATION
1-7 days         | 12,657       | 12.6%      | ❌ VIOLATION  
1-4 weeks        | 3,287        | 3.3%       | ❌ VIOLATION
30-60 days       | 0            | 0.0%       | ❌ VIOLATION
60+ days         | 0            | 0.0%       | ✅ COMPLIANT
```

**Critical Statistics:**
- **0 flights** respected the 60-day policy
- **96.7% archived within 1 week** of last activity
- **Average archive delay: 0.8 days** (should be 60+ days)

### Specific Examples

**Most Recent Violations (September 20, 2025):**
```sql
callsign | last_updated           | created_at             | days_delay
---------|------------------------|------------------------|------------
QFA7427  | 2025-09-20 13:19:54+00 | 2025-09-20 21:22:12+00 | 0.33 days
BOX538   | 2025-09-20 13:20:53+00 | 2025-09-20 21:22:12+00 | 0.33 days
```

**Historical Pattern (September 8, 2025):**
```sql
callsign | last_updated           | created_at             | days_delay
---------|------------------------|------------------------|------------
ABD666   | 2025-09-06 20:25:43+00 | 2025-09-08 06:56:53+00 | 1.44 days
```

## Root Cause Analysis

### System Architecture Discovery

The investigation revealed that the system has **two distinct processing pipelines** for flight archival:

#### 1. Legacy Pipeline (INACTIVE)
```python
# File: app/services/data_service.py, Lines 1523-1550
async def process_completed_flights(self):
    # OLD CODE PATH - NOT BEING USED
    completed_flights = await self._identify_completed_flights(completion_hours)
    records_archived = await self._archive_completed_flights(completed_flights)  # ✅ HAS 60-day policy
    records_deleted = await self._delete_completed_flights(completed_flights)    # ✅ HAS 60-day policy
```

#### 2. Canonical Pipeline (ACTIVE)
```python
# File: app/services/data_service.py, Lines 1509-1511
async def process_completed_flights(self):
    # ACTIVE CODE PATH - CURRENTLY IN USE
    self.logger.info("🧭 Canonical session pipeline (default) - using selector")
    result = await self._process_completed_flights_canonical()  # ❌ NO 60-day policy
```

### The Critical Flaw

**The active canonical pipeline completely bypasses the 60-day archive delay policy.**

### Code Analysis: Legacy Methods (CORRECT Implementation)

#### `_archive_completed_flights()` Method
**Location:** Lines 2083-2098  
**Status:** ✅ CORRECTLY IMPLEMENTS 60-DAY DELAY

```python
# Respect archive delay configuration to avoid archiving very recent flights
import os
from datetime import datetime, timezone, timedelta
days_str = os.getenv("FLIGHT_DAYS_BEFORE_ARCHIVE", "0")
try:
    days_before = int(days_str)  # Gets 60 from docker-compose.yml
except Exception:
    days_before = 0
archive_cutoff = datetime.now(timezone.utc) - timedelta(days=days_before) if days_before > 0 else None

# Archive each record
for record in records:
    # If archive_cutoff is set, only archive records older than cutoff
    if archive_cutoff and record.last_updated and record.last_updated > archive_cutoff:
        # Skip archiving this recent record
        continue
```

#### `_delete_completed_flights()` Method  
**Location:** Lines 2604-2630  
**Status:** ✅ CORRECTLY IMPLEMENTS 60-DAY DELAY

```python
# Respect archive delay configuration: only delete rows older than cutoff
import os
from datetime import datetime, timezone, timedelta
days_str = os.getenv("FLIGHT_DAYS_BEFORE_ARCHIVE", "0")
try:
    days_before = int(days_str)
except Exception:
    days_before = 0

if days_before > 0:
    archive_cutoff = datetime.now(timezone.utc) - timedelta(days=days_before)
    result = await session.execute(text("""
        DELETE FROM flights
        WHERE callsign = :callsign
        AND departure = :departure
        AND arrival = :arrival
        AND cid = :cid
        AND deptime = :deptime
        AND last_updated <= :archive_cutoff  -- ✅ ENFORCES 60-DAY DELAY
    """), {...})
```

### Code Analysis: Canonical Method (FLAWED Implementation)

#### `_process_completed_flights_canonical()` Method
**Location:** Lines 2517-2580  
**Status:** ❌ COMPLETELY IGNORES 60-DAY POLICY

```python
# Archive rows ≤ HWM within window
arch_sql = text("""
    INSERT INTO flights_archive (...)
    SELECT ... FROM flights f
    WHERE f.callsign = :callsign
      AND f.cid = :cid
      AND f.departure = :departure
      AND f.arrival = :arrival
      AND f.last_updated BETWEEN :start AND :hwm  -- ❌ NO ARCHIVE DELAY CHECK
""")
```

**Critical Issues:**
1. **No `FLIGHT_DAYS_BEFORE_ARCHIVE` check** - Configuration completely ignored
2. **Immediate archival** - Archives flights as soon as they pass 8-hour completion threshold
3. **NULL completion_time** - Sets completion_time as NULL (line 2540)
4. **Policy bypass** - No date-based filtering for archive delay

### Configuration Analysis

#### Docker Compose Configuration
**File:** `docker-compose.yml`, Line 73
```yaml
FLIGHT_DAYS_BEFORE_ARCHIVE: "60"  # Days before flight data is archived in the archive tables
```

#### Application Configuration
**File:** `app/config.py`, Lines 142-151
```python
@dataclass
class FlightSummaryConfig:
    completion_hours: int = 14
    # ... other fields ...
    
    @classmethod
    def from_env(cls):
        return cls(
            completion_hours=int(os.getenv("FLIGHT_COMPLETION_HOURS", "14")),
            # NOTE: FLIGHT_DAYS_BEFORE_ARCHIVE is NOT loaded into config class
        )
```

**Issue:** The `FLIGHT_DAYS_BEFORE_ARCHIVE` environment variable is not integrated into the configuration system, requiring manual `os.getenv()` calls.

## Technical Impact Analysis

### Database Impact

**Archive Table Analysis:**
```sql
-- Total records in flights_archive
SELECT COUNT(*) FROM flights_archive;
-- Result: 100,186

-- Records with NULL completion_time (indicating canonical processing)
SELECT COUNT(*) FROM flights_archive WHERE completion_time IS NULL;
-- Result: 100,186 (100%)

-- Archive date range
SELECT MIN(created_at), MAX(created_at) FROM flights_archive;
-- Result: 2025-09-08 06:56:53+00 to 2025-09-20 21:22:12+00
```

### Processing Flow Analysis

**Current Active Flow:**
1. **Session Selection** - `select_canonical_sessions()` identifies completed flights (8 hours old)
2. **Summary Creation** - Creates/updates `flight_summaries` records
3. **Immediate Archival** - Archives flights to `flights_archive` with NO delay check
4. **Immediate Deletion** - Removes flights from main `flights` table

**Expected Flow:**
1. **Session Selection** - Identify completed flights (8 hours old)
2. **Summary Creation** - Create/update summaries
3. **Delayed Archival** - Archive only flights older than 60 days
4. **Delayed Deletion** - Delete only flights older than 60 days

### Data Integrity Issues

1. **Inconsistent Timestamps:**
   - All `completion_time` fields are NULL in archive
   - Cannot determine actual flight completion time
   - Archive timing based on `created_at` vs `last_updated` delta

2. **Missing Enrichment Data:**
   - Canonical method sets enrichment fields as NULL
   - Lost sector breakdown and controller interaction data

3. **Premature Data Loss:**
   - Flight details deleted from main table too early
   - Unable to reprocess or analyze recent flights

## Business Impact

### Policy Compliance
- **Data Retention Policy:** Completely violated
- **Business Rules:** Archive timing requirements not met
- **Audit Trail:** Premature data archival may affect compliance audits

### Operational Impact
- **Data Analysis:** Recent flight data prematurely archived
- **Debugging:** Limited ability to investigate recent flight issues
- **Performance:** Unnecessary archive table bloat with recent data

### Risk Assessment
- **High:** Complete policy non-compliance
- **Medium:** Data lifecycle management compromised  
- **Low:** Current system functionality not impacted (flights still processed)

## Evidence Documentation

### Database Queries Used

```sql
-- Archive delay analysis
SELECT 
    CASE 
        WHEN EXTRACT(EPOCH FROM (created_at - last_updated)) / 86400 < 1 THEN '< 1 day'
        WHEN EXTRACT(EPOCH FROM (created_at - last_updated)) / 86400 < 7 THEN '1-7 days'
        WHEN EXTRACT(EPOCH FROM (created_at - last_updated)) / 86400 < 30 THEN '1-4 weeks'
        WHEN EXTRACT(EPOCH FROM (created_at - last_updated)) / 86400 < 60 THEN '30-60 days'
        ELSE '60+ days'
    END as delay_category,
    COUNT(*) as flight_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM flights_archive WHERE last_updated IS NOT NULL AND created_at IS NOT NULL), 1) as percentage
FROM flights_archive 
WHERE last_updated IS NOT NULL 
AND created_at IS NOT NULL
GROUP BY 1
ORDER BY MIN(EXTRACT(EPOCH FROM (created_at - last_updated)) / 86400);

-- Recent violations
SELECT 
    callsign,
    last_updated,
    created_at,
    ROUND(EXTRACT(EPOCH FROM (created_at - last_updated)) / 86400, 2) as days_delay
FROM flights_archive 
WHERE last_updated IS NOT NULL 
AND created_at IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

### Code References

**Primary Issue Locations:**
- `app/services/data_service.py:1509-1511` - Wrong pipeline selection
- `app/services/data_service.py:2517-2580` - Missing archive delay check
- `app/services/data_service.py:2540` - NULL completion_time assignment

**Correct Implementation References:**
- `app/services/data_service.py:2083-2098` - Proper archive delay implementation
- `app/services/data_service.py:2604-2630` - Proper delete delay implementation

## Recommendations

### Immediate Actions Required

1. **Fix Canonical Processing**
   - Add `FLIGHT_DAYS_BEFORE_ARCHIVE` check to canonical archive method
   - Update archive SQL to include date filter
   - Set proper completion_time values

2. **Code Changes Needed**
   ```python
   # Add before line 2517 in _process_completed_flights_canonical()
   import os
   from datetime import datetime, timezone, timedelta
   
   days_str = os.getenv("FLIGHT_DAYS_BEFORE_ARCHIVE", "0")
   try:
       days_before = int(days_str)
   except Exception:
       days_before = 0
   
   if days_before > 0:
       archive_cutoff = datetime.now(timezone.utc) - timedelta(days=days_before)
       # Add archive_cutoff to WHERE clause in arch_sql
   ```

3. **Testing Required**
   - Verify archive delay is properly enforced
   - Test with various `FLIGHT_DAYS_BEFORE_ARCHIVE` values
   - Confirm completion_time is properly set

### Long-term Improvements

1. **Configuration Integration**
   - Add `FLIGHT_DAYS_BEFORE_ARCHIVE` to `FlightSummaryConfig` class
   - Centralize archive policy configuration

2. **Code Consolidation**
   - Remove duplicate archive delay logic
   - Create shared archive policy helper function

3. **Monitoring**
   - Add alerts for archive policy violations
   - Monitor archive timing compliance

4. **Documentation**
   - Update architecture documentation
   - Document archive policy implementation

## Conclusion

This analysis reveals a critical system flaw where the active flight processing pipeline completely bypasses the configured 60-day archive delay policy. The issue stems from implementing a new "canonical" processing system without carrying forward the archive delay logic from the legacy system.

**Immediate action is required** to fix the canonical processing method and ensure compliance with the configured data retention policy. Until fixed, the system will continue to violate its own archive policy and potentially compromise data lifecycle management requirements.

The fix is straightforward but critical - the canonical processing method must be updated to respect the `FLIGHT_DAYS_BEFORE_ARCHIVE` configuration before archiving flight records.

---

**Document Prepared By:** AI Assistant  
**Analysis Date:** September 20, 2025  
**Next Review:** After fix implementation  
**Distribution:** Development Team, System Administrators, Data Management Team
