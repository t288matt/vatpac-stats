-- Comprehensive Database Initialization Script
-- This script creates all tables with all required fields for the VATSIM data collection system
-- Run automatically when PostgreSQL container starts for the first time
-- 
-- VATSIM API Field Mapping - EXACT 1:1 mapping with API field names:
-- - API "cid" → cid (Controller ID from VATSIM)
-- - API "name" → name (Controller name from VATSIM)  
-- - API "rating" → rating (Controller rating from VATSIM)
-- - API "facility" → facility (Facility type from VATSIM)
-- - API "server" → server (Network server from VATSIM)
-- - API "last_updated" → last_updated (Last update timestamp from VATSIM)
-- - API "logon_time" → logon_time (Controller logon time from VATSIM)

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

-- Controllers table with EXACT VATSIM API field mapping
CREATE TABLE IF NOT EXISTS controllers (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) UNIQUE NOT NULL,
    frequency VARCHAR(20),
    cid INTEGER,                    -- From API "cid" - Controller ID
    name VARCHAR(100),              -- From API "name" - Controller name
    rating INTEGER,                 -- From API "rating" - Controller rating
    facility INTEGER,               -- From API "facility" - Facility type
    visual_range INTEGER,           -- From API "visual_range" - Visual range in NM
    text_atis TEXT,                 -- From API "text_atis" - ATIS information
    server VARCHAR(50),             -- From API "server" - Network server
    last_updated TIMESTAMP WITH TIME ZONE,  -- From API "last_updated"
    logon_time TIMESTAMP WITH TIME ZONE,    -- From API "logon_time"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Flights table with optimized VATSIM API field mapping
