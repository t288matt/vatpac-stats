# Free Windows Database Query Tools for VATSIM Data

## 🎯 **Top Recommendations**

### 1. **DB Browser for SQLite** (Most Popular)
**Download**: https://sqlitebrowser.org/
**Price**: Free and Open Source
**Best for**: SQLite databases (your current setup)

**Features**:
- ✅ Visual database browser
- ✅ SQL query editor with syntax highlighting
- ✅ Table structure viewer
- ✅ Data import/export
- ✅ Database design tools
- ✅ Query history
- ✅ Export to CSV/JSON

**Setup**:
1. Download and install DB Browser for SQLite
2. Open your `atc_optimization.db` file
3. Use the "Execute SQL" tab for queries
4. Browse tables in the "Browse Data" tab

### 2. **DBeaver Community** (Universal)
**Download**: https://dbeaver.io/download/
**Price**: Free
**Best for**: Multiple database types (SQLite, PostgreSQL, MySQL, etc.)

**Features**:
- ✅ Supports 80+ database types
- ✅ Advanced SQL editor
- ✅ ER diagrams
- ✅ Data export/import
- ✅ Query builder
- ✅ Database migration tools
- ✅ Team collaboration features

**Setup**:
1. Install DBeaver Community
2. Create new connection → SQLite
3. Select your `atc_optimization.db` file
4. Start querying!

### 3. **HeidiSQL** (Lightweight)
**Download**: https://www.heidisql.com/
**Price**: Free
**Best for**: Simple, fast database browsing

**Features**:
- ✅ Lightweight and fast
- ✅ Simple interface
- ✅ SQL editor
- ✅ Data export
- ✅ Table structure viewer

## 📊 **VATSIM Database Schema**

Your database contains these main tables:

### **atc_positions**
- `id` - Primary key
- `callsign` - ATC position callsign
- `facility` - ATC facility
- `position` - ATC position type
- `status` - online/offline
- `last_seen` - Last activity timestamp
- `workload_score` - Workload rating

### **flights**
- `id` - Primary key
- `callsign` - Flight number
- `aircraft_type` - Aircraft type
- `departure` - Origin airport
- `arrival` - Destination airport
- `altitude` - Flight altitude
- `speed` - Air speed
- `last_updated` - Last update timestamp

### **traffic_movements**
- `id` - Primary key
- `airport_code` - Airport ICAO code
- `movement_type` - arrival/departure
- `aircraft_callsign` - Flight callsign
- `timestamp` - Movement time

## 🔍 **Useful Queries to Try**

### **Active ATC Positions**
```sql
SELECT callsign, facility, position, status, last_seen, workload_score
FROM atc_positions 
WHERE status = 'online' 
ORDER BY last_seen DESC 
LIMIT 20;
```

### **Recent Flights**
```sql
SELECT callsign, aircraft_type, departure, arrival, altitude, speed, last_updated
FROM flights 
WHERE status = 'active' 
ORDER BY last_updated DESC 
LIMIT 20;
```

### **ATC Position Workload Analysis**
```sql
SELECT 
    c.callsign,
    c.facility,
    c.workload_score,
    COUNT(f.id) as flight_count
FROM atc_positions c
LEFT JOIN flights f ON c.id = f.atc_position_id
WHERE c.status = 'online'
GROUP BY c.id
ORDER BY c.workload_score DESC
LIMIT 15;
```

### **Aircraft Type Distribution**
```sql
SELECT 
    aircraft_type,
    COUNT(*) as count
FROM flights 
WHERE aircraft_type IS NOT NULL
GROUP BY aircraft_type 
ORDER BY count DESC 
LIMIT 10;
```

### **Facility Statistics**
```sql
SELECT 
    facility,
    COUNT(*) as atc_position_count,
    AVG(workload_score) as avg_workload
FROM atc_positions 
WHERE status = 'online'
GROUP BY facility 
ORDER BY atc_position_count DESC;
```

### **Recent Activity (Last Hour)**
```sql
SELECT 
    'atc_positions' as table_name,
    COUNT(*) as count,
    MAX(last_seen) as latest_update
FROM atc_positions 
WHERE last_seen > datetime('now', '-1 hour')
UNION ALL
SELECT 
    'flights' as table_name,
    COUNT(*) as count,
    MAX(last_updated) as latest_update
FROM flights 
WHERE last_updated > datetime('now', '-1 hour');
```

## 🚀 **Quick Start Guide**

### **Using DB Browser for SQLite**:

1. **Download and Install**
   - Go to https://sqlitebrowser.org/
   - Download the Windows installer
   - Install with default settings

2. **Open Your Database**
   - Launch DB Browser for SQLite
   - Click "Open Database"
   - Navigate to your `atc_optimization.db` file
   - Click "Open"

3. **Browse Data**
   - Click the "Browse Data" tab
   - Select a table from the dropdown
   - View and edit data directly

4. **Run Queries**
   - Click the "Execute SQL" tab
   - Type your SQL query
   - Click the "Execute" button (or press F5)
   - View results in the table below

5. **Export Results**
   - Right-click on query results
   - Select "Export to CSV" or "Export to JSON"
   - Choose save location

### **Using DBeaver Community**:

1. **Download and Install**
   - Go to https://dbeaver.io/download/
   - Download DBeaver Community
   - Install with default settings

2. **Create Connection**
   - Launch DBeaver
   - Click "New Database Connection"
   - Select "SQLite"
   - Browse to your `atc_optimization.db` file
   - Click "Finish"

3. **Query Database**
   - Right-click on your connection
   - Select "SQL Editor" → "New SQL Script"
   - Type your query
   - Press Ctrl+Enter to execute

## 📈 **Advanced Features**

### **Data Visualization**
- **DBeaver**: Built-in charting capabilities
- **DB Browser**: Export to Excel for charts
- **HeidiSQL**: Export to CSV for external tools

### **Query Optimization**
- All tools show query execution time
- DBeaver provides query analysis
- DB Browser shows query plan

### **Data Export Options**
- CSV files for Excel
- JSON for web applications
- SQL scripts for backups
- Excel files for analysis

## 🔧 **Troubleshooting**

### **Common Issues**:

1. **Database Locked**
   - Close any other applications using the database
   - Restart the query tool
   - Check if the VATSIM application is running

2. **Permission Denied**
   - Run the tool as Administrator
   - Check file permissions
   - Ensure the database file is not read-only

3. **Query Performance**
   - Use LIMIT clauses for large tables
   - Add WHERE clauses to filter data
   - Use indexes on frequently queried columns

### **Performance Tips**:
- Use indexes on `last_seen`, `last_updated`, `status` columns
- Limit result sets with `LIMIT` clauses
- Use `WHERE` clauses to filter data
- Export large datasets to CSV for analysis

## 🎯 **Recommended Workflow**

1. **Start with DB Browser for SQLite** (easiest)
2. **Move to DBeaver** for advanced features
3. **Use the provided queries** as starting points
4. **Export results** to CSV for further analysis
5. **Create custom queries** for specific needs

## 📞 **Support**

- **DB Browser**: https://github.com/sqlitebrowser/sqlitebrowser
- **DBeaver**: https://dbeaver.io/support/
- **HeidiSQL**: https://www.heidisql.com/forum.php

---

**Happy Querying!** 🚁✈️ 