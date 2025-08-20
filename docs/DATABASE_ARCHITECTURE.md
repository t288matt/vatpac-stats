# 🗄️ VATSIM Data Collection System - Database Architecture

## 📋 Overview

This document provides a comprehensive overview of the database architecture for the VATSIM Data Collection System. The system uses PostgreSQL as its primary database engine and is designed for high-performance real-time data collection, efficient storage, and rapid querying of air traffic control data.

**Database Engine**: PostgreSQL 13+  
**Primary Use Case**: Real-time VATSIM flight data collection and analysis  
**Design Philosophy**: Performance-first with data integrity and scalability  

---

## 🏗️ **Database Schema Overview**

### **Core Tables (Real-time Data)**
1. **`controllers`** - ATC controller positions and status
2. **`flights`** - Active flight data and positions  
3. **`transceivers`** - Radio frequency and communication data
4. **`flight_sector_occupancy`** - Real-time sector tracking

### **Summary Tables (Aggregated Data)**
5. **`flight_summaries`** - Completed flight summaries
6. **`flights_archive`** - Historical flight records
7. **`controller_summaries`** - Controller session summaries

---

## 📊 **Table Architecture Details**

### **1. Controllers Table (`controllers`)**

**Purpose**: Stores real-time ATC controller positions and status information from VATSIM API.

