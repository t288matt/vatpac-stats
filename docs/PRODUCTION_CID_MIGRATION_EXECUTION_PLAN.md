# 🚀 Production CID Migration Execution Plan

## 📋 **Overview**

This document provides **step-by-step production deployment instructions** for the CID migration that fixes the callsign collision issue in the VATSIM data collection system.

**Document Type**: Production Execution Plan  
**Migration**: Add CID column to `flight_sector_occupancy` table  
**Purpose**: Fix callsign collisions causing phantom enroute time calculations  
**Status**: ✅ **STAGING COMPLETED** - Ready for Production Deployment  

---

## 🎯 **Current Status Summary**

### **✅ Completed in Staging:**
- [x] **Database Migration**: CID column added successfully
- [x] **Data Population**: All existing records populated with CIDs
- [x] **Index Updates**: Composite index created and working
- [x] **Application Code**: All CID-related fixes implemented
- [x] **Testing**: Migration validated and working correctly

### **🔄 Ready for Production:**
- [ ] **Production Database Migration** (following this plan)
- [ ] **Production Application Deployment** (with updated code)
- [ ] **Production Validation** (confirming fix works in live environment)

---

## ⚠️ **Prerequisites & Safety Checks**

### **Before Starting:**
- [ ] **Maintenance window** scheduled (recommended: 2-4 hours)
- [ ] **Team notified** of planned maintenance
- [ ] **Monitoring alerts** temporarily disabled
- [ ] **Rollback plan** prepared and tested
- [x] **Staging environment** migration completed successfully ✅

### **Required Access:**
- [ ] **Database access** (PostgreSQL admin)
- [ ] **Application deployment** access
- [ ] **Backup storage** access
- [ ] **Monitoring tools** access

---

## 🔄 **Phase 1: Pre-Migration Preparation**

### **Step 1.1: Create Production Database Backup**

```bash
# Create timestamped backup filename (PowerShell format)
$BACKUP_FILE = "production_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"

# Create full database backup
docker-compose exec postgres pg_dump -U vatsim_user -d vatsim_data > "$BACKUP_FILE"

# Verify backup file exists and has content
Get-ChildItem "$BACKUP_FILE"
Write-Host "Backup file size: $((Get-Item "$BACKUP_FILE").Length / 1MB) MB"

# Test backup integrity (optional but recommended)
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM flight_sector_occupancy;"
```

**Expected Output**: Backup file created with timestamp, size > 0 bytes

### **Step 1.2: Capture Baseline State**

```bash
# Record current table structure
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'flight_sector_occupancy' 
ORDER BY ordinal_position;" > baseline_structure.txt

# Record current record count
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT COUNT(*) as total_records FROM flight_sector_occupancy;" > baseline_count.txt

# Record current indexes
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'flight_sector_occupancy';" > baseline_indexes.txt

# Record specific problematic data (NWK1736)
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds 
FROM flight_sector_occupancy 
WHERE callsign = 'NWK1736' 
ORDER BY entry_timestamp;" > baseline_nwk1736.txt
```

**Expected Output**: All baseline files created with current system state

### **Step 1.3: Verify Migration Script**

```bash
# Confirm migration script exists and is readable
Get-ChildItem scripts/migrate_add_cid_to_sector_occupancy.sql

# Verify script content (should contain all migration steps)
Get-Content scripts/migrate_add_cid_to_sector_occupancy.sql | Select-Object -First 20
Get-Content scripts/migrate_add_cid_to_sector_occupancy.sql | Select-Object -Last 20
```

**Expected Output**: Migration script exists and contains SQL commands

---

## 🚀 **Phase 2: Production Migration Execution**

### **Step 2.1: Stop Application Services**

```bash
# Stop the application to prevent new data during migration
docker-compose down

# Verify all containers are stopped
docker-compose ps

# Optional: Stop only the app container if you want to keep database running
# docker-compose stop app
```

**Expected Output**: All containers stopped, no running services

### **Step 2.2: Execute Database Migration**

**IMPORTANT**: The migration script path is relative to the container, not the host. Execute each step individually:

