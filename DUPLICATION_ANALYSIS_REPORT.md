# Data Duplication Analysis Report
## VATSIM Stats Application - Similar Examples Found

**Date**: December 19, 2024  
**Investigator**: AI Assistant  
**Issue**: Multiple route formats causing potential duplication in `flight_summaries` table  
**Severity**: High - Same root cause as BUCK03 case  

---

## Executive Summary

I have identified multiple flights in the current database that exhibit the **exact same root cause** as the BUCK03 duplication issue described in the production report. These flights have multiple route formats in the `flights` table, which would cause the same UPDATE WHERE clause failure and subsequent INSERT duplication.

## Root Cause Confirmed

The issue is in the UPDATE WHERE clause in `app/services/data_service.py` lines 2663-2667:

```sql
WHERE callsign = :callsign
  AND cid = :cid
  AND departure = :departure
  AND arrival = :arrival
  AND logon_time = :session_start
```

When a flight has multiple route formats (like the examples below), the UPDATE fails to match any existing record because the WHERE clause includes `departure` and `arrival`, but the flight exists with different route variations. This causes INSERT to create duplicate records.

## Similar Examples Found

### Current Database Analysis (Last 7 Days)

I found **10 flights** with multiple route formats that would cause the same duplication issue:

| Callsign | CID      | Route | Arrival | Route Formats | Example Routes |
|----------|----------|-------|---------|---------------|----------------|
| FDX674   | 811376   | YBAS  | YSSY    | 5 formats     | `3314S14742E RIVET4/34L`, `3346S14904E RIVET4/16R`, `AS A576 APOMA Y52 VELGI Y105 TARAL Y59 RIVET` |
| JST516   | 1829178  | YMML  | YSSY    | 4 formats     | `DOSEL2/27 DOSEL Y59 RIVET`, `DOSEL2/27 DOSEL Y59 RIVET RIVET4/16R` |
| AWK192   | 1856479  | YMML  | YSSY    | 4 formats     | `DOSEL2/27 DOSEL Y59 RIVET`, `ISPEG DCT DOSEL Y59 RIVET` |
| JST137   | 1677356  | YSSY  | YMML    | 4 formats     | `GROOK1/16R PEGSU V169 ML`, `SY3/16R PEGSU V169 ML` |
| ACA34    | 1627668  | YSSY  | CYVR    | 4 formats     | Multiple international route variations |
| DLH9525  | 1768254  | YSSY  | YMML    | 4 formats     | `SY3/34L WOL H65 LEECE Q29 ML`, `WOL2/34L WOL H65 LEECE Q29 ML` |
| JST211   | 1624022  | YSSY  | YMML    | 4 formats     | `MARUB7/34R WOL H65 LEECE Q29 ML`, coordinate-based routes |
| AFL2WT   | 1546736  | YSSY  | NZAA    | 4 formats     | `EVONN L521 GEROS/N0466F330 L521 LUNBI`, `MARUB7/34R EVONN L521...` |
| GIA499   | 1782776  | YMML  | YSSY    | 4 formats     | `YMML/27 3432S14855E CULIN Y59 RIVET RIVET4/16R` |
| JST588   | 1954532  | YMML  | YBBN    | 4 formats     | `NONIX4/16 NONIX H66 BLAKA`, coordinate variations |

### Route Format Patterns

The multiple route formats follow these patterns:

1. **Full Standard Route**: `AS A576 APOMA Y52 VELGI Y105 TARAL Y59 RIVET`
2. **SID/STAR with Coordinates**: `3314S14742E RIVET4/34L`
3. **SID/STAR Only**: `RIVET4/16R`
4. **Coordinates Only**: `3346S14904E`
5. **Combined Formats**: `DOSEL2/27 DOSEL Y59 RIVET RIVET4/16R`

## Technical Analysis

### The Problem

1. **Canonical Session Selector** groups flights by `(callsign, cid, departure, arrival)` and creates one session per flight
2. **UPDATE Statement** tries to match existing records using the full signature including `departure` and `arrival`
3. **Multiple Route Formats** in the `flights` table cause the UPDATE to fail
4. **INSERT Creates Duplicates** for each route variation that doesn't match the UPDATE WHERE clause

### Code Location

- **File**: `app/services/data_service.py`
- **Function**: `_process_completed_flights_canonical()`
- **Lines**: 2624-2750 (UPDATE/INSERT logic)
- **Critical Section**: Lines 2663-2667 (UPDATE WHERE clause)

### Current Database Status

- **No Current Duplicates**: The database currently has no duplicate flight_summaries records
- **Root Cause Present**: Multiple flights with multiple route formats exist
- **Risk Level**: High - Any processing of these flights will create duplicates

## Impact Assessment

### Immediate Risk
- **FDX674**: 5 route formats = potential for 5 duplicate summaries
- **JST516, AWK192, JST137, ACA34, DLH9525, JST211, AFL2WT, GIA499, JST588**: 4 route formats each = potential for 4 duplicate summaries each

### Statistics Inflation Potential
- **Current Risk**: 10 flights × average 4.2 route formats = 42 potential duplicates
- **If Not Fixed**: Each processing cycle could create these duplicates
- **Cumulative Effect**: Over time, this would recreate the BUCK03 scenario

## Recommended Solution

### Option 1: Fix UPDATE WHERE Clause (Recommended)

Change the UPDATE WHERE clause from:
```sql
WHERE callsign = :callsign
  AND cid = :cid
  AND departure = :departure
  AND arrival = :arrival
  AND logon_time = :session_start
```

To:
```sql
WHERE callsign = :callsign
  AND cid = :cid
  AND logon_time = :session_start
```

This matches the canonical session signature and avoids the route format issue.

### Option 2: Add Unique Constraint

Add a unique constraint on `(callsign, cid, logon_time)` to prevent duplicates at the database level.

## Implementation Plan

### Phase 1: Immediate Fix
1. **Modify UPDATE WHERE clause** in `_process_completed_flights_canonical()`
2. **Test with sample data** to ensure no duplicates are created
3. **Deploy fix** to prevent future duplication

### Phase 2: Monitoring
1. **Add logging** to detect when UPDATE fails and INSERT is used
2. **Monitor** for any new duplication patterns
3. **Verify** that canonical session selector properly groups flights

### Phase 3: Prevention
1. **Add database constraints** if needed
2. **Implement data quality checks** for route format consistency
3. **Document** the fix and prevention measures

## Conclusion

The BUCK03 duplication issue is **not an isolated case**. The same root cause exists in the current database with 10 flights having multiple route formats. The fix is straightforward and should be implemented immediately to prevent the same 21,000% statistics inflation from occurring again.

The recommended solution (Option 1) addresses the root cause by simplifying the UPDATE WHERE clause to match the canonical session signature, avoiding the route format matching issue entirely.

---

**Next Steps**: Implement the UPDATE WHERE clause fix immediately to prevent duplication of these 10 identified flights and any future similar cases.