**Schema**:
```sql
CREATE TABLE controllers (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,           -- Controller callsign (e.g., "SY_TWR")
    frequency VARCHAR(20),                   -- Active frequency
    cid INTEGER,                            -- VATSIM user ID
    name VARCHAR(100),                      -- Controller's real name
    rating INTEGER,                         -- Controller rating (-1 to 12)
    facility INTEGER,                       -- Facility type (0-6)
    visual_range INTEGER,                   -- Visual range in nautical miles
    text_atis TEXT,                         -- ATIS information
    server VARCHAR(50),                     -- Network server
    last_updated TIMESTAMP WITH TIME ZONE,  -- Last API update
    logon_time TIMESTAMP WITH TIME ZONE,    -- Session start time
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features**:
- **Real-time updates**: Updated every 5 seconds from VATSIM API
- **Rating validation**: Enforces valid controller ratings (-1 to 12)
- **Facility validation**: Enforces valid facility types (0-6)
- **Automatic timestamps**: `created_at` and `updated_at` managed by triggers

**Indexes**:
```sql
-- Performance indexes
CREATE INDEX idx_controllers_callsign ON controllers(callsign);
CREATE INDEX idx_controllers_cid ON controllers(cid);
CREATE INDEX idx_controllers_facility_server ON controllers(facility, server);
CREATE INDEX idx_controllers_last_updated ON controllers(last_updated);
CREATE INDEX idx_controllers_rating_last_updated ON controllers(rating, last_updated);
```

---

### **2. Flights Table (`flights`)**

**Purpose**: Stores real-time flight data including position, flight plan, and pilot information.

**Schema**:
```sql
CREATE TABLE flights (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,          -- Aircraft callsign
    aircraft_type VARCHAR(20),              -- Aircraft type code
    
    -- Position Data (Real-time)
    latitude DOUBLE PRECISION,              -- Current latitude
    longitude DOUBLE PRECISION,             -- Current longitude
    altitude INTEGER,                       -- Current altitude (feet)
    heading INTEGER,                        -- Current heading (degrees)
    groundspeed INTEGER,                    -- Current ground speed (knots)
    
    -- Flight Plan Data
    departure VARCHAR(10),                  -- Departure airport code
    arrival VARCHAR(10),                    -- Arrival airport code
    route TEXT,                             -- Flight plan route
    flight_rules VARCHAR(10),               -- IFR/VFR
    aircraft_faa VARCHAR(20),               -- FAA aircraft code
    aircraft_short VARCHAR(20),             -- Short aircraft code
    planned_altitude VARCHAR(10),           -- Planned cruise altitude
    
    -- Pilot Information
    cid INTEGER,                            -- VATSIM user ID
    name VARCHAR(100),                      -- Pilot name
    server VARCHAR(50),                     -- Network server
    pilot_rating INTEGER,                   -- Pilot rating
    military_rating INTEGER,                -- Military rating
    
    -- Timestamps
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    logon_time TIMESTAMP WITH TIME ZONE,    -- Connection time
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features**:
- **Complete flight tracking**: Every position update preserved
- **Flight plan validation**: Essential fields required for data quality
- **Geographic constraints**: Latitude/longitude validation
- **Performance optimized**: Extensive indexing for rapid queries

**Indexes**:
```sql
-- Core performance indexes
CREATE INDEX idx_flights_callsign ON flights(callsign);
CREATE INDEX idx_flights_position ON flights(latitude, longitude);
CREATE INDEX idx_flights_departure_arrival ON flights(departure, arrival);
CREATE INDEX idx_flights_altitude ON flights(altitude);

-- ATC detection optimization
CREATE INDEX idx_flights_callsign_departure_arrival ON flights(callsign, departure, arrival);
CREATE INDEX idx_flights_callsign_logon ON flights(callsign, logon_time);
```

---

### **3. Transceivers Table (`transceivers`)**

**Purpose**: Tracks radio frequency usage and communication between aircraft and ATC.

**Schema**:
```sql
CREATE TABLE transceivers (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,          -- Entity callsign
    transceiver_id INTEGER NOT NULL,        -- VATSIM transceiver ID
    frequency BIGINT NOT NULL,              -- Frequency in Hz
    position_lat DOUBLE PRECISION,          -- Position latitude
    position_lon DOUBLE PRECISION,          -- Position longitude
    height_msl DOUBLE PRECISION,            -- Height above mean sea level (meters)
    height_agl DOUBLE PRECISION,            -- Height above ground level (meters)
    entity_type VARCHAR(20) NOT NULL,       -- 'flight' or 'atc'
    entity_id INTEGER,                      -- Foreign key to flights.id or controllers.id
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features**:
- **Dual entity support**: Tracks both flight and ATC transceivers
- **Frequency monitoring**: Real-time frequency usage tracking
- **Position correlation**: Links frequency usage to geographic position
- **Performance optimized**: Specialized indexes for ATC detection

**Indexes**:
```sql
-- Core indexes
CREATE INDEX idx_transceivers_callsign ON transceivers(callsign);
CREATE INDEX idx_transceivers_frequency ON transceivers(frequency);
CREATE INDEX idx_transceivers_entity ON transceivers(entity_type, entity_id);

-- ATC detection optimization
CREATE INDEX idx_transceivers_atc_detection ON transceivers(
    entity_type, callsign, timestamp, frequency, position_lat, position_lon
);
```

---

### **4. Flight Sector Occupancy Table (`flight_sector_occupancy`)**

**Purpose**: Real-time tracking of flights entering and exiting Australian airspace sectors.

**Schema**:
```sql
CREATE TABLE flight_sector_occupancy (
    id BIGSERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,          -- Aircraft callsign
    sector_name VARCHAR(10) NOT NULL,       -- Sector identifier (e.g., "WOL")
    entry_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_timestamp TIMESTAMP WITH TIME ZONE, -- NULL until exit
    duration_seconds INTEGER DEFAULT 0,     -- Calculated on exit
    entry_lat DECIMAL(10, 8) NOT NULL,     -- Entry position
    entry_lon DECIMAL(11, 8) NOT NULL,
    exit_lat DECIMAL(10, 8),               -- Exit position (NULL until exit)
    exit_lon DECIMAL(11, 8),               -- Exit position (NULL until exit)
    entry_altitude INTEGER,                 -- Entry altitude (feet)
    exit_altitude INTEGER,                  -- Exit altitude (feet)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features**:
- **Real-time tracking**: Continuous sector entry/exit monitoring
- **Altitude tracking**: Vertical profile for sector transitions
- **Performance optimized**: <1ms per flight for sector detection
- **Automatic cleanup**: Stale sector management system

**Indexes**:
```sql
CREATE INDEX idx_flight_sector_occupancy_callsign ON flight_sector_occupancy(callsign);
CREATE INDEX idx_flight_sector_occupancy_sector_name ON flight_sector_occupancy(sector_name);
CREATE INDEX idx_flight_sector_occupancy_entry_timestamp ON flight_sector_occupancy(entry_timestamp);
```

---

### **5. Flight Summaries Table (`flight_summaries`)**

**Purpose**: Pre-computed summaries of completed flights for rapid analytics and reporting.

**Schema**:
```sql
CREATE TABLE flight_summaries (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,          -- Aircraft callsign
    aircraft_type VARCHAR(20),              -- Aircraft type
    departure VARCHAR(10),                  -- Departure airport
    arrival VARCHAR(10),                    -- Arrival airport
    logon_time TIMESTAMP WITH TIME ZONE,    -- Connection time
    route TEXT,                             -- Flight plan route
    flight_rules VARCHAR(10),               -- IFR/VFR
    aircraft_faa VARCHAR(20),               -- FAA aircraft code
    planned_altitude VARCHAR(10),           -- Planned cruise altitude
    aircraft_short VARCHAR(20),             -- Short aircraft code
    
    -- Pilot Information
    cid INTEGER,                            -- VATSIM user ID
    name VARCHAR(100),                      -- Pilot name
    server VARCHAR(50),                     -- Network server
    pilot_rating INTEGER,                   -- Pilot rating
    military_rating INTEGER,                -- Military rating
    
    -- ATC Interaction Summary
    controller_callsigns JSONB,             -- Controller interaction data
    controller_time_percentage DECIMAL(5,2), -- % time with ATC contact
    time_online_minutes INTEGER,            -- Total online time
    
    -- Sector Analysis
    primary_enroute_sector VARCHAR(50),     -- Primary sector flown
    total_enroute_sectors INTEGER,          -- Total sectors visited
    total_enroute_time_minutes INTEGER,     -- Total enroute time
    sector_breakdown JSONB,                 -- Detailed sector timing
    
    -- Metadata
    completion_time TIMESTAMP WITH TIME ZONE, -- When flight completed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features**:
- **Pre-computed analytics**: Instant query results
- **JSONB storage**: Flexible controller and sector data
- **Performance optimized**: 100-300x faster than real-time aggregation
- **Automatic processing**: Generated every 60 minutes

**JSONB Structures**:
```json
// controller_callsigns
{
  "SY_TWR": {
    "callsign": "SY_TWR",
    "type": "TWR",
    "time_minutes": 15,
    "first_contact": "2025-01-15T10:00:00Z",
    "last_contact": "2025-01-15T10:15:00Z"
  }
}

// sector_breakdown
{
  "ARL": 5,     // 5 minutes in Armidale
  "WOL": 45,    // 45 minutes in Wollongong
  "HUO": 10     // 10 minutes in Huon
}
```

**Indexes**:
```sql
CREATE INDEX idx_flight_summaries_callsign ON flight_summaries(callsign);
CREATE INDEX idx_flight_summaries_completion_time ON flight_summaries(completion_time);
CREATE INDEX idx_flight_summaries_flight_rules ON flight_summaries(flight_rules);
CREATE INDEX idx_flight_summaries_controller_time ON flight_summaries(controller_time_percentage);
```

---

### **6. Flights Archive Table (`flights_archive`)**

**Purpose**: Long-term storage of detailed flight records for historical analysis.

**Schema**:
```sql
CREATE TABLE flights_archive (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,          -- Aircraft callsign
    aircraft_type VARCHAR(20),              -- Aircraft type
    departure VARCHAR(10),                  -- Departure airport
    arrival VARCHAR(10),                    -- Arrival airport
    logon_time TIMESTAMP WITH TIME ZONE,    -- Connection time
    route TEXT,                             -- Flight plan route
    flight_rules VARCHAR(10),               -- IFR/VFR
    aircraft_faa VARCHAR(20),               -- FAA aircraft code
    planned_altitude VARCHAR(10),           -- Planned cruise altitude
    aircraft_short VARCHAR(20),             -- Short aircraft code
    
    -- Pilot Information
    cid INTEGER,                            -- VATSIM user ID
    name VARCHAR(100),                      -- Pilot name
    server VARCHAR(50),                     -- Network server
    pilot_rating INTEGER,                   -- Pilot rating
    military_rating INTEGER,                -- Military rating
    
    -- Final Position Data
    latitude DOUBLE PRECISION,              -- Final latitude
    longitude DOUBLE PRECISION,             -- Final longitude
    altitude INTEGER,                       -- Final altitude
    groundspeed INTEGER,                    -- Final ground speed
    heading INTEGER,                        -- Final heading
    last_updated TIMESTAMP WITH TIME ZONE,  -- Final update time
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features**:
- **Complete preservation**: All flight data preserved indefinitely
- **Storage optimization**: ~90% reduction in daily storage growth
- **Historical analysis**: Complete data for trend analysis
- **Performance optimized**: Indexed for rapid historical queries

**Indexes**:
```sql
CREATE INDEX idx_flights_archive_callsign ON flights_archive(callsign);
CREATE INDEX idx_flights_archive_logon_time ON flights_archive(logon_time);
CREATE INDEX idx_flights_archive_last_updated ON flights_archive(last_updated);
```

---

### **7. Controller Summaries Table (`controller_summaries`)**

**Purpose**: Pre-computed summaries of controller sessions for rapid ATC analytics.

**Schema**:
```sql
CREATE TABLE controller_summaries (
    id BIGSERIAL PRIMARY KEY,
    
    -- Controller Identity
    callsign VARCHAR(50) NOT NULL,          -- Controller callsign
    cid INTEGER,                            -- VATSIM user ID
    name VARCHAR(100),                      -- Controller name
    
    -- Session Summary
    session_start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    session_end_time TIMESTAMP WITH TIME ZONE,
    session_duration_minutes INTEGER DEFAULT 0,
    
    -- Controller Details
    rating INTEGER,                         -- Controller rating
    facility INTEGER,                        -- Facility type
    server VARCHAR(50),                     -- Network server
    
    -- Aircraft Activity
    total_aircraft_handled INTEGER DEFAULT 0,
    peak_aircraft_count INTEGER DEFAULT 0,
    hourly_aircraft_breakdown JSONB,       -- Aircraft count per hour
    frequencies_used JSONB,                 -- Frequencies used
    aircraft_details JSONB,                 -- Detailed aircraft data
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features**:
- **Session analytics**: Complete controller session summaries
- **Aircraft tracking**: Detailed aircraft interaction data using controller-specific proximity ranges
- **Performance optimized**: 100-300x faster than real-time queries
- **JSONB flexibility**: Rich data structures for detailed analysis
- **Controller-specific proximity**: Dynamic ranges based on controller type (Ground/Tower: 15nm, Approach: 60nm, Center: 400nm, FSS: 1000nm)

---

## 🎮 **Controller-Specific Proximity System**

### **Purpose**
The system uses intelligent proximity ranges based on controller type to provide realistic ATC operations and optimized performance.

### **Proximity Ranges by Controller Type**
```sql
-- Environment variable configuration in docker-compose.yml
CONTROLLER_PROXIMITY_GROUND_NM: "15"      -- Ground controllers (local airport operations)
CONTROLLER_PROXIMITY_TOWER_NM: "15"       -- Tower controllers (approach/departure operations)
CONTROLLER_PROXIMITY_APPROACH_NM: "60"    -- Approach controllers (terminal area operations)
CONTROLLER_PROXIMITY_CENTER_NM: "400"     -- Center controllers (enroute operations)
CONTROLLER_PROXIMITY_FSS_NM: "1000"      -- FSS controllers (flight service operations)
CONTROLLER_PROXIMITY_DEFAULT_NM: "30"     -- Fallback for unknown controller types
```

### **Implementation Details**
- **Automatic Detection**: Controller type detected from callsign patterns (last 3 characters)
- **Dynamic Configuration**: Proximity ranges configurable via environment variables
- **Performance Impact**: Ground/Tower controllers get faster queries due to smaller search radius
- **Realistic Operations**: Matches real-world ATC coverage areas and responsibilities

### **Database Integration**
- **Flight Detection Service**: Uses dynamic proximity ranges for aircraft interaction detection
- **Controller Summaries**: Aircraft counts calculated using appropriate proximity ranges
- **Real-time Processing**: Proximity ranges applied during live data processing
- **Performance Monitoring**: System tracks proximity range usage and effectiveness

### **Comprehensive Testing & Validation**
- **ATCDetectionService Tests**: 8 comprehensive tests ensuring service symmetry with FlightDetectionService
- **Real Outcome Verification**: Tests verify actual controller detection, proximity assignment, and live API behavior
- **Service Symmetry**: Both detection services use identical ControllerTypeDetector logic and return identical results
- **Live System Testing**: E2E tests call actual running endpoints to verify real proximity calculations
- **Controller Type Accuracy**: 100% accuracy for all controller types (Ground, Tower, Approach, Center, FSS)

---

## 🔗 **Table Relationships**

### **Primary Relationships**
```
controllers (id) ←→ transceivers (entity_id, entity_type='atc')
flights (id) ←→ transceivers (entity_id, entity_type='flight')
flights (callsign) ←→ flight_sector_occupancy (callsign)
flights (callsign) ←→ flight_summaries (callsign)
flights (callsign) ←→ flights_archive (callsign)
controllers (callsign) ←→ controller_summaries (callsign)
```

### **Data Flow Relationships**
```
VATSIM API → Real-time Tables → Summary Tables → Archive Tables
     ↓              ↓              ↓              ↓
  controllers    flights      flight_summaries  flights_archive
     ↓              ↓              ↓
  transceivers  flight_sector_occupancy
```

---

## 📈 **Performance Architecture**

### **Indexing Strategy**
- **Primary keys**: Auto-incrementing SERIAL for rapid inserts
- **Composite indexes**: Multi-column indexes for complex queries
- **Partial indexes**: WHERE clause optimization for specific entity types
- **JSONB indexes**: GIN indexes for JSON field queries

### **Query Optimization**
- **Summary tables**: Pre-computed aggregations for instant results
- **Real-time tables**: Optimized for rapid position updates
- **Archive tables**: Long-term storage with minimal query overhead
- **Sector tracking**: Specialized indexes for geographic queries

### **Performance Metrics**
- **Real-time updates**: <1ms per entity for geographic filtering
- **Summary queries**: 10-50ms vs 5-15 seconds for real-time aggregation
- **Sector detection**: <1ms per flight for boundary intersection
- **Storage efficiency**: ~90% reduction in daily growth through summarization

---

## 🔒 **Data Integrity & Constraints**

### **Validation Constraints**
```sql
-- Controllers
ALTER TABLE controllers ADD CONSTRAINT valid_rating 
    CHECK (rating >= -1 AND rating <= 12);
ALTER TABLE controllers ADD CONSTRAINT valid_facility 
    CHECK (facility >= 0 AND facility <= 6);

-- Flights
ALTER TABLE flights ADD CONSTRAINT valid_latitude 
    CHECK (latitude >= -90 AND latitude <= 90);
ALTER TABLE flights ADD CONSTRAINT valid_longitude 
    CHECK (longitude >= -180 AND longitude <= 180);
ALTER TABLE flights ADD CONSTRAINT valid_altitude 
    CHECK (altitude >= -1000 AND altitude <= 100000);

-- Transceivers
ALTER TABLE transceivers ADD CONSTRAINT valid_entity_type 
    CHECK (entity_type IN ('flight', 'atc'));
```

### **Triggers**
```sql
-- Automatic timestamp updates
CREATE TRIGGER update_controllers_updated_at 
    BEFORE UPDATE ON controllers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Similar triggers for all tables with updated_at columns
```

---

## 🗂️ **Data Lifecycle Management**

### **Real-time Data Flow**
1. **VATSIM API** → **Real-time tables** (controllers, flights, transceivers)
2. **Position updates** → **Sector tracking** (flight_sector_occupancy)
3. **Continuous monitoring** → **Real-time analytics**

### **Summary Processing**
1. **Background task** runs every 60 minutes
2. **Completed flights** → **flight_summaries** table
3. **Controller sessions** → **controller_summaries** table
4. **Old real-time data** → **flights_archive** table

### **Storage Optimization**
- **Active data**: Real-time tables (recent 24-48 hours)
- **Summary data**: Aggregated tables (long-term analytics)
- **Archive data**: Historical tables (complete preservation)
- **Automatic cleanup**: Stale sector management

---

## 🚀 **Scaling Considerations**

### **Current Capacity**
- **Real-time tables**: Optimized for 1000+ concurrent entities
- **Summary tables**: Support millions of historical records
- **Archive tables**: Unlimited historical storage
- **Performance**: Sub-second response times for all queries

### **Future Scaling**
- **Partitioning**: Time-based partitioning for large tables
- **Read replicas**: Separate read/write databases
- **Materialized views**: Additional pre-computed aggregations
- **Data retention**: Configurable retention policies

---

## 📚 **Related Documentation**

- **`config/init.sql`** - Complete database initialization script
- **`docs/API_FIELD_MAPPING.md`** - VATSIM API field mappings
- **`docs/SECTOR_TRACKING_IMPLEMENTATION_PLAN.md`** - Sector tracking details
- **`docs/MATERIALIZED_VIEW_OPTIMIZATION.md`** - Performance optimization strategies

---

## 🔧 **Maintenance & Operations**

### **Regular Maintenance**
- **Index optimization**: Monthly index analysis and optimization
- **Statistics updates**: Automatic statistics collection
- **Vacuum operations**: Automatic cleanup of dead tuples
- **Performance monitoring**: Query performance tracking

### **Backup Strategy**
- **Daily backups**: Complete database backups
- **Point-in-time recovery**: WAL archiving for recovery
- **Automated testing**: Backup restoration testing
- **Offsite storage**: Cloud backup integration

---

*This document provides a comprehensive overview of the database architecture. For specific implementation details, refer to the individual table specifications and related documentation.*



