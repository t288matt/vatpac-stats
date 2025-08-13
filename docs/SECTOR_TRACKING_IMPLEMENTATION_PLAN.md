# Sector Tracking Implementation Plan

## Overview

This document outlines the implementation plan for **real-time sector occupancy tracking** in the VATSIM data collection system. The system will divide Australian airspace into defined sectors and track which sectors flights are flying through in real-time, enabling rich sector-based reporting and analytics.

## 🎯 **What Sector Tracking Provides**

Instead of just knowing "flight ABC123 is at lat/lon", you'll know:
- **"Flight ABC123 is currently in the SYDNEY sector"**
- **"SYDNEY sector has 15 flights right now"**
- **"Most flights transition from SYDNEY → MELBOURNE sectors"**
- **"BRISBANE sector has no ATC coverage currently"**

This enables **much richer reporting capabilities** for understanding airspace usage, ATC coverage, and flight patterns across different regions of Australia.

## 📊 **System Architecture**

### **Data Flow**
```
VATSIM API → Flight Position Updates → Sector Boundary Detection → Sector Occupancy Tracking → Real-time Reports
```

### **Component Architecture**
```
app/
├── utils/
│   ├── geographic_utils.py (existing - enhanced)
│   └── sector_loader.py (new - XML parsing)
├── services/
│   └── data_service.py (modified - sector integration)
└── database/
    └── flight_sector_occupancy (new table)
```

## 🗃️ **Database Schema**

### **Flight Sector Occupancy Table** (`flight_sector_occupancy`)
```sql
CREATE TABLE flight_sector_occupancy (
    id BIGSERIAL PRIMARY KEY,
    flight_id VARCHAR(50) NOT NULL,
    sector_name VARCHAR(10) NOT NULL,
    entry_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_seconds INTEGER NOT NULL,
    entry_lat DECIMAL(10, 8) NOT NULL,
    entry_lon DECIMAL(11, 8) NOT NULL,
    exit_lat DECIMAL(10, 8) NOT NULL,
    exit_lon DECIMAL(11, 8) NOT NULL,
    entry_altitude INTEGER,                      -- Altitude in feet when entering sector
    exit_altitude INTEGER,                       -- Altitude in feet when exiting sector
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes for Performance:**
```sql
CREATE INDEX idx_flight_sector_occupancy_flight_id ON flight_sector_occupancy(flight_id);
CREATE INDEX idx_flight_sector_occupancy_sector_name ON flight_sector_occupancy(sector_name);
CREATE INDEX idx_flight_sector_occupancy_entry_timestamp ON flight_sector_occupancy(entry_timestamp);
```

### **Enhanced Flight Summaries** (`flight_summaries`)
**New Sector Fields:**
- **primary_enroute_sector**: VARCHAR(10) - Sector with most time spent (e.g., "WOL")
- **total_enroute_sectors**: INTEGER - Count of sectors visited (e.g., 3)
- **total_enroute_time_minutes**: INTEGER - Total time in enroute sectors (e.g., 60)
- **sector_breakdown**: JSONB - Detailed timing per sector

**Sector Breakdown JSONB Structure:**
```json
{
  "ARL": 5,     // 5 minutes in Armidale
  "WOL": 45,    // 45 minutes in Wollongong
  "HUO": 10     // 10 minutes in Huon
}
```

## 🔧 **Technical Implementation**

### **Sector Data Management (Simplified Approach)**
**Implementation**: JSON sector definitions parsed once at startup, converted to Shapely Polygons, stored in-memory as JSON data

**Scope**: **En-route sectors only** - Only processes sectors with type CTR (Center) nd FSS

**Technical Architecture**:
reuse as much of the boundary processing as possible
Benefits of Using the Same Flow:
Performance: get_cached_polygon() already has a caching mechanism (_polygon_cache) that prevents reloading the same JSON files
Consistency: Same error handling, validation, and logging across all polygon loading
Maintainability: One place to fix polygon loading issues
Memory efficiency: The cache prevents duplicate polygon objects in memory

**Storage Strategy**:
- **External Refdata Directory**: Contains only json sector files 


**Benefits**:
- **Simpler architecture** - No additional database tables for sector definitions
- **Faster performance** - In-memory polygon intersection testing
- **Matches "KEEP IT SIMPLE" philosophy** - Minimal moving parts

### **Data Flow**
```
Startup:

2. Parse json → Convert to Python data structures
3. Convert coordinates → Create Shapely Polygons
4. Store everything in memory as JSON-like Python objects

Runtime:
- Use in-memory data structures
- No disk I/O for sector data
- Fast polygon intersection testing
```



## 📍 **Sector Detection Process**

**Scope**: **En-route sectors only** (~85 sectors) - excludes terminal, ground, and other non-en-route sectors

**Process**:
1. **Sector Detection**: Check each flight position against en-route sector polygon boundaries using existing `geographic_utils.py` and Shapely library
2. **Entry/Exit Tracking**: Record timestamp when flight enters/exits each en-route sector
3. **Duration Calculation**: Calculate time spent in each en-route sector
4. **Summary Aggregation**: When flight completes, aggregate en-route sector data into JSONB

**Example Sector Tracking**:
```
10:00:00 - Enters ARL sector (Armidale) at FL250
10:05:00 - Exits ARL sector at FL250, enters WOL sector (Wollongong) at FL250
10:50:00 - Exits WOL sector at FL250, enters HUO sector (Huon) at FL250
11:00:00 - Exits HUO sector at FL250

