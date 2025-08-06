-- Write-Optimized Table Schema for VATSIM Data Collection
-- OPTIMIZED FOR 99.9% WRITES - MINIMAL READS
-- High-throughput insert operations with minimal read overhead

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ===========================================
-- CONTROLLERS TABLE (Write-Optimized)
-- ===========================================
CREATE TABLE IF NOT EXISTS controllers (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,           -- No UNIQUE constraint for write speed
    facility VARCHAR(50) NOT NULL,
    position VARCHAR(50),
    status VARCHAR(20) DEFAULT 'offline',
    frequency VARCHAR(20),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    workload_score FLOAT DEFAULT 0.0,
    preferences JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- MINIMAL INDEXES for controllers (write-optimized)
CREATE INDEX IF NOT EXISTS idx_controllers_callsign ON controllers(callsign);
CREATE INDEX IF NOT EXISTS idx_controllers_last_seen ON controllers(last_seen);

-- ===========================================
-- FLIGHTS TABLE (Write-Optimized)
-- ===========================================
-- Write-optimized flights table for high-frequency inserts
CREATE TABLE IF NOT EXISTS flights_write_optimized (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    aircraft_type VARCHAR(20),
    position_lat DOUBLE PRECISION,
    position_lng DOUBLE PRECISION,
    
    -- Flight tracking fields
    altitude INTEGER,
    heading INTEGER,
    groundspeed INTEGER,
    cruise_tas INTEGER,
    squawk VARCHAR(10),
    
    -- Flight plan fields
    departure VARCHAR(10),
    arrival VARCHAR(10),
    route TEXT,
    flight_plan JSONB,
    
    -- Status and timestamps
    status VARCHAR(20) DEFAULT 'active',
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- VATSIM API fields
    cid INTEGER,
    name VARCHAR(100),
    server VARCHAR(50),
    pilot_rating INTEGER,
    military_rating INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    transponder VARCHAR(10),
    qnh_i_hg DECIMAL(4,2),
    qnh_mb INTEGER,
    logon_time TIMESTAMP WITH TIME ZONE,
    last_updated_api TIMESTAMP WITH TIME ZONE,
    
    -- Flight plan fields
    flight_rules VARCHAR(10),
    aircraft_faa VARCHAR(20),
    aircraft_short VARCHAR(10),
    alternate VARCHAR(10),
    planned_altitude INTEGER,
    deptime VARCHAR(10),
    enroute_time VARCHAR(10),
    fuel_time VARCHAR(10),
    remarks TEXT,
    revision_id INTEGER,
    assigned_transponder VARCHAR(10),
    
    -- Foreign keys
    controller_id INTEGER
);

-- MINIMAL INDEXES for flights (write-optimized)
CREATE INDEX IF NOT EXISTS idx_flights_callsign ON flights(callsign);
CREATE INDEX IF NOT EXISTS idx_flights_last_updated ON flights(last_updated);

-- ===========================================
-- SECTORS TABLE (Write-Optimized)
-- ===========================================
CREATE TABLE IF NOT EXISTS sectors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    facility VARCHAR(50) NOT NULL,
    controller_id INTEGER,                   -- No FK constraint for write speed
    traffic_density INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'unmanned',
    priority_level INTEGER DEFAULT 1,
    boundaries TEXT,  -- JSON string for sector boundaries
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- MINIMAL INDEXES for sectors
CREATE INDEX IF NOT EXISTS idx_sectors_facility ON sectors(facility);

-- ===========================================
-- TRAFFIC MOVEMENTS TABLE (Write-Optimized)
-- ===========================================
CREATE TABLE IF NOT EXISTS traffic_movements (
    id SERIAL PRIMARY KEY,
    airport_code VARCHAR(10) NOT NULL,
    movement_type VARCHAR(20) NOT NULL,
    aircraft_callsign VARCHAR(50),
    aircraft_type VARCHAR(20),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    runway VARCHAR(10),
    altitude INTEGER,
    heading INTEGER,
    metadata_json TEXT,  -- JSON string
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- MINIMAL INDEXES for traffic movements
CREATE INDEX IF NOT EXISTS idx_traffic_movements_timestamp ON traffic_movements(timestamp);

-- ===========================================
-- FLIGHT SUMMARIES TABLE (Write-Optimized)
-- ===========================================
CREATE TABLE IF NOT EXISTS flight_summaries (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(20) NOT NULL,
    aircraft_type VARCHAR(10),
    departure VARCHAR(10),
    arrival VARCHAR(10),
    route TEXT,
    max_altitude SMALLINT,
    duration_minutes SMALLINT,
    controller_id INTEGER,  -- Foreign key to controllers.id
    sector_id INTEGER,  -- Foreign key to sectors.id
    completed_at TIMESTAMPTZ NOT NULL
);

-- MINIMAL INDEXES for flight summaries
CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign ON flight_summaries(callsign);
CREATE INDEX IF NOT EXISTS idx_flight_summaries_completed_at ON flight_summaries(completed_at);

-- ===========================================
-- MOVEMENT SUMMARIES TABLE (Write-Optimized)
-- ===========================================
CREATE TABLE IF NOT EXISTS movement_summaries (
    id SERIAL PRIMARY KEY,
    airport_icao VARCHAR(10) NOT NULL,
    movement_type VARCHAR(10) NOT NULL,
    aircraft_type VARCHAR(10),
    date TIMESTAMPTZ NOT NULL,
    hour SMALLINT NOT NULL,
    count SMALLINT DEFAULT 1
);

-- MINIMAL INDEXES for movement summaries
CREATE INDEX IF NOT EXISTS idx_movement_summaries_airport_date ON movement_summaries(airport_icao, date);

-- ===========================================
-- AIRPORTS TABLE (Global Airport Database)
-- ===========================================
CREATE TABLE IF NOT EXISTS airports (
    id SERIAL PRIMARY KEY,
    icao_code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(200),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    elevation INTEGER,  -- Feet above sea level
    country VARCHAR(100),
    region VARCHAR(100),  -- State/province
    timezone VARCHAR(50),
    facility_type VARCHAR(50),  -- airport, heliport, seaplane_base
    runways TEXT,  -- JSON string for runway data
    frequencies TEXT,  -- JSON string for frequency data
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- INDEXES for airports
CREATE INDEX IF NOT EXISTS idx_airports_country ON airports(country);
CREATE INDEX IF NOT EXISTS idx_airports_region ON airports(region);
CREATE INDEX IF NOT EXISTS idx_airports_icao_prefix ON airports(icao_code);

-- ===========================================
-- AIRPORT CONFIG TABLE
-- ===========================================
CREATE TABLE IF NOT EXISTS airport_config (
    id SERIAL PRIMARY KEY,
    icao_code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    detection_radius_nm FLOAT DEFAULT 10.0,
    departure_altitude_threshold INTEGER DEFAULT 1000,
    arrival_altitude_threshold INTEGER DEFAULT 3000,
    departure_speed_threshold INTEGER DEFAULT 50,
    arrival_speed_threshold INTEGER DEFAULT 150,
    is_active BOOLEAN DEFAULT TRUE,
    region VARCHAR(50),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- MOVEMENT DETECTION CONFIG TABLE
-- ===========================================
CREATE TABLE IF NOT EXISTS movement_detection_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- SYSTEM CONFIG TABLE
-- ===========================================
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    description TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    environment VARCHAR(20) DEFAULT 'development'
);

-- ===========================================
-- EVENTS TABLE
-- ===========================================
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    expected_traffic INTEGER DEFAULT 0,
    required_controllers INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'scheduled',
    notes TEXT
);

-- ===========================================
-- WRITE-OPTIMIZED FUNCTIONS
-- ===========================================

-- Function to update updated_at timestamp (minimal overhead)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function for bulk insert optimization
CREATE OR REPLACE FUNCTION bulk_insert_flights(flight_data JSONB[])
RETURNS INTEGER AS $$
DECLARE
    flight_record JSONB;
    inserted_count INTEGER := 0;
BEGIN
    FOREACH flight_record IN ARRAY flight_data
    LOOP
        INSERT INTO flights_write_optimized (
            callsign, aircraft_type, position_lat, position_lng,
            altitude, heading, groundspeed, cruise_tas,
            squawk, departure, arrival, route, flight_plan, status,
            cid, name, server, pilot_rating, military_rating,
            latitude, longitude, transponder, qnh_i_hg, qnh_mb,
            logon_time, last_updated_api, flight_rules, aircraft_faa,
            aircraft_short, alternate, planned_altitude, deptime,
            enroute_time, fuel_time, remarks, revision_id,
            assigned_transponder, controller_id
        ) VALUES (
            flight_record->>'callsign',
            flight_record->>'aircraft_type',
            (flight_record->>'position_lat')::DOUBLE PRECISION,
            (flight_record->>'position_lng')::DOUBLE PRECISION,
            (flight_record->>'altitude')::INTEGER,
            (flight_record->>'heading')::INTEGER,
            (flight_record->>'groundspeed')::INTEGER,
            (flight_record->>'cruise_tas')::INTEGER,
            flight_record->>'squawk',
            flight_record->>'departure',
            flight_record->>'arrival',
            flight_record->>'route',
            flight_record->'flight_plan',
            COALESCE(flight_record->>'status', 'active'),
            (flight_record->>'cid')::INTEGER,
            flight_record->>'name',
            flight_record->>'server',
            (flight_record->>'pilot_rating')::INTEGER,
            (flight_record->>'military_rating')::INTEGER,
            (flight_record->>'latitude')::DOUBLE PRECISION,
            (flight_record->>'longitude')::DOUBLE PRECISION,
            flight_record->>'transponder',
            (flight_record->>'qnh_i_hg')::DECIMAL(4,2),
            (flight_record->>'qnh_mb')::INTEGER,
            (flight_record->>'logon_time')::TIMESTAMP WITH TIME ZONE,
            (flight_record->>'last_updated_api')::TIMESTAMP WITH TIME ZONE,
            flight_record->>'flight_rules',
            flight_record->>'aircraft_faa',
            flight_record->>'aircraft_short',
            flight_record->>'alternate',
            (flight_record->>'planned_altitude')::INTEGER,
            flight_record->>'deptime',
            flight_record->>'enroute_time',
            flight_record->>'fuel_time',
            flight_record->>'remarks',
            (flight_record->>'revision_id')::INTEGER,
            flight_record->>'assigned_transponder',
            (flight_record->>'controller_id')::INTEGER
        );
        inserted_count := inserted_count + 1;
    END LOOP;
    
    RETURN inserted_count;
END;
$$ LANGUAGE plpgsql;

-- Function for bulk insert controllers
CREATE OR REPLACE FUNCTION bulk_insert_controllers(controller_data JSONB[])
RETURNS INTEGER AS $$
DECLARE
    controller_record JSONB;
    inserted_count INTEGER := 0;
BEGIN
    FOREACH controller_record IN ARRAY controller_data
    LOOP
        INSERT INTO controllers (
            callsign, facility, position, status, frequency,
            workload_score, preferences
        ) VALUES (
            controller_record->>'callsign',
            controller_record->>'facility',
            controller_record->>'position',
            COALESCE(controller_record->>'status', 'offline'),
            controller_record->>'frequency',
            COALESCE((controller_record->>'workload_score')::FLOAT, 0.0),
            controller_record->'preferences'
        );
        inserted_count := inserted_count + 1;
    END LOOP;
    
    RETURN inserted_count;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- MINIMAL TRIGGERS (Write-Optimized)
-- ===========================================

-- Only essential triggers for write performance
CREATE TRIGGER update_controllers_updated_at 
    BEFORE UPDATE ON controllers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_flights_updated_at 
    BEFORE UPDATE ON flights 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- WRITE PERFORMANCE OPTIMIZATIONS
-- ===========================================

-- Set table storage parameters for write optimization
ALTER TABLE flights SET (fillfactor = 100);      -- No space for updates
ALTER TABLE controllers SET (fillfactor = 100);   -- No space for updates
ALTER TABLE traffic_movements SET (fillfactor = 100);
ALTER TABLE events SET (fillfactor = 100);

-- Disable autovacuum for write-heavy tables (use manual cleanup)
ALTER TABLE flights SET (autovacuum_enabled = false);
ALTER TABLE controllers SET (autovacuum_enabled = false);
ALTER TABLE traffic_movements SET (autovacuum_enabled = false);
ALTER TABLE events SET (autovacuum_enabled = false); 