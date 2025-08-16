# Database Monitoring Tools

This directory contains tools to monitor data flow into the VATSIM database in real-time. Use these tools to verify if the system is working and data is being collected properly.

## 🛠️ Available Tools

### 1. **Python Live Monitor** (Recommended)
**File**: `monitor_database_live.py`

**Features**:
- Real-time database monitoring with automatic updates
- Shows table counts, data flow statistics, and sector tracking
- Displays recent records and system status
- Configurable update intervals
- Cross-platform compatibility

**Usage**:
```bash
# Basic monitoring (30-second updates)
python scripts/monitor_database_live.py

# Focus on specific table with detailed view
python scripts/monitor_database_live.py --table flights

# Faster updates (10-second intervals)
python scripts/monitor_database_live.py --interval 10

# Custom database connection
python scripts/monitor_database_live.py --database-url "postgresql://user:pass@host:port/db"
```

**What You'll See**:
- 📊 Table record counts with changes
- 🌊 Data flow statistics (last hour/10min/1min)
- 🚁 Sector tracking statistics
- 📈 System status summary
- 📝 Recent record samples

### 2. **PowerShell Monitor**
**File**: `check_database.ps1`

**Features**:
- PowerShell-based monitoring
- SQL query execution via psql
- Real-time updates
- Windows-focused

**Usage**:
```powershell
# Start monitoring
.\scripts\check_database.ps1

# Quick single check
.\scripts\check_database.ps1 --quick

# Custom parameters
.\scripts\check_database.ps1 -Interval 15 -DatabaseHost "192.168.1.100"
```

### 3. **Windows Batch File**
**File**: `check_database.bat`

**Features**:
- Simple double-click execution
- Automatic PowerShell detection
- Fallback to Python script if needed

**Usage**:
- Double-click the `.bat` file
- Or run from command prompt: `scripts\check_database.bat`

### 4. **SQL Queries**
**File**: `quick_db_check.sql`

**Features**:
- Raw SQL queries for manual execution
- Comprehensive database status checks
- Can be run in any PostgreSQL client

**Usage**:
```bash
# Run with psql
psql -h localhost -U vatsim_user -d vatsim_data -f scripts/quick_db_check.sql

# Or copy/paste individual queries into your database client
```

## 🔍 What to Look For

### ✅ **System Working Properly**:
- **Flight counts increasing** every 30-60 seconds
- **Recent timestamps** showing current time
- **Sector entries** being created and closed
- **Data flow statistics** showing recent activity

### ❌ **System Not Working**:
- **Static record counts** (no changes)
- **Old timestamps** (data not updating)
- **Empty tables** or no recent activity
- **Connection errors** or timeouts

## 📊 Key Metrics to Monitor

### **Flight Data**:
- Total flight records should be growing
- `last_updated_api` should be recent (within last few minutes)
- New flights appearing every 30-60 seconds

### **Sector Tracking**:
- `flight_sector_occupancy` table should have records
- Mix of open (no exit) and closed sectors
- Recent entry timestamps

### **Data Flow**:
- Records in last hour: Should be > 0
- Records in last 10 minutes: Should be > 0
- Records in last minute: May vary

## 🚀 Quick Start

### **Option 1: Python (Recommended)**
```bash
cd "VATSIM data"
python scripts/monitor_database_live.py
```

### **Option 2: Windows Batch**
```bash
cd "VATSIM data"
scripts\check_database.bat
```

### **Option 3: PowerShell**
```powershell
cd "VATSIM data"
.\scripts\check_database.ps1
```

### **Option 4: Manual SQL**
```bash
cd "VATSIM data"
psql -h localhost -U vatsim_user -d vatsim_data -f scripts/quick_db_check.sql
```

## 🔧 Troubleshooting

### **Connection Issues**:
- Check if Docker containers are running
- Verify database credentials in `docker-compose.yml`
- Ensure PostgreSQL port 5432 is accessible

### **No Data Flow**:
- Check if VATSIM API is accessible
- Verify application logs for errors
- Check if geographic filtering is working

### **Permission Issues**:
- Ensure database user has SELECT permissions
- Check if tables exist and are accessible

## 📈 Interpreting Results

### **Healthy System**:
```
✅ Database has data
✅ Flight data is being added
✅ Sector tracking is active
```

### **System Issues**:
```
⚠️  Flight data count unchanged
⚠️  No recent sector activity
❌ Database appears empty
```

## 🎯 Monitoring Tips

1. **Start with Python script** - Most comprehensive and reliable
2. **Watch for changes** - Record counts should increase over time
3. **Check timestamps** - Should be recent (within minutes)
4. **Monitor sector tracking** - Shows if cleanup process is working
5. **Use shorter intervals** during testing (10-15 seconds)

## 🔄 Continuous Monitoring

For production use, consider:
- Running the Python script as a service
- Setting up alerts for data flow issues
- Logging monitoring results for trend analysis
- Integrating with existing monitoring systems

---

**Need Help?** Check the main project README or run the monitoring tools to see what's happening in real-time!