```bash
# Step 1: Add CID column
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "ALTER TABLE flight_sector_occupancy ADD COLUMN IF NOT EXISTS cid INTEGER NOT NULL DEFAULT 0;"

# Step 2: Populate CIDs from flights table
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "UPDATE flight_sector_occupancy fso SET cid = f.cid FROM flights f WHERE fso.callsign = f.callsign AND fso.entry_timestamp BETWEEN f.logon_time AND COALESCE(f.last_updated, f.logon_time + INTERVAL '24 hours') AND fso.cid = 0;"

# Step 3: Populate remaining CIDs from flight_summaries
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "UPDATE flight_sector_occupancy fso SET cid = fs.cid FROM flight_summaries fs WHERE fso.callsign = fs.callsign AND fso.cid = 0 AND fs.cid IS NOT NULL;"

# Step 4: Handle orphaned records (controller callsigns)
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "UPDATE flight_sector_occupancy SET cid = 999999 WHERE cid = 0;"

# Step 5: Remove default value
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "ALTER TABLE flight_sector_occupancy ALTER COLUMN cid DROP DEFAULT;"

# Step 6: Add constraint
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "ALTER TABLE flight_sector_occupancy ADD CONSTRAINT valid_cid CHECK (cid > 0);"

# Step 7: Drop old index
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "DROP INDEX IF EXISTS idx_flight_sector_occupancy_callsign;"

# Step 8: Create new composite index
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_callsign_cid ON flight_sector_occupancy(callsign, cid);"
```

**Expected Output**: Each command should complete without errors

### **Step 2.3: Validate Migration Results**

```bash
# Check 1: Verify all records have valid CIDs
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT COUNT(*) as total_records, 
       COUNT(CASE WHEN cid > 0 THEN 1 END) as records_with_cid, 
       COUNT(CASE WHEN cid = 0 THEN 1 END) as records_without_cid 
FROM flight_sector_occupancy;"

# Check 2: Verify new table structure
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'flight_sector_occupancy' 
ORDER BY ordinal_position;" 

# Check 3: Verify new indexes
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'flight_sector_occupancy';"

# Check 4: Verify specific callsign collision fix
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT callsign, cid, sector_name, entry_timestamp, exit_timestamp 
FROM flight_sector_occupancy 
WHERE callsign = 'NWK1736' 
ORDER BY entry_timestamp;"
```

**Expected Output**: 
- All records have valid CIDs (total_records = records_with_cid)
- New `cid` column present in table structure
- New composite index `idx_flight_sector_occupancy_callsign_cid` exists
- NWK1736 records show different CIDs for different flights

---

## 🔧 **Phase 3: Application Code Deployment**

### **Step 3.1: Update Application Code**

```bash
# Pull latest code with CID fixes
git pull origin main

# Verify the changes are present
git log --oneline -5
git diff HEAD~1 app/services/data_service.py
```

**Expected Output**: Latest commits pulled, CID-related changes visible

### **Step 3.2: Build and Deploy Application**

```bash
# Rebuild application with new code
docker-compose build

# Start application services
docker-compose up -d

# Verify services are running
docker-compose ps
docker-compose logs app --tail=20
```

**Expected Output**: Application rebuilt and running, no startup errors

---

## ✅ **Phase 4: Post-Migration Validation**

### **Step 4.1: Verify Database Migration**

```bash
# Final validation: All records have CIDs
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT COUNT(*) as total_records, 
       COUNT(CASE WHEN cid > 0 THEN 1 END) as records_with_cid 
FROM flight_sector_occupancy;"

# Verify no orphaned records (should be minimal)
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT COUNT(*) as orphaned_records 
FROM flight_sector_occupancy fso 
WHERE NOT EXISTS (SELECT 1 FROM flight_summaries fs WHERE fso.cid = fs.cid) 
AND NOT EXISTS (SELECT 1 FROM flights f WHERE fso.cid = f.cid);"
```

**Expected Output**: 
- `total_records = records_with_cid` (100% success)
- `orphaned_records` should be 0 or minimal (controller callsigns only)

### **Step 4.2: Test Composite Index Performance**

```bash
# Test that new composite index is being used
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
EXPLAIN (ANALYZE, BUFFERS) 
SELECT sector_name, SUM(duration_seconds) / 60 as minutes 
FROM flight_sector_occupancy 
WHERE callsign = 'TEST123' AND cid = 1001 
GROUP BY sector_name;"
```

**Expected Output**: Query plan shows `Index Scan using idx_flight_sector_occupancy_callsign_cid`

### **Step 4.3: Verify Callsign Collision Fix**

```bash
# Test the specific issue that was fixed
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT callsign, cid, COUNT(*) as sector_count, 
       MIN(entry_timestamp) as first_entry, 
       MAX(exit_timestamp) as last_exit 
FROM flight_sector_occupancy 
WHERE callsign = 'NWK1736' 
GROUP BY callsign, cid 
ORDER BY first_entry;"
```

**Expected Output**: Multiple rows with different CIDs, proving callsign collisions are resolved

---

## 🚨 **Phase 5: Rollback Procedure (If Needed)**

### **Step 5.1: Stop Application**

