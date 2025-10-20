# Comprehensive Test Flights for Sector Tracking Fix - 50+ Flights

**Date**: October 14, 2025  
**Environment**: Dev Database  
**Purpose**: Test the sector tracking bug fix with 50+ diverse flight examples  

---

## Test Flight Categories

### **Category 1: High Fragmentation Flights (30 flights)**
*Flights with 10-50 total entries across multiple sectors*

| Callsign | Total Entries | Sectors Visited | First Entry | Last Activity | Test Purpose |
|----------|---------------|-----------------|-------------|---------------|--------------|
| JST983 | 50 | 6 | 2025-09-25 06:36:43 | 2025-10-03 13:22:41 | High fragmentation test |
| QFA67 | 48 | 9 | 2025-09-09 22:06:41 | 2025-10-02 13:11:33 | Multi-sector fragmentation |
| UAE449 | 48 | 7 | 2025-09-26 10:18:41 | 2025-09-27 14:04:06 | Single-day high activity |
| SWR81N | 47 | 12 | 2025-09-28 12:11:43 | 2025-10-13 19:25:24 | Long-duration fragmentation |
| MAS122 | 47 | 5 | 2025-09-25 06:36:40 | 2025-10-01 10:01:05 | Multi-day fragmentation |
| QFA5 | 44 | 12 | 2025-09-08 21:32:51 | 2025-10-06 07:42:03 | High sector diversity |
| QFA64 | 43 | 11 | 2025-09-28 14:54:58 | 2025-10-12 21:51:40 | Recent activity test |
| FJI935 | 43 | 6 | 2025-09-25 23:35:13 | 2025-09-26 12:17:43 | Short-duration high activity |
| JST528 | 42 | 6 | 2025-09-08 09:07:37 | 2025-10-12 12:05:53 | Long-term fragmentation |
| EYZ | 42 | 7 | 2025-09-18 11:35:56 | 2025-10-07 10:03:26 | Multi-week fragmentation |
| UAE412 | 42 | 9 | 2025-09-26 15:23:54 | 2025-10-06 16:51:42 | UAE series test |
| SIA678 | 42 | 6 | 2025-09-26 09:02:40 | 2025-09-26 13:49:40 | Single-day intensive |
| SIA228 | 41 | 7 | 2025-09-10 12:30:12 | 2025-09-26 12:53:00 | SIA series test |
| GC0721 | 40 | 12 | 2025-09-18 11:35:56 | 2025-10-12 14:42:09 | High sector diversity |
| JST124 | 40 | 7 | 2025-09-08 08:54:06 | 2025-10-08 22:40:08 | JST series test |
| SIA221 | 40 | 8 | 2025-09-08 15:46:17 | 2025-10-08 21:04:26 | Long-term SIA test |
| ACA33 | 40 | 4 | 2025-09-23 16:05:20 | 2025-10-05 19:57:12 | ACA series test |
| CFC227 | 39 | 1 | 2025-09-22 20:20:18 | 2025-09-26 22:07:16 | Single-sector extreme |
| QFA94 | 39 | 5 | 2025-09-22 14:55:51 | 2025-10-13 16:59:58 | QFA series test |
| QFA2 | 38 | 7 | 2025-09-09 10:20:55 | 2025-10-07 08:39:07 | QFA series test |
| UAE440 | 36 | 4 | 2025-09-06 20:24:43 | 2025-10-13 21:39:41 | UAE series test |
| MAS128 | 36 | 8 | 2025-09-20 13:34:52 | 2025-10-08 08:39:13 | MAS series test |
| CPA171 | 36 | 4 | 2025-09-25 12:12:56 | 2025-10-02 12:04:28 | CPA series test |
| BOX538 | 36 | 12 | 2025-09-06 20:24:43 | 2025-10-05 22:20:03 | BOX series test |
| QFA11 | 36 | 3 | 2025-09-06 21:21:08 | 2025-10-06 09:32:50 | QFA series test |
| QFA6 | 35 | 11 | 2025-09-10 17:43:53 | 2025-10-07 19:46:16 | QFA series test |
| QFA578 | 34 | 3 | 2025-09-22 21:27:48 | 2025-10-08 09:36:52 | QFA series test |
| JST420 | 34 | 6 | 2025-09-08 09:20:10 | 2025-10-04 11:57:09 | JST series test |
| UAE424 | 34 | 3 | 2025-09-09 20:52:13 | 2025-10-03 22:40:40 | UAE series test |
| JST522 | 33 | 7 | 2025-09-08 07:51:14 | 2025-10-06 10:09:29 | JST series test |

### **Category 2: Overlapping Entry Flights (20 flights)**
*Flights with confirmed overlapping timestamp issues*

| Callsign | Test Purpose | Corruption Type |
|----------|--------------|-----------------|
| AAL7 | American Airlines test | Overlapping entries |
| AAL79 | American Airlines test | Overlapping entries |
| ACA21 | ACA series test | Overlapping entries |
| ACA325 | ACA series test | Overlapping entries |
| ACA33 | ACA series test | Overlapping entries |
| ACA601 | ACA series test | Overlapping entries |
| ACI140 | ACI series test | Overlapping entries |
| ACI150 | ACI series test | Overlapping entries |
| ACI745 | ACI series test | Overlapping entries |
| AFL4484 | AFL series test | Overlapping entries |
| AFR286 | AFR series test | Overlapping entries |
| AKU205 | AKU series test | Overlapping entries |
| AKU607 | AKU series test | Overlapping entries |
| AKU631 | AKU series test | Overlapping entries |
| AM181 | AM series test | Overlapping entries |
| ANA626 | ANA series test | Overlapping entries |
| ANO116 | ANO series test | Overlapping entries |
| ANZ124 | ANZ series test | Overlapping entries |
| ANZ145 | ANZ series test | Overlapping entries |
| ANZ246 | ANZ series test | Overlapping entries |

### **Category 3: Impossible Timestamp Flights (24 flights)**
*Flights with exit timestamps before entry timestamps*

| Callsign | Test Purpose | Corruption Type |
|----------|--------------|-----------------|
| ANA618 | ANA series test | Impossible timestamps |
| DAL41 | Delta Airlines test | Impossible timestamps |
| GC0721 | GC series test | Impossible timestamps |
| GEC8401 | GEC series test | Impossible timestamps |
| GIA714 | GIA series test | Impossible timestamps |
| GIA716 | GIA series test | Impossible timestamps |
| HAL451 | HAL series test | Impossible timestamps |
| JST612 | JST series test | Impossible timestamps |
| JST94 | JST series test | Impossible timestamps |
| N694PB | N series test | Impossible timestamps |
| NWS4388 | NWS series test | Impossible timestamps |
| PHENX84 | PHENX series test | Impossible timestamps |
| QFA33 | QFA series test | Impossible timestamps |
| QFA67 | QFA series test | Impossible timestamps |
| SAA280 | SAA series test | Impossible timestamps |
| SIA192 | SIA series test | Impossible timestamps |
| SIA227 | SIA series test | Impossible timestamps |
| SWR81N | SWR series test | Impossible timestamps |
| TEST_COMPLETE_001 | Test flight | Impossible timestamps |
| UAE3HJ | UAE series test | Impossible timestamps |
| UAE411 | UAE series test | Impossible timestamps |
| UAE412 | UAE series test | Impossible timestamps |
| UAE421 | UAE series test | Impossible timestamps |
| UAE425 | UAE series test | Impossible timestamps |

### **Category 4: Open Sector Flights (20 flights)**
*Flights with sectors that have no exit timestamp*

| Callsign | Test Purpose | Corruption Type |
|----------|--------------|-----------------|
| ANZ226 | ANZ series test | Open sectors |
| BVX532 | BVX series test | Open sectors |
| CZN1A | CZN series test | Open sectors |
| CZN642D | CZN series test | Open sectors |
| JST067 | JST series test | Open sectors |
| JST461 | JST series test | Open sectors |
| JST612 | JST series test | Open sectors |
| JST613 | JST series test | Open sectors |
| JST618 | JST series test | Open sectors |
| JST769 | JST series test | Open sectors |
| JST97 | JST series test | Open sectors |
| M6T | M series test | Open sectors |
| QFA1 | QFA series test | Open sectors |
| QFA11A | QFA series test | Open sectors |
| QFA1652 | QFA series test | Open sectors |
| QFA235 | QFA series test | Open sectors |
| QFA409 | QFA series test | Open sectors |
| QFA484 | QFA series test | Open sectors |
| QFA490 | QFA series test | Open sectors |
| QFA7474 | QFA series test | Open sectors |

### **Category 5: Extreme Fragmentation Flights (14 flights)**
*Flights with 20+ entries in single sectors*

| Callsign | Test Purpose | Corruption Type |
|----------|--------------|-----------------|
| CFC227 | Extreme single-sector fragmentation | 39 entries in IND |
| HLTK418 | Military aircraft test | 30 entries in INL |
| MAS122 | MAS series test | 47 entries across sectors |
| NYZ | NYZ series test | 20+ entries |
| PHENX1 | PHENX series test | 20+ entries |
| QFA67 | QFA series test | 48 entries across sectors |
| QFA94 | QFA series test | 39 entries across sectors |
| SAA280 | SAA series test | 28 entries in IND |
| SIA285 | SIA series test | 30 entries in ASP |
| UAE414 | UAE series test | 31 entries in IND |
| UAE415 | UAE series test | 39 entries in IND |
| UAE424 | UAE series test | 25 entries in IND |
| UAL863 | UAL series test | 20+ entries |
| VOZ083 | VOZ series test | 34 entries in ISA |

---

## Test Execution Strategy

### **Phase 1: Core Algorithm Testing (10 flights)**
**Test the new `_close_open_sector_for_flight_and_sector()` method**

1. **JST983** - Test with 50 entries across 6 sectors
2. **QFA67** - Test with 48 entries across 9 sectors  
3. **UAE449** - Test single-day high activity (48 entries)
4. **SWR81N** - Test long-duration fragmentation (47 entries)
5. **MAS122** - Test multi-day fragmentation (47 entries)
6. **QFA5** - Test high sector diversity (44 entries, 12 sectors)
7. **QFA64** - Test recent activity (43 entries)
8. **FJI935** - Test short-duration high activity (43 entries)
9. **JST528** - Test long-term fragmentation (42 entries)
10. **EYZ** - Test multi-week fragmentation (42 entries)

### **Phase 2: Overlap Resolution Testing (10 flights)**
**Test overlapping entry detection and repair**

1. **AAL7** - American Airlines overlap test
2. **ACA21** - ACA series overlap test
3. **ACI140** - ACI series overlap test
4. **AKU205** - AKU series overlap test
5. **ANA626** - ANA series overlap test
6. **ANZ124** - ANZ series overlap test
7. **VOZ083** - VOZ series overlap test (34 entries in ISA)
8. **UAE415** - UAE series overlap test (39 entries in IND)
9. **CFC227** - CFC series overlap test (39 entries in IND)
10. **SIA285** - SIA series overlap test (30 entries in ASP)

### **Phase 3: Impossible Timestamp Testing (10 flights)**
**Test impossible timestamp detection and cleanup**

1. **DAL41** - Delta Airlines impossible timestamp (-299,510 seconds!)
2. **UAE3HJ** - UAE series impossible timestamp (-7,060 seconds)
3. **N694PB** - N series impossible timestamp (-329 seconds)
4. **GIA716** - GIA series impossible timestamp (-326 seconds)
5. **HAL451** - HAL series impossible timestamp (-328 seconds)
6. **JST612** - JST series impossible timestamp
7. **QFA33** - QFA series impossible timestamp
8. **SAA280** - SAA series impossible timestamp
9. **SIA192** - SIA series impossible timestamp
10. **UAE425** - UAE series impossible timestamp

### **Phase 4: Open Sector Testing (10 flights)**
**Test open sector closure**

1. **QFA1** - QFA series open sector test
2. **QFA11A** - QFA series open sector test
3. **QFA235** - QFA series open sector test
4. **JST067** - JST series open sector test
5. **JST461** - JST series open sector test
6. **ANZ226** - ANZ series open sector test
7. **BVX532** - BVX series open sector test
8. **CZN1A** - CZN series open sector test
9. **M6T** - M series open sector test
10. **QFA7474** - QFA series open sector test

### **Phase 5: Extreme Case Testing (10 flights)**
**Test the most challenging corruption scenarios**

1. **UAE414** - 31 entries in IND sector (original case study)
2. **UAE415** - 39 entries in IND sector (worst case)
3. **CFC227** - 39 entries in IND sector (tied for worst)
4. **VOZ083** - 34 entries in ISA sector with 22 overlaps
5. **QFA94** - 39 entries across 5 sectors
6. **SIA285** - 30 entries in ASP sector
7. **HLTK418** - 30 entries in INL sector (military)
8. **SAA280** - 28 entries in IND sector
9. **UAE424** - 25 entries in IND sector
10. **PHENX1** - 20+ entries (test flight)

---

## Test Validation Queries

### **Pre-Test Baseline**
```sql
-- Get corruption metrics for all 50+ test flights
SELECT 
    'Pre-test Baseline' as phase,
    COUNT(*) as total_test_records,
    COUNT(*) FILTER (WHERE exit_timestamp IS NULL) as open_sectors,
    COUNT(*) FILTER (WHERE exit_timestamp < entry_timestamp) as impossible_timestamps,
    COUNT(*) FILTER (WHERE callsign IN (
        'JST983','QFA67','UAE449','SWR81N','MAS122','QFA5','QFA64','FJI935','JST528','EYZ',
        'AAL7','ACA21','ACI140','AKU205','ANA626','ANZ124','VOZ083','UAE415','CFC227','SIA285',
        'DAL41','UAE3HJ','N694PB','GIA716','HAL451','JST612','QFA33','SAA280','SIA192','UAE425',
        'QFA1','QFA11A','QFA235','JST067','JST461','ANZ226','BVX532','CZN1A','M6T','QFA7474',
        'UAE414','UAE424','HLTK418','QFA94','PHENX1'
    )) as test_flight_records
FROM flight_sector_occupancy;
```

### **Post-Test Validation**
```sql
-- Verify fix effectiveness for test flights
SELECT 
    'Post-test Validation' as phase,
    COUNT(*) FILTER (WHERE exit_timestamp IS NULL) as remaining_open_sectors,  -- Should be 0
    COUNT(*) FILTER (WHERE exit_timestamp < entry_timestamp) as remaining_impossible_timestamps,  -- Should be 0
    COUNT(*) FILTER (WHERE callsign IN (
        'JST983','QFA67','UAE449','SWR81N','MAS122','QFA5','QFA64','FJI935','JST528','EYZ',
        'AAL7','ACA21','ACI140','AKU205','ANA626','ANZ124','VOZ083','UAE415','CFC227','SIA285',
        'DAL41','UAE3HJ','N694PB','GIA716','HAL451','JST612','QFA33','SAA280','SIA192','UAE425',
        'QFA1','QFA11A','QFA235','JST067','JST461','ANZ226','BVX532','CZN1A','M6T','QFA7474',
        'UAE414','UAE424','HLTK418','QFA94','PHENX1'
    ) AND callsign IN (
        SELECT callsign FROM (
            SELECT callsign, sector_name, COUNT(*) as entry_count
            FROM flight_sector_occupancy 
            WHERE exit_timestamp IS NOT NULL
            GROUP BY callsign, sector_name
            HAVING COUNT(*) > 1
        ) multiple_entries
    )) as test_flights_with_multiple_entries  -- Should be <10% of test flights
FROM flight_sector_occupancy;
```

---

## Success Criteria for 50+ Test Flights

### **Immediate (After Core Fix)**
- ✅ **Zero new impossible timestamps** across all test flights
- ✅ **Zero new overlapping entries** across all test flights
- ✅ **All open sectors closed** for test flights

### **Short-term (After Data Repair)**
- ✅ **<10% of test flights** with multiple sector entries (vs current ~70%)
- ✅ **Zero impossible timestamps** in test flight historical data
- ✅ **Zero overlapping entries** in test flight historical data

### **Performance**
- ✅ **<30 seconds** to process all 50+ test flights
- ✅ **No database constraint violations**
- ✅ **Consistent results** across multiple test runs

---

## Test Data Export Commands

### **Export Test Flight Data**
```sql
-- Export all data for the 50+ test flights
COPY (
    SELECT callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds,
           EXTRACT(EPOCH FROM (exit_timestamp - entry_timestamp))::INTEGER as computed_duration
    FROM flight_sector_occupancy 
    WHERE callsign IN (
        'JST983','QFA67','UAE449','SWR81N','MAS122','QFA5','QFA64','FJI935','JST528','EYZ',
        'AAL7','ACA21','ACI140','AKU205','ANA626','ANZ124','VOZ083','UAE415','CFC227','SIA285',
        'DAL41','UAE3HJ','N694PB','GIA716','HAL451','JST612','QFA33','SAA280','SIA192','UAE425',
        'QFA1','QFA11A','QFA235','JST067','JST461','ANZ226','BVX532','CZN1A','M6T','QFA7474',
        'UAE414','UAE424','HLTK418','QFA94','PHENX1'
    )
    ORDER BY callsign, entry_timestamp
) TO '/tmp/test_flights_data.csv' WITH CSV HEADER;
```

This comprehensive test suite provides 50+ diverse flight examples covering all corruption patterns, ensuring thorough validation of the sector tracking fix across different airlines, time periods, and corruption types.