Result:
- ARL (Armidale): 5 minutes at FL250
- WOL (Wollongong): 45 minutes at FL250  
- HUO (Huon): 10 minutes at FL250
```

**Altitude Tracking Benefits**:
- **Vertical Profile Analysis**: Track altitude changes between sectors
- **Climb/Descent Patterns**: Identify typical altitude profiles for routes
- **Performance Metrics**: Analyze altitude efficiency across sectors
- **Safety Analysis**: Monitor altitude compliance and separation
- **Route Optimization**: Optimize flight levels for sector transitions

**Sector Data Structure**:
- **Real-time**: `flight_sector_occupancy` table tracks each sector visit
- **Summary**: `sector_breakdown` JSONB in `flight_summaries` stores final totals

## ⚙️ **Configuration Requirements**

### **Docker Compose Variables**
```yaml
# Sector Tracking Settings
SECTOR_TRACKING_ENABLED: "true"         # Enable real-time sector occupancy tracking
SECTOR_UPDATE_INTERVAL: 60              # Seconds between sector position updates (1 minute)
```

### **Default Values**
- **SECTOR_TRACKING_ENABLED**: true
- **SECTOR_UPDATE_INTERVAL**: 60 seconds

## 🔄 **Real-Time Processing Requirements**

### **Processing Timing**
**Real-Time Processing (Every 60 seconds)**:
- **Flight position updates** in `flights` table
- **Sector boundary detection** using existing `geographic_utils.py` and Shapely
- **Sector occupancy tracking** in `flight_sector_occupancy` table

### **Data Flow**
1. **Active Flights**: Stored in `flights` table with real-time updates
2. **Sector Tracking**: Update `flight_sector_occupancy` as flights move between sectors using in-memory Shapely polygons (real-time)
3. **Summary Aggregation**: When flight completes, aggregate sector data into `sector_breakdown` JSONB

## 🚀 **Implementation Phases**

### **Phase 1: Core Infrastructure** ✅ **COMPLETED**
1. **Create `flight_sector_occupancy` table** ✅ **COMPLETED**
   - Base table structure with coordinates and timing
   - **NEW: Added `entry_altitude` and `exit_altitude` fields** ✅ **COMPLETED**
   - Performance indexes for fast queries
2. **Implement sector data loading from XML files** (Shapely Polygons in-memory)
3. **Enhance `geographic_utils.py`** with DDMM.MMMM coordinate parsing
4. **Create `sector_loader.py`** for XML parsing and sector management
5. **Add configuration variables** to Docker Compose

### **Altitude Fields Implementation** ✅ **COMPLETED**
- **Database Schema**: Added `entry_altitude INTEGER` and `exit_altitude INTEGER` fields
- **Migration Scripts**: Created automated and manual migration options
- **Field Purpose**: Track flight altitude when entering/exiting each sector
- **Benefits**: Enhanced vertical profile analysis and performance metrics

### **Phase 2: Sector Detection**
1. **Implement sector boundary detection** using existing `geographic_utils.py` and Shapely library
2. **Implement sector occupancy tracking** (en-route sectors only)
3. **Integrate sector tracking** with flight position updates
4. **Add sector entry/exit logging**

### **Phase 3: Integration & Testing**
1. **Integrate with existing data service**
2. **Implement one-time migration** of existing data
3. **Basic testing** with sample data
4. **Performance testing** and optimization
5. **Validate sector tracking accuracy**

### **Phase 4: Production Deployment**
1. **Staged deployment** (dev → staging → production)
2. **Monitor system performance**
3. **Validate sector tracking accuracy**
4. **Document operational procedures**

## 📋 **Implementation Tasks**

### **Core Development Tasks**
- [ ] **Design sector occupancy tracking system**
- [ ] **Implement sector boundary detection**
- [ ] **Create sector occupancy table and logic**
- [ ] **Enhance geographic_utils.py** with DDMM.MMMM parsing
- [ ] **Create sector_loader.py** for XML parsing
- [ ] **Integrate sector tracking** with flight position updates
- [ ] **Add configuration management**

### **Testing Tasks**
- [ ] **Test sector boundary detection**
- [ ] **Test sector occupancy tracking**
- [ ] **Performance testing** with ~85 sectors
- [ ] **Integration testing** with flight updates
- [ ] **Validate sector tracking accuracy**

### **Documentation Tasks**
- [ ] **Sector tracking operational guide**
- [ ] **API documentation updates**
- [ ] **Monitoring and alerting guide**
- [ ] **Troubleshooting guide**

## 📊 **Current Implementation Status**

### **✅ Completed Components**
- **Database Schema**: `flight_sector_occupancy` table with altitude fields
- **Migration Scripts**: Automated and manual migration options
- **Field Documentation**: Comprehensive field descriptions and benefits

### **🔄 Next Steps**
1. **Run Migration**: Execute altitude fields migration in database
2. **Test Schema**: Verify new fields are accessible and functional
3. **Continue Phase 1**: Implement sector data loading from XML files
4. **Enhance Geographic Utils**: Add DDMM.MMMM coordinate parsing support

### **📁 Migration Files Created**
- `scripts/add_altitude_fields_migration.sql` - SQL migration script
- `scripts/run_altitude_migration_simple.py` - Automated migration script
- `scripts/manual_altitude_migration.sql` - Manual SQL execution
- `database/init.sql` - Updated with new schema

## ❓ **Technical Questions (Resolved)**

### **All Technical Decisions Resolved:**
1. **Coordinate Conversion**: ✅ **SOLVED** - Add DDMM.MMMM parsing function to `geographic_utils.py`
2. **XML Parsing**: ✅ **SOLVED** - Create new `sector_loader.py` file for XML handling
3. **Sector Data Storage**: ✅ **SOLVED** - Use `SectorManager` class for in-memory sector data
4. **Error Handling**: ✅ **SOLVED** - Fail fast approach (stop everything if any sector fails to load)
5. **Sector Updates**: ✅ **SOLVED** - Restart required (sectors change rarely, not a performance concern)
6. **Performance Approach**: ✅ **SOLVED** - Simple loop approach for ~85 en-route sectors (3M operations/minute manageable)
7. **Sector Scope**: ✅ **SOLVED** - En-route sectors only (CTR, TMA, APP), excludes terminal/ground sectors

## 🎯 **Success Criteria**

### **Functional Requirements**
- [ ] **Sector occupancy data is accurately tracked** and summarized
- [ ] **Real-time sector detection** works for all en-route sectors
- [ ] **Sector entry/exit events** are properly logged
- [ ] **Sector breakdown data** is accurately aggregated in flight summaries
- [ ] **Performance impact is minimal** (<10ms per flight position update)

### **Quality Requirements**
- [ ] **Integration tests pass** with real flight data
- [ ] **Performance tests meet requirements** (3M operations/minute)
- [ ] **Error handling is robust** (fail fast approach)
- [ ] **Documentation is complete**

## 📊 **Expected Benefits**

### **Operational Benefits**
- **Real-time sector visibility** - Know which sectors have traffic
- **ATC coverage analysis** - Identify sectors without controller coverage
- **Traffic pattern analysis** - Understand common sector transitions
- **Capacity planning** - Identify busy sectors and times

### **Reporting Benefits**
- **Sector-based analytics** - "Flights in Sydney sector by hour"
- **Route analysis** - "Most common sector transitions"
- **Performance metrics** - "Sector occupancy rates"
- **Operational insights** - "Peak sector usage times"

## 🔮 **Future Enhancements**

### **Potential Improvements**
1. **Multiple boundary support** - Support different airspace regions
2. **Dynamic boundaries** - Update boundaries without restart
3. **Altitude filtering** - Consider flight altitude in boundary checks
4. **Time-based filtering** - Different boundaries for different times
5. **Caching optimization** - Cache boundary check results

### **Performance Optimizations**
1. **Spatial indexing** - Use R-tree for faster point-in-polygon checks
2. **Coordinate precision** - Optimize coordinate precision for performance
3. **Parallel processing** - Process multiple flights in parallel
4. **Memory pooling** - Reuse polygon objects to reduce GC pressure

## 📚 **Dependencies**

### **Required Libraries**
- `shapely==2.0.2` - Geographic calculations
- `lxml` - XML parsing (for sector data)

### **External Data Sources**
- **VATSYS sector data** - `ALL_SECTORS.xml`, `Sectors.xml`, `Volumes.xml`
- **Australian airspace boundary** - `australian_airspace_polygon.json`

## 📅 **Timeline Estimate**

### **Phase 1 (Core Infrastructure)**: 2-3 days
- Database table creation
- XML parsing implementation
- Coordinate conversion utilities

### **Phase 2 (Sector Detection)**: 2-3 days
- Boundary detection logic
- Real-time tracking integration
- Performance optimization

### **Phase 3 (Integration & Testing)**: 2-3 days
- System integration
- Testing and validation
- Performance tuning

### **Phase 4 (Production Deployment)**: 1-2 days
- Staged deployment
- Monitoring setup
- Documentation completion

**Total estimated time**: 7-11 days

## 🚨 **Risk Assessment**

### **Technical Risks**
- **Performance impact**: Boundary checks may slow processing
- **Memory usage**: Large polygon data may increase memory footprint
- **Coordinate precision**: Floating point precision issues

### **Mitigation Strategies**
- **Performance**: Pre-compute polygon, optimize algorithms
- **Memory**: Use efficient data structures, monitor usage
- **Precision**: Use appropriate coordinate precision, add validation

## 📝 **Conclusion**

This sector tracking implementation plan provides a comprehensive approach to implementing real-time sector occupancy tracking while maintaining system performance and reliability. The modular design allows for independent control and future enhancements.

The system will transform basic flight position data into rich sector-based insights, enabling much more sophisticated airspace analysis and operational reporting for the VATSIM data collection system.