CREATE TABLE IF NOT EXISTS flights (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    aircraft_type VARCHAR(20),
    
    -- Flight tracking fields - using VATSIM API field names directly
    latitude DOUBLE PRECISION,      -- From API "latitude" - Position latitude
    longitude DOUBLE PRECISION,     -- From API "longitude" - Position longitude
    altitude INTEGER,               -- From API "altitude" - Current altitude
    heading INTEGER,                -- From API "heading" - Current heading
    groundspeed INTEGER,            -- From API "groundspeed" - Current ground speed
    
    -- Flight plan fields - simplified to essential only
    departure VARCHAR(10),          -- From API flight plan
    arrival VARCHAR(10),            -- From API flight plan
    route TEXT,                     -- From API flight plan
    
    -- Additional flight plan fields from VATSIM API
    flight_rules VARCHAR(10),       -- IFR/VFR from flight_plan.flight_rules
    aircraft_faa VARCHAR(20),       -- FAA aircraft code from flight_plan.aircraft_faa
    alternate VARCHAR(10),          -- Alternate airport from flight_plan.alternate
    cruise_tas VARCHAR(10),         -- True airspeed from flight_plan.cruise_tas
    planned_altitude VARCHAR(10),   -- Planned cruise altitude from flight_plan.altitude
    deptime VARCHAR(10),            -- Departure time from flight_plan.deptime
    enroute_time VARCHAR(10),       -- Enroute time from flight_plan.enroute_time
    fuel_time VARCHAR(10),          -- Fuel time from flight_plan.fuel_time
    remarks TEXT,                   -- Flight plan remarks from flight_plan.remarks
    aircraft_short VARCHAR(20),     -- Short aircraft code from flight_plan.aircraft_short
    revision_id INTEGER,            -- Flight plan revision from flight_plan.revision_id
    assigned_transponder VARCHAR(10), -- Assigned transponder from flight_plan.assigned_transponder
    
    -- Timestamps
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- VATSIM API fields - 1:1 mapping with API field names
    cid INTEGER,                    -- From API "cid" - VATSIM user ID
    name VARCHAR(100),              -- From API "name" - Pilot name
    server VARCHAR(50),             -- From API "server" - Network server
    pilot_rating INTEGER,           -- From API "pilot_rating" - Pilot rating
    military_rating INTEGER,        -- From API "military_rating" - Military rating
    transponder VARCHAR(10),        -- From API "transponder" - Transponder code
    qnh_i_hg DOUBLE PRECISION,      -- QNH pressure in inches Hg from VATSIM API
    qnh_mb INTEGER,                 -- QNH pressure in millibars from VATSIM API
    logon_time TIMESTAMP WITH TIME ZONE,    -- From API "logon_time"
    last_updated_api TIMESTAMP WITH TIME ZONE,  -- From API "last_updated"
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transceivers table for radio frequency and position data
CREATE TABLE IF NOT EXISTS transceivers (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    transceiver_id INTEGER NOT NULL,  -- ID from VATSIM API
    frequency BIGINT NOT NULL,        -- Frequency in Hz
    position_lat DOUBLE PRECISION,    -- Position latitude
    position_lon DOUBLE PRECISION,    -- Position longitude
    height_msl DOUBLE PRECISION,      -- Height above mean sea level in meters from VATSIM API
    height_agl DOUBLE PRECISION,      -- Height above ground level in meters from VATSIM API
    entity_type VARCHAR(20) NOT NULL, -- 'flight' or 'atc'
    entity_id INTEGER,                -- Foreign key to flights.id or controllers.id
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance (matching SQLAlchemy model definitions)
-- Controllers indexes
CREATE INDEX IF NOT EXISTS idx_controllers_callsign ON controllers(callsign);
CREATE INDEX IF NOT EXISTS idx_controllers_cid ON controllers(cid);
CREATE INDEX IF NOT EXISTS idx_controllers_cid_rating ON controllers(cid, rating);
CREATE INDEX IF NOT EXISTS idx_controllers_facility_server ON controllers(facility, server);
CREATE INDEX IF NOT EXISTS idx_controllers_last_updated ON controllers(last_updated);

-- Flights indexes
CREATE INDEX IF NOT EXISTS idx_flights_callsign ON flights(callsign);
CREATE INDEX IF NOT EXISTS idx_flights_callsign_status ON flights(callsign, last_updated);
CREATE INDEX IF NOT EXISTS idx_flights_position ON flights(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_flights_departure_arrival ON flights(departure, arrival);
CREATE INDEX IF NOT EXISTS idx_flights_cid_server ON flights(cid, server);
CREATE INDEX IF NOT EXISTS idx_flights_altitude ON flights(altitude);
CREATE INDEX IF NOT EXISTS idx_flights_flight_rules ON flights(flight_rules);
CREATE INDEX IF NOT EXISTS idx_flights_planned_altitude ON flights(planned_altitude);
CREATE INDEX IF NOT EXISTS idx_flights_aircraft_short ON flights(aircraft_short);
CREATE INDEX IF NOT EXISTS idx_flights_revision_id ON flights(revision_id);

-- Transceivers indexes
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign ON transceivers(callsign);
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign_timestamp ON transceivers(callsign, timestamp);
CREATE INDEX IF NOT EXISTS idx_transceivers_frequency ON transceivers(frequency);
CREATE INDEX IF NOT EXISTS idx_transceivers_entity ON transceivers(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_transceivers_position ON transceivers(position_lat, position_lon);

-- Create triggers for updated_at columns
CREATE TRIGGER update_controllers_updated_at 
    BEFORE UPDATE ON controllers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_flights_updated_at 
    BEFORE UPDATE ON flights 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transceivers_updated_at 
    BEFORE UPDATE ON transceivers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add constraints matching SQLAlchemy model definitions
-- Controllers constraints
ALTER TABLE controllers ADD CONSTRAINT IF NOT EXISTS valid_rating 
    CHECK (rating >= -1 AND rating <= 12);
ALTER TABLE controllers ADD CONSTRAINT IF NOT EXISTS valid_facility 
    CHECK (facility >= 0 AND facility <= 6);
ALTER TABLE controllers ADD CONSTRAINT IF NOT EXISTS valid_visual_range 
    CHECK (visual_range >= 0);

-- Flights constraints
ALTER TABLE flights ADD CONSTRAINT IF NOT EXISTS valid_latitude 
    CHECK (latitude >= -90 AND latitude <= 90);
ALTER TABLE flights ADD CONSTRAINT IF NOT EXISTS valid_longitude 
    CHECK (longitude >= -180 AND longitude <= 180);
ALTER TABLE flights ADD CONSTRAINT IF NOT EXISTS valid_altitude 
    CHECK (altitude >= 0);
ALTER TABLE flights ADD CONSTRAINT IF NOT EXISTS valid_heading 
    CHECK (heading >= 0 AND heading <= 360);
ALTER TABLE flights ADD CONSTRAINT IF NOT EXISTS valid_groundspeed 
    CHECK (groundspeed >= 0);
ALTER TABLE flights ADD CONSTRAINT IF NOT EXISTS valid_pilot_rating 
    CHECK (pilot_rating >= 0 AND pilot_rating <= 63);

-- Transceivers constraints
ALTER TABLE transceivers ADD CONSTRAINT IF NOT EXISTS valid_frequency 
    CHECK (frequency > 0);
ALTER TABLE transceivers ADD CONSTRAINT IF NOT EXISTS valid_transceiver_latitude 
    CHECK (position_lat >= -90 AND position_lat <= 90);
ALTER TABLE transceivers ADD CONSTRAINT IF NOT EXISTS valid_transceiver_longitude 
    CHECK (position_lon >= -180 AND position_lon <= 180);
ALTER TABLE transceivers ADD CONSTRAINT IF NOT EXISTS valid_entity_type 
    CHECK (entity_type IN ('flight', 'atc'));

-- Add comments for documentation
COMMENT ON COLUMN controllers.cid IS 'Controller ID from VATSIM API "cid" field';
COMMENT ON COLUMN controllers.name IS 'Controller name from VATSIM API "name" field';
COMMENT ON COLUMN controllers.rating IS 'Controller rating from VATSIM API "rating" field';
COMMENT ON COLUMN controllers.facility IS 'Facility type from VATSIM API "facility" field';
COMMENT ON COLUMN controllers.server IS 'Network server from VATSIM API "server" field';
COMMENT ON COLUMN controllers.last_updated IS 'Last update timestamp from VATSIM API "last_updated" field';
COMMENT ON COLUMN controllers.logon_time IS 'Controller logon time from VATSIM API "logon_time" field';
COMMENT ON COLUMN controllers.visual_range IS 'Visual range in nautical miles from VATSIM API "visual_range" field';
COMMENT ON COLUMN controllers.text_atis IS 'ATIS text information from VATSIM API "text_atis" field';

COMMENT ON COLUMN flights.cid IS 'VATSIM user ID from API "cid" field';
COMMENT ON COLUMN flights.name IS 'Pilot name from VATSIM API "name" field';
COMMENT ON COLUMN flights.server IS 'Network server from VATSIM API "server" field';
COMMENT ON COLUMN flights.pilot_rating IS 'Pilot rating from VATSIM API "pilot_rating" field';
COMMENT ON COLUMN flights.military_rating IS 'Military rating from VATSIM API "military_rating" field';
COMMENT ON COLUMN flights.latitude IS 'Position latitude from VATSIM API "latitude" field';
COMMENT ON COLUMN flights.longitude IS 'Position longitude from VATSIM API "longitude" field';
COMMENT ON COLUMN flights.altitude IS 'Current altitude from VATSIM API "altitude" field';
COMMENT ON COLUMN flights.heading IS 'Current heading from VATSIM API "heading" field';
COMMENT ON COLUMN flights.groundspeed IS 'Ground speed from VATSIM API "groundspeed" field';
COMMENT ON COLUMN flights.transponder IS 'Transponder code from VATSIM API "transponder" field';
COMMENT ON COLUMN flights.logon_time IS 'When pilot connected from VATSIM API "logon_time" field';
COMMENT ON COLUMN flights.last_updated_api IS 'API last_updated timestamp from VATSIM API "last_updated" field';
COMMENT ON COLUMN flights.flight_rules IS 'IFR/VFR from VATSIM API flight_plan.flight_rules field';
COMMENT ON COLUMN flights.aircraft_faa IS 'FAA aircraft code from VATSIM API flight_plan.aircraft_faa field';
COMMENT ON COLUMN flights.alternate IS 'Alternate airport from VATSIM API flight_plan.alternate field';
COMMENT ON COLUMN flights.cruise_tas IS 'True airspeed from VATSIM API flight_plan.cruise_tas field';
COMMENT ON COLUMN flights.planned_altitude IS 'Planned cruise altitude from VATSIM API flight_plan.altitude field';
COMMENT ON COLUMN flights.deptime IS 'Departure time from VATSIM API flight_plan.deptime field';
COMMENT ON COLUMN flights.enroute_time IS 'Enroute time from VATSIM API flight_plan.enroute_time field';
COMMENT ON COLUMN flights.fuel_time IS 'Fuel time from VATSIM API flight_plan.fuel_time field';
COMMENT ON COLUMN flights.remarks IS 'Flight plan remarks from VATSIM API flight_plan.remarks field';
COMMENT ON COLUMN flights.aircraft_short IS 'Short aircraft code from VATSIM API flight_plan.aircraft_short field';
COMMENT ON COLUMN flights.revision_id IS 'Flight plan revision from VATSIM API flight_plan.revision_id field';
COMMENT ON COLUMN flights.assigned_transponder IS 'Assigned transponder from VATSIM API flight_plan.assigned_transponder field';
COMMENT ON COLUMN flights.qnh_i_hg IS 'QNH pressure in inches Hg from VATSIM API qnh_i_hg field';
COMMENT ON COLUMN flights.qnh_mb IS 'QNH pressure in millibars from VATSIM API qnh_mb field';

-- Verify all tables were created successfully
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
    AND table_name IN ('controllers', 'flights', 'transceivers')
ORDER BY table_name, ordinal_position; 