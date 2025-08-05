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
CREATE TABLE IF NOT EXISTS flights (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    aircraft_type VARCHAR(20),
    position_lat FLOAT,
    position_lng FLOAT,
    altitude INTEGER,
    speed INTEGER,
    heading INTEGER,
    ground_speed INTEGER,
    vertical_speed INTEGER,
    squawk VARCHAR(10),
    flight_plan JSONB,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    controller_id INTEGER,                   -- No FK constraint for write speed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    departure VARCHAR(10),
    arrival VARCHAR(10),
    route TEXT,
    status VARCHAR(20) DEFAULT 'active',
    updated_at TIMESTAMPTZ DEFAULT NOW()
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
    speed INTEGER,
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
        INSERT INTO flights (
            callsign, aircraft_type, position_lat, position_lng,
            altitude, speed, heading, ground_speed, vertical_speed,
            squawk, flight_plan, departure, arrival, route, status
        ) VALUES (
            flight_record->>'callsign',
            flight_record->>'aircraft_type',
            (flight_record->>'position_lat')::FLOAT,
            (flight_record->>'position_lng')::FLOAT,
            (flight_record->>'altitude')::INTEGER,
            (flight_record->>'speed')::INTEGER,
            (flight_record->>'heading')::INTEGER,
            (flight_record->>'ground_speed')::INTEGER,
            (flight_record->>'vertical_speed')::INTEGER,
            flight_record->>'squawk',
            flight_record->'flight_plan',
            flight_record->>'departure',
            flight_record->>'arrival',
            flight_record->>'route',
            COALESCE(flight_record->>'status', 'active')
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