```bash
# Stop all services
docker-compose down
```

### **Step 5.2: Restore Database**

```bash
# Restore from backup (replace YYYYMMDD_HHMMSS with actual backup timestamp)
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -f production_backup_YYYYMMDD_HHMMSS.sql
```

### **Step 5.3: Revert Application Code**

```bash
# Revert to previous commit
git checkout HEAD~1

# Rebuild and restart
docker-compose build
docker-compose up -d
```

### **Step 5.4: Verify Rollback**

```bash
# Check table structure is back to original
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'flight_sector_occupancy' 
ORDER BY ordinal_position;"

# Check original indexes are restored
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'flight_sector_occupancy';"
```

---

## 📊 **Phase 6: Post-Deployment Monitoring**

### **Step 6.1: Enable Monitoring**

```bash
# Re-enable monitoring alerts
# (Depends on your monitoring system)

# Start application logging monitoring
docker-compose logs -f app
```

### **Step 6.2: Monitor Key Metrics**

**Database Performance:**
- Monitor query performance for sector tracking
- Watch for any constraint violations
- Check index usage statistics

**Application Performance:**
- Monitor sector tracking response times
- Watch for any errors in flight processing
- Check memory and CPU usage

**Data Integrity:**
- Monitor for any new callsign collision reports
- Verify flight summary accuracy
- Check sector data consistency

### **Step 6.3: Validation Queries (Run Daily for First Week)**

```bash
# Daily validation: Check CID data integrity
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT COUNT(*) as total_records, 
       COUNT(CASE WHEN cid > 0 THEN 1 END) as records_with_cid 
FROM flight_sector_occupancy;"

# Daily validation: Check for any new orphaned records
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "
SELECT COUNT(*) as orphaned_records 
FROM flight_sector_occupancy fso 
WHERE NOT EXISTS (SELECT 1 FROM flight_summaries fs WHERE fso.cid = fs.cid) 
AND NOT EXISTS (SELECT 1 FROM flights f WHERE fso.cid = f.cid);"
```

---

## 🎯 **Success Criteria**

### **Migration Success:**
- [ ] **100% of records** have valid CIDs
- [ ] **New composite index** is created and working
- [ ] **Table structure** includes CID column
- [ ] **No data loss** during migration

### **Application Success:**
- [ ] **Application starts** without errors
- [ ] **Sector tracking** uses composite keys
- [ ] **No callsign collisions** in new flights
- [ ] **Performance maintained** or improved

### **Business Success:**
- [ ] **NWK1736 issue resolved** (no more phantom 109 minutes)
- [ ] **Flight summaries accurate** (enroute times match actual flight times)
- [ ] **Data integrity restored** (sector data correctly linked to flights)

---

## 📞 **Emergency Contacts**

### **During Migration:**
- **Primary**: Development Team Lead
- **Secondary**: Database Administrator
- **Backup**: System Administrator

### **Post-Migration:**
- **Support**: Operations Team
- **Monitoring**: DevOps Team
- **Business**: Product Owner

---

## 📝 **Migration Checklist**

### **Pre-Migration:**
- [ ] Maintenance window scheduled
- [ ] Team notified
- [ ] Backup completed and verified
- [ ] Baseline state captured
- [ ] Migration script verified
- [ ] Rollback plan prepared

### **Migration Execution:**
- [ ] Application stopped
- [ ] Database migration executed
- [ ] Migration results validated
- [ ] Application code updated
- [ ] Application deployed
- [ ] Services verified running

### **Post-Migration:**
- [ ] Final validation completed
- [ ] Monitoring re-enabled
- [ ] Team notified of completion
- [ ] Post-deployment monitoring started
- [ ] Success criteria verified

---

## 🔍 **Key Differences from Staging**

### **Migration Script Execution:**
- **Staging**: Used individual `psql -c` commands due to path issues
- **Production**: Use the same individual commands for reliability
- **Note**: Migration script exists but individual commands are more reliable

### **PowerShell Compatibility:**
- **Staging**: Used bash-style commands
- **Production**: Updated to use PowerShell-compatible syntax
- **Note**: All commands now work with Windows PowerShell

### **Validation Approach:**
- **Staging**: Step-by-step validation after each command
- **Production**: Same approach for maximum reliability
- **Note**: Individual validation ensures each step succeeds

---

**Document Version**: 2.0  
**Created**: January 2025  
**Last Updated**: After staging migration completion  
**Next Review**: After successful production deployment  
**Maintained By**: Development Team  
**Staging Status**: ✅ **COMPLETED SUCCESSFULLY**  
**Production Status**: 🚀 **READY FOR DEPLOYMENT**
