# Data Movement Reprocessing Plan

**Date**: September 26, 2025  
**Purpose**: One-off data movement strategy to reprocess archived flights with updated completion logic  
**Status**: Planning Phase  

---

## **Overview**

This document outlines a strategy to move archived flight data back to the active `flights` table for reprocessing with the updated completion time logic. The approach involves temporarily moving data from `flights_archive` to `flights`, resetting completion processing flags, and letting the system automatically reprocess and re-archive the data.

---

## **Phase 1: Test with Single Flight**

### **Step 1: Identify a test flight in archive**

```sql
-- Find a flight in flights_archive that needs reprocessing
SELECT callsign, departure, arrival, cid, deptime, last_updated, completion_time
FROM flights_archive 
WHERE completion_time IS NOT NULL  -- Has been processed before
ORDER BY last_updated DESC 
LIMIT 5;
```

### **Step 2: Check for conflicts in flights table**

```sql
-- Verify it's NOT in flights table (to avoid conflicts)
SELECT callsign, departure, arrival, cid, deptime
FROM flights 
WHERE callsign = 'TEST_CALLSIGN' 
AND departure = 'TEST_DEP' 
AND arrival = 'TEST_ARR';
```

### **Step 3: Move flight data from archive to flights table**

```sql
-- Map only the fields that both tables share and are needed for completion processing
INSERT INTO flights (
    callsign, departure, arrival, cid, deptime, last_updated,
    aircraft_type, route, flight_rules, aircraft_faa, planned_altitude,
    aircraft_short, name, server, pilot_rating, military_rating,
    latitude, longitude, altitude, groundspeed, heading, logon_time,
    created_at, updated_at
)
SELECT 
    callsign, departure, arrival, cid, deptime, last_updated,
    aircraft_type, route, flight_rules, aircraft_faa, planned_altitude,
    aircraft_short, name, server, pilot_rating, military_rating,
    latitude, longitude, altitude, groundspeed, heading, logon_time,
    created_at, updated_at
FROM flights_archive 
WHERE callsign = 'TEST_CALLSIGN' 
AND departure = 'TEST_DEP' 
AND arrival = 'TEST_ARR'
AND cid = TEST_CID
AND deptime = 'TEST_DEPTIME';
```

### **Step 4: Reset flight summary for reprocessing**

```sql
-- Reset completion_time and enrichment_status to trigger reprocessing
UPDATE flight_summaries 
SET 
    completion_time = NULL,
    enrichment_status = 'pending',
    updated_at = NOW()
WHERE callsign = 'TEST_CALLSIGN' 
AND departure = 'TEST_DEP' 
AND arrival = 'TEST_ARR'
AND cid = TEST_CID
AND deptime = 'TEST_DEPTIME';
```

### **Step 5: Monitor processing**

- Watch application logs for completion processing
- Verify the flight gets picked up by scheduled processing
- Check that completion_time gets calculated correctly with new logic
- Verify enrichment runs and completes

### **Step 6: Verify results**

```sql
-- Check that completion_time was recalculated
SELECT callsign, completion_time, enrichment_status, updated_at
FROM flight_summaries 
WHERE callsign = 'TEST_CALLSIGN' 
AND departure = 'TEST_DEP' 
AND arrival = 'TEST_ARR';
```

### **Step 7: Cleanup test data**

```sql
-- Remove test flight from flights table after processing
DELETE FROM flights 
WHERE callsign = 'TEST_CALLSIGN' 
AND departure = 'TEST_DEP' 
AND arrival = 'TEST_ARR'
AND cid = TEST_CID
AND deptime = 'TEST_DEPTIME';
```

---

## **Phase 2: Full 3-Month Move (After Test Success)**

### **Step 1: Identify 3 months of data**

```sql
-- Find flights from last 3 months in archive
SELECT COUNT(*) as total_flights
FROM flights_archive 
WHERE last_updated >= NOW() - INTERVAL '3 months'
AND completion_time IS NOT NULL;  -- Only processed flights
```

### **Step 2: Batch move in chunks (1000 flights at a time)**

```sql
-- Move in batches to avoid locking issues
INSERT INTO flights (callsign, departure, arrival, cid, deptime, last_updated, ...)
SELECT callsign, departure, arrival, cid, deptime, last_updated, ...
FROM flights_archive 
WHERE last_updated >= NOW() - INTERVAL '3 months'
AND completion_time IS NOT NULL
LIMIT 1000;
```

### **Step 3: Reset flight summaries for reprocessing**

```sql
-- Reset all 3-month flight summaries for reprocessing
UPDATE flight_summaries 
SET 
    completion_time = NULL,
    enrichment_status = 'pending',
    updated_at = NOW()
WHERE callsign IN (
    SELECT DISTINCT callsign 
    FROM flights_archive 
    WHERE last_updated >= NOW() - INTERVAL '3 months'
    AND completion_time IS NOT NULL
);
```

### **Step 4: Let processing run**

- Monitor completion processing logs
- Let system automatically re-archive processed flights
- Verify completion times are calculated correctly with new logic
- Monitor enrichment completion

### **Step 5: Verify final results**

```sql
-- Check processing status
SELECT 
    COUNT(CASE WHEN completion_time IS NULL THEN 1 END) as pending_processing,
    COUNT(CASE WHEN completion_time IS NOT NULL THEN 1 END) as processed,
    COUNT(CASE WHEN enrichment_status = 'completed' THEN 1 END) as enriched,
    COUNT(CASE WHEN enrichment_status = 'pending' THEN 1 END) as pending_enrichment
FROM flight_summaries
WHERE updated_at >= NOW() - INTERVAL '24 hours';
```

---

## **Safety Considerations**

- ✅ **Test first** with single flight
- ✅ **Backup database** before full move
- ✅ **Monitor conflicts** - ensure no duplicate callsigns
- ✅ **Batch processing** - avoid locking entire tables
- ✅ **Rollback plan** - can delete moved data if issues arise
- ✅ **Monitor system load** - ensure processing can handle volume

---

## **Expected Outcomes**

- ✅ **Completion times recalculated** with new, fixed logic
- ✅ **No data truncation** due to completion horizon fix
- ✅ **Long-haul flights processed** due to duration limit removal
- ✅ **Enrichment rerun** with updated algorithms
- ✅ **Automatic re-archiving** of processed flights

---

## **Monitoring Commands**

### **Check processing status**
```bash
docker-compose logs --tail=50 app | findstr /i "flight summary processing\|summaries created"
```

### **Check database status**
```sql
SELECT 
    'Records with NULL completion_time' as status,
    COUNT(*) as count
FROM flight_summaries 
WHERE completion_time IS NULL
UNION ALL
SELECT 
    'Records with completion_time' as status,
    COUNT(*) as count
FROM flight_summaries 
WHERE completion_time IS NOT NULL;
```

---

## **Rollback Procedures**

If issues arise during processing:

1. **Stop processing**: The system will naturally stop processing when no more NULL completion_time records exist
2. **Clean up moved data**: Delete moved records from flights table
3. **Restore original state**: Reset flight_summaries completion_time to original values if needed

---

**Document Version**: 1.0  
**Last Updated**: September 26, 2025  
**Next Review**: After Phase 1 completion

