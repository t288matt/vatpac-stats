# Test Data for Sector Tracking Fix - Dev Environment

**Date**: October 14, 2025  
**Environment**: Dev Database  
**Purpose**: Specific data examples to test the sector tracking bug fix  

---

## Test Data Summary

### **Current Corruption State:**
- **Total Records**: 19,115
- **Open Sectors**: 36 (need to be closed)
- **Impossible Timestamps**: 26 (exit before entry)
- **Overlapping Entries**: 1,560 pairs
- **Flights with Multiple Entries**: 1,929 flights (69.21%)

---

## Test Cases for Core Fix

### **Test Case 1: Same-Sector Re-entry (Core Bug)**
**Flight**: `VOZ083` in `ISA` sector
**Problem**: 34 entries with overlapping timestamps
**Data Pattern**:
```
Entry 1: 09:19:42 → 09:26:14 (392 seconds)
Entry 2: 09:27:27 → 09:47:08 (1181 seconds) 
Entry 3: 09:46:43 → 09:49:11 (148 seconds) ← OVERLAPS with Entry 2
Entry 4: 09:48:58 → 09:50:32 (94 seconds) ← OVERLAPS with Entry 2
```

**Test Scenario**: 
1. Create a test flight that enters ISA sector
2. Simulate brief exit and re-entry to same sector
3. Verify fix prevents overlapping entries
4. Compare with actual VOZ083 data

### **Test Case 2: Impossible Timestamps**
**Problem**: 26 records where exit happens before entry
**Examples**:
```
DAL41 TSN: Entry 2025-10-12 09:51:58, Exit 2025-10-08 22:40:08 (-299,510 seconds!)
UAE3HJ IND: Entry 2025-10-01 15:25:10, Exit 2025-10-01 13:27:30 (-7,060 seconds)
N694PB ASP: Entry 2025-09-30 16:16:13, Exit 2025-09-30 16:10:44 (-329 seconds)
```

**Test Scenario**:
1. Verify these records are identified correctly
2. Test deletion of impossible records
3. Ensure no new impossible records are created

### **Test Case 3: Open Sectors**
**Problem**: 36 sectors without exit timestamps
**Examples**:
```
QFA490 WOL: Entry 2025-10-14 10:20:55 (open for ~1.7 minutes)
TRI1130 SYA: Entry 2025-10-14 10:19:13 (open for ~3.4 minutes)
UAL1535 SYA: Entry 2025-10-14 10:19:10 (open for ~3.4 minutes)
```

**Test Scenario**:
1. Test closing open sectors using last known flight position
2. Verify duration calculations are correct
3. Ensure all open sectors get closed

---

## Test Cases for Data Repair

### **Test Case 4: Overlapping Entries Repair**
**Flight**: `VOZ083` in `ISA` sector (22 overlapping pairs)
**Current State**: Multiple overlapping entries
**Target State**: Single continuous entry or clean separate entries

**Repair Test**:
```sql
-- Before repair: Check overlaps
SELECT COUNT(*) FROM (
    SELECT fso1.id 
    FROM flight_sector_occupancy fso1
    JOIN flight_sector_occupancy fso2 
        ON fso1.callsign = fso2.callsign 
        AND fso1.sector_name = fso2.sector_name
        AND fso1.id < fso2.id
    WHERE fso1.callsign = 'VOZ083' AND fso1.sector_name = 'ISA'
        AND fso1.entry_timestamp < fso2.exit_timestamp 
        AND fso1.exit_timestamp > fso2.entry_timestamp
) overlaps;
-- Should return 22

-- After repair: Should return 0
```

### **Test Case 5: Multiple Entry Fragmentation**
**Flight**: `UAE425` in `IND` sector (15 entries)
**Current State**: Highly fragmented with impossible timestamps
**Target State**: Clean, logical sequence of entries

**Fragmentation Analysis**:
```sql
-- Analyze UAE425 fragmentation
SELECT 
    callsign,
    sector_name,
    COUNT(*) as entry_count,
    MIN(entry_timestamp) as first_entry,
    MAX(exit_timestamp) as last_exit,
    SUM(duration_seconds) as total_duration,
    EXTRACT(EPOCH FROM (MAX(exit_timestamp) - MIN(entry_timestamp))) as continuous_duration
FROM flight_sector_occupancy
WHERE callsign = 'UAE425' AND sector_name = 'IND'
GROUP BY callsign, sector_name;
```

---

## Test Execution Plan

### **Phase 1: Unit Testing with Dev Data**

#### **Test 1.1: Close Open Sectors**
```sql
-- Test data: 10 open sectors from recent entries
-- Expected: All 10 should be closed with correct durations
-- Validation: Zero open sectors remain
```

#### **Test 1.2: Fix Impossible Timestamps**
```sql
-- Test data: 26 impossible timestamp records
-- Expected: All 26 should be deleted
-- Validation: Zero impossible timestamps remain
```

#### **Test 1.3: Prevent Overlapping Entries**
```sql
-- Test scenario: Simulate VOZ083 pattern
-- Expected: No overlapping entries created
-- Validation: Clean entry-exit sequence
```

### **Phase 2: Integration Testing**

#### **Test 2.1: VOZ083 ISA Sector Repair**
```sql
-- Current: 34 entries with 22 overlaps
-- Target: Clean, non-overlapping entries
-- Method: Merge overlapping entries into continuous periods
```

#### **Test 2.2: UAE425 IND Sector Repair**
```sql
-- Current: 15 entries with impossible timestamps
-- Target: Logical sequence without impossible durations
-- Method: Fix timestamps and merge where appropriate
```

### **Phase 3: Performance Testing**

#### **Test 3.1: Bulk Operations**
```sql
-- Test: Process 100 sector entries rapidly
-- Expected: <10 seconds completion time
-- Validation: No performance degradation
```

#### **Test 3.2: Database Constraints**
```sql
-- Test: Verify all database constraints still work
-- Expected: No constraint violations
-- Validation: Data integrity maintained
```

---

## Validation Queries

### **Pre-Test Validation**
```sql
-- Get baseline corruption metrics
SELECT 
    'Pre-test State' as phase,
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE exit_timestamp IS NULL) as open_records,
    COUNT(*) FILTER (WHERE exit_timestamp < entry_timestamp) as impossible_timestamps,
    COUNT(*) FILTER (WHERE callsign IN (
        SELECT callsign FROM (
            SELECT callsign, sector_name, COUNT(*) as entry_count
            FROM flight_sector_occupancy 
            WHERE exit_timestamp IS NOT NULL
            GROUP BY callsign, sector_name
            HAVING COUNT(*) > 1
        ) multiple_entries
    )) as flights_with_multiple_entries
FROM flight_sector_occupancy;
```

### **Post-Test Validation**
```sql
-- Verify fix effectiveness
SELECT 
    'Post-test State' as phase,
    COUNT(*) FILTER (WHERE exit_timestamp IS NULL) as open_records,  -- Should be 0
    COUNT(*) FILTER (WHERE exit_timestamp < entry_timestamp) as impossible_timestamps,  -- Should be 0
    COUNT(*) FILTER (WHERE callsign IN (
        SELECT callsign FROM (
            SELECT callsign, sector_name, COUNT(*) as entry_count
            FROM flight_sector_occupancy 
            WHERE exit_timestamp IS NOT NULL
            GROUP BY callsign, sector_name
            HAVING COUNT(*) > 1
        ) multiple_entries
    )) as flights_with_multiple_entries  -- Should be <5% of total
FROM flight_sector_occupancy;
```

---

## Specific Test Data Files

### **Test Data 1: VOZ083 ISA Sector (Overlapping Entries)**
```csv
id,entry_timestamp,exit_timestamp,duration_seconds
62566,2025-09-26 09:19:42+00,2025-09-26 09:26:14+00,392
62583,2025-09-26 09:27:27+00,2025-09-26 09:47:08+00,1181
62657,2025-09-26 09:46:43+00,2025-09-26 09:49:11+00,148
62704,2025-09-26 09:48:58+00,2025-09-26 09:50:32+00,94
62750,2025-09-26 09:50:28+00,2025-09-26 09:51:52+00,84
```

### **Test Data 2: Impossible Timestamps**
```csv
callsign,sector_name,entry_timestamp,exit_timestamp,computed_duration
DAL41,TSN,2025-10-12 09:51:58+00,2025-10-08 22:40:08+00,-299510
UAE3HJ,IND,2025-10-01 15:25:10+00,2025-10-01 13:27:30+00,-7060
N694PB,ASP,2025-09-30 16:16:13+00,2025-09-30 16:10:44+00,-329
```

### **Test Data 3: Open Sectors**
```csv
callsign,sector_name,entry_timestamp,hours_open
QFA490,WOL,2025-10-14 10:20:55+00,0.027
TRI1130,SYA,2025-10-14 10:19:13+00,0.056
UAL1535,SYA,2025-10-14 10:19:10+00,0.057
```

---

## Success Criteria

### **Immediate (After Fix Deployment)**
- ✅ **Zero new impossible timestamps** (exit before entry)
- ✅ **Zero new overlapping entries** 
- ✅ **All open sectors closed** within 5 minutes

### **Short-term (After Data Repair)**
- ✅ **<5% of flights with multiple entries** (down from 69%)
- ✅ **Zero impossible timestamps** in historical data
- ✅ **Zero overlapping entries** in historical data

### **Performance**
- ✅ **<10 seconds** for 100 sector operations
- ✅ **No database constraint violations**
- ✅ **Efficient index usage**

---

## Rollback Test Data

If testing fails, we can restore specific test cases:
```sql
-- Restore VOZ083 ISA data (if corrupted during testing)
-- Restore UAE425 IND data
-- Restore open sector test cases
```

This comprehensive test data set provides real-world examples of all the corruption patterns we need to fix, allowing us to validate the solution thoroughly before production deployment.



