-- Comprehensive Database Initialization Script
-- This script creates all tables with all required fields for the VATSIM data collection system
-- Run automatically when PostgreSQL container starts for the first time
-- 
-- VATSIM API Field Mapping:
-- - API "cid" → controller_id (Controller ID from VATSIM)
-- - API "name" → controller_name (Controller name from VATSIM)  
-- - API "rating" → controller_rating (Controller rating from VATSIM)
-- - All new fields use 1:1 mapping with VATSIM API field names

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create or replace the update_updated_at_column function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Controllers table with all VATSIM API fields
CREATE TABLE IF NOT EXISTS controllers (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) UNIQUE NOT NULL,
    facility VARCHAR(50) NOT NULL,
    position VARCHAR(50),
    status VARCHAR(20) DEFAULT 'offline',
    frequency VARCHAR(20),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    workload_score DOUBLE PRECISION DEFAULT 0.0,
    preferences TEXT,
    -- VATSIM API fields
    controller_id INTEGER,  -- From API "cid"
    controller_name VARCHAR(100),  -- From API "name"
    controller_rating INTEGER,  -- From API "rating"
    -- Missing VATSIM API fields - 1:1 mapping with API field names
    visual_range INTEGER,  -- Visual range in nautical miles
    text_atis TEXT,  -- ATIS text information
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sectors table removed - VATSIM API v3 does not provide sectors data
-- CREATE TABLE IF NOT EXISTS sectors (...) -- REMOVED

-- Flights table with all VATSIM API fields
CREATE TABLE IF NOT EXISTS flights (
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
    transponder VARCHAR(10),
    
    -- Flight plan fields
    departure VARCHAR(10),
    arrival VARCHAR(10),
    route TEXT,
    
    -- Timestamps
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- VATSIM API fields - 1:1 mapping with API field names
    cid INTEGER,  -- VATSIM user ID
    name VARCHAR(100),  -- Pilot name
    server VARCHAR(50),  -- Network server
    pilot_rating INTEGER,  -- Pilot rating
    military_rating INTEGER,  -- Military rating
    latitude DOUBLE PRECISION,  -- Position latitude
    longitude DOUBLE PRECISION,  -- Position longitude
    transponder VARCHAR(10),  -- Transponder code
    qnh_i_hg DECIMAL(4,2),  -- QNH in inches Hg
    qnh_mb INTEGER,  -- QNH in millibars
    logon_time TIMESTAMP WITH TIME ZONE,  -- When pilot connected
    last_updated_api TIMESTAMP WITH TIME ZONE,  -- API last_updated timestamp
    
    -- Flight plan fields (nested object)
    flight_rules VARCHAR(10),  -- IFR/VFR
    aircraft_faa VARCHAR(20),  -- FAA aircraft code
    aircraft_short VARCHAR(10),  -- Short aircraft code
    alternate VARCHAR(10),  -- Alternate airport
    planned_altitude INTEGER,  -- Planned cruise altitude
    deptime VARCHAR(10),  -- Departure time
    enroute_time VARCHAR(10),  -- Enroute time
    fuel_time VARCHAR(10),  -- Fuel time
    remarks TEXT,  -- Flight plan remarks
    revision_id INTEGER,  -- Flight plan revision
    assigned_transponder VARCHAR(10)  -- Assigned transponder
);

-- REMOVED: Traffic Analysis Service - Phase 3
-- Traffic movements table removed
-- CREATE TABLE IF NOT EXISTS traffic_movements (...) -- REMOVED

-- Airport config table removed - functionality merged with airports table
-- CREATE TABLE IF NOT EXISTS airport_config (...) -- REMOVED

-- Airports table
CREATE TABLE IF NOT EXISTS airports (
    id SERIAL PRIMARY KEY,
    icao_code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(200),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    elevation INTEGER,
    country VARCHAR(100),
    region VARCHAR(100)
);

-- Movement detection config table removed - configuration handled via environment variables
-- CREATE TABLE IF NOT EXISTS movement_detection_config (...) -- REMOVED

-- Transceivers table
CREATE TABLE IF NOT EXISTS transceivers (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    transceiver_id INTEGER NOT NULL,
    frequency BIGINT NOT NULL,
    position_lat DOUBLE PRECISION,
    position_lon DOUBLE PRECISION,
    height_msl DOUBLE PRECISION,
    height_agl DOUBLE PRECISION,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_controllers_callsign ON controllers(callsign);
CREATE INDEX IF NOT EXISTS idx_controllers_controller_id ON controllers(controller_id);
CREATE INDEX IF NOT EXISTS idx_flights_callsign ON flights(callsign);
CREATE INDEX IF NOT EXISTS idx_flights_cid ON flights(cid);
CREATE INDEX IF NOT EXISTS idx_flights_name ON flights(name);
CREATE INDEX IF NOT EXISTS idx_flights_server ON flights(server);
CREATE INDEX IF NOT EXISTS idx_flights_latitude ON flights(latitude);
CREATE INDEX IF NOT EXISTS idx_flights_longitude ON flights(longitude);
CREATE INDEX IF NOT EXISTS idx_flights_groundspeed ON flights(groundspeed);
CREATE INDEX IF NOT EXISTS idx_flights_transponder ON flights(transponder);
CREATE INDEX IF NOT EXISTS idx_flights_logon_time ON flights(logon_time);
CREATE INDEX IF NOT EXISTS idx_flights_last_updated_api ON flights(last_updated_api);
CREATE INDEX IF NOT EXISTS idx_controllers_visual_range ON controllers(visual_range);
-- REMOVED: Traffic Analysis Service - Phase 3
-- CREATE INDEX IF NOT EXISTS idx_traffic_movements_airport ON traffic_movements(airport_code); -- REMOVED
-- CREATE INDEX IF NOT EXISTS idx_traffic_movements_timestamp ON traffic_movements(timestamp); -- REMOVED
-- CREATE INDEX IF NOT EXISTS idx_airport_config_icao ON airport_config(icao_code); -- REMOVED - table removed
CREATE INDEX IF NOT EXISTS idx_airports_icao ON airports(icao_code);
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign ON transceivers(callsign);
CREATE INDEX IF NOT EXISTS idx_transceivers_timestamp ON transceivers(timestamp);

-- Create triggers for updated_at columns
CREATE TRIGGER update_controllers_updated_at 
    BEFORE UPDATE ON controllers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- CREATE TRIGGER update_sectors_updated_at -- REMOVED - table removed

CREATE TRIGGER update_flights_updated_at 
    BEFORE UPDATE ON flights 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();



-- REMOVED: Traffic Analysis Service - Phase 3
-- CREATE TRIGGER update_traffic_movements_updated_at ON traffic_movements -- REMOVED

-- CREATE TRIGGER update_airport_config_updated_at -- REMOVED - table removed



-- CREATE TRIGGER update_movement_detection_config_updated_at -- REMOVED - table removed



CREATE TRIGGER update_transceivers_updated_at 
    BEFORE UPDATE ON transceivers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();



-- Insert default movement detection configuration -- REMOVED - table removed
-- All INSERT statements for movement_detection_config removed



-- Add comments for documentation
COMMENT ON COLUMN controllers.visual_range IS 'Visual range in nautical miles from VATSIM API';
COMMENT ON COLUMN controllers.text_atis IS 'ATIS text information from VATSIM API';

COMMENT ON COLUMN flights.cid IS 'VATSIM user ID from API';
COMMENT ON COLUMN flights.name IS 'Pilot name from VATSIM API';
COMMENT ON COLUMN flights.server IS 'Network server from VATSIM API';
COMMENT ON COLUMN flights.pilot_rating IS 'Pilot rating from VATSIM API';
COMMENT ON COLUMN flights.military_rating IS 'Military rating from VATSIM API';
COMMENT ON COLUMN flights.latitude IS 'Position latitude from VATSIM API';
COMMENT ON COLUMN flights.longitude IS 'Position longitude from VATSIM API';
COMMENT ON COLUMN flights.groundspeed IS 'Ground speed from VATSIM API';
COMMENT ON COLUMN flights.transponder IS 'Transponder code from VATSIM API';
COMMENT ON COLUMN flights.qnh_i_hg IS 'QNH in inches Hg from VATSIM API';
COMMENT ON COLUMN flights.qnh_mb IS 'QNH in millibars from VATSIM API';
COMMENT ON COLUMN flights.logon_time IS 'When pilot connected from VATSIM API';
COMMENT ON COLUMN flights.last_updated_api IS 'API last_updated timestamp from VATSIM API';
COMMENT ON COLUMN flights.flight_rules IS 'IFR/VFR from VATSIM API flight plan';
COMMENT ON COLUMN flights.aircraft_faa IS 'FAA aircraft code from VATSIM API flight plan';
COMMENT ON COLUMN flights.aircraft_short IS 'Short aircraft code from VATSIM API flight plan';
COMMENT ON COLUMN flights.alternate IS 'Alternate airport from VATSIM API flight plan';
COMMENT ON COLUMN flights.cruise_tas IS 'True airspeed from VATSIM API flight plan';
COMMENT ON COLUMN flights.planned_altitude IS 'Planned cruise altitude from VATSIM API flight plan';
COMMENT ON COLUMN flights.deptime IS 'Departure time from VATSIM API flight plan';
COMMENT ON COLUMN flights.enroute_time IS 'Enroute time from VATSIM API flight plan';
COMMENT ON COLUMN flights.fuel_time IS 'Fuel time from VATSIM API flight plan';
COMMENT ON COLUMN flights.remarks IS 'Flight plan remarks from VATSIM API';
COMMENT ON COLUMN flights.revision_id IS 'Flight plan revision from VATSIM API';
COMMENT ON COLUMN flights.assigned_transponder IS 'Assigned transponder from VATSIM API flight plan';



-- Verify all tables were created successfully
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_schema = 'public' 
    AND table_name IN (
        'controllers', 'sectors', 'flights',
        -- 'traffic_movements', -- REMOVED: Traffic Analysis Service - Phase 3
        'airport_config', 'airports', 'movement_detection_config', 
        'system_config', 'transceivers'
    )
ORDER BY table_name, ordinal_position; 