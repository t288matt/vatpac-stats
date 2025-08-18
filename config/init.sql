-- Comprehensive Database Initialization Script
-- This script creates all tables with all required fields for the VATSIM data collection system
-- Run automatically when PostgreSQL container starts for the first time
-- 
-- IMPORTANT: This script includes the flight_sector_occupancy table with altitude fields
-- required for real-time sector tracking functionality.
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
    callsign VARCHAR(50) NOT NULL,
    frequency VARCHAR(20),
    cid INTEGER,                    -- From API "cid" - Controller ID
    name VARCHAR(100),              -- From API "name" - Controller name
    rating INTEGER,                 -- From API "rating" - Controller rating
    facility INTEGER,               -- From API "facility" - Facility type
    visual_range INTEGER,           -- From API "visual_range" - Visual range in NM
    text_atis TEXT,                 -- From API "text_atis" - ATIS information
    server VARCHAR(50),             -- From API "server" - Network server
    last_updated TIMESTAMP(0) WITH TIME ZONE,  -- From API "last_updated" - UTC, no subseconds
    logon_time TIMESTAMP(0) WITH TIME ZONE,    -- From API "logon_time" - UTC, no subseconds
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW()
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
    aircraft_short VARCHAR(20),     -- Short aircraft code from flight_plan.aircraft_short
    alternate VARCHAR(10),          -- Alternate airport from flight_plan.alternate
    cruise_tas VARCHAR(10),         -- True airspeed from flight_plan.cruise_tas
    planned_altitude VARCHAR(10),   -- Planned cruise altitude from flight_plan.altitude
    deptime VARCHAR(10),            -- Departure time from flight_plan.deptime
    enroute_time VARCHAR(10),       -- Enroute time from flight_plan.enroute_time
    fuel_time VARCHAR(10),          -- Fuel time from flight_plan.fuel_time
    remarks TEXT,                   -- Flight plan remarks from flight_plan.remarks
    
    -- Additional VATSIM API fields
    revision_id INTEGER,            -- Flight plan revision from flight_plan.revision_id
    assigned_transponder VARCHAR(10), -- Assigned transponder from flight_plan.assigned_transponder
    
    -- Timestamps
    last_updated TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),  -- UTC, no subseconds
    
    -- VATSIM API fields - 1:1 mapping with API field names
    cid INTEGER,                    -- From API "cid" - VATSIM user ID
    name VARCHAR(100),              -- From API "name" - Pilot name
    server VARCHAR(50),             -- From API "server" - Network server
    pilot_rating INTEGER,           -- From API "pilot_rating" - Pilot rating
    military_rating INTEGER,        -- From API "military_rating" - Military rating
    transponder VARCHAR(10),        -- From API "transponder" - Transponder code
    qnh_i_hg DOUBLE PRECISION,      -- QNH pressure in inches Hg from VATSIM API
    qnh_mb INTEGER,                 -- QNH pressure in millibars from VATSIM API
    logon_time TIMESTAMP(0) WITH TIME ZONE,    -- From API "logon_time" - UTC, no subseconds
    last_updated_api TIMESTAMP(0) WITH TIME ZONE,  -- From API "last_updated" - UTC, no subseconds
    
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW()
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance (optimized for production queries)
-- Controllers indexes
CREATE INDEX IF NOT EXISTS idx_controllers_callsign ON controllers(callsign);
CREATE INDEX IF NOT EXISTS idx_controllers_cid ON controllers(cid);
CREATE INDEX IF NOT EXISTS idx_controllers_cid_rating ON controllers(cid, rating);
CREATE INDEX IF NOT EXISTS idx_controllers_facility_server ON controllers(facility, server);
CREATE INDEX IF NOT EXISTS idx_controllers_last_updated ON controllers(last_updated);
CREATE INDEX IF NOT EXISTS idx_controllers_rating_last_updated ON controllers(rating, last_updated);

-- ATC Detection Performance Indexes for controllers
CREATE INDEX IF NOT EXISTS idx_controllers_callsign_facility ON controllers(callsign, facility);

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

-- ATC Detection Performance Indexes for flights
CREATE INDEX IF NOT EXISTS idx_flights_callsign_departure_arrival ON flights(callsign, departure, arrival);
CREATE INDEX IF NOT EXISTS idx_flights_callsign_logon ON flights(callsign, logon_time);

-- Transceivers indexes (optimized for frequency-based queries)
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign ON transceivers(callsign);
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign_timestamp ON transceivers(callsign, timestamp);
CREATE INDEX IF NOT EXISTS idx_transceivers_frequency ON transceivers(frequency);
CREATE INDEX IF NOT EXISTS idx_transceivers_entity ON transceivers(entity_type, entity_id);

-- ATC Detection Performance Indexes for transceivers
CREATE INDEX IF NOT EXISTS idx_transceivers_entity_type_callsign ON transceivers(entity_type, callsign);
CREATE INDEX IF NOT EXISTS idx_transceivers_entity_type_timestamp ON transceivers(entity_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_transceivers_atc_detection ON transceivers(entity_type, callsign, timestamp, frequency, position_lat, position_lon);

-- Performance-optimized indexes for controller flight counting queries
CREATE INDEX IF NOT EXISTS idx_transceivers_flight_frequency_callsign ON transceivers(entity_type, frequency, callsign) WHERE entity_type = 'flight';

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

-- Add constraints matching SQLAlchemy model definitions with error handling
DO $$
BEGIN
    -- Controllers constraints
    BEGIN
        ALTER TABLE controllers ADD CONSTRAINT valid_rating 
            CHECK (rating >= -1 AND rating <= 12);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;
    
    BEGIN
        ALTER TABLE controllers ADD CONSTRAINT valid_facility 
            CHECK (facility >= 0 AND facility <= 6);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;
    
    BEGIN
        ALTER TABLE controllers ADD CONSTRAINT valid_visual_range 
            CHECK (visual_range >= 0);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;

    -- Flights constraints
    BEGIN
        ALTER TABLE flights ADD CONSTRAINT valid_latitude 
            CHECK (latitude >= -90 AND latitude <= 90);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;
    
    BEGIN
        ALTER TABLE flights ADD CONSTRAINT valid_longitude 
            CHECK (longitude >= -180 AND longitude <= 180);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;
    
    BEGIN
        ALTER TABLE flights ADD CONSTRAINT valid_altitude 
            CHECK (altitude >= -1000 AND altitude <= 100000);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;
    
    BEGIN
        ALTER TABLE flights ADD CONSTRAINT valid_heading 
            CHECK (heading >= 0 AND heading <= 360);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;
    
    BEGIN
        ALTER TABLE flights ADD CONSTRAINT valid_groundspeed 
            CHECK (groundspeed >= 0);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;
    
    BEGIN
        ALTER TABLE flights ADD CONSTRAINT valid_pilot_rating 
            CHECK (pilot_rating >= 0 AND pilot_rating <= 63);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;

    -- Transceivers constraints
    BEGIN
        ALTER TABLE transceivers ADD CONSTRAINT valid_frequency 
            CHECK (frequency >= 0);
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;
    
    BEGIN
        ALTER TABLE transceivers ADD CONSTRAINT valid_entity_type 
            CHECK (entity_type IN ('flight', 'atc'));
    EXCEPTION WHEN duplicate_object THEN
        -- Constraint already exists, skip
    END;
END $$;

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
COMMENT ON COLUMN flights.altitude IS 'Current altitude from VATSIM API "altitude" field (allows -1000 to 100000 for below ground level and extreme altitudes)';
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

-- Flight Summaries table for completed flight data
CREATE TABLE IF NOT EXISTS flight_summaries (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    aircraft_type VARCHAR(20),
    departure VARCHAR(10),
    arrival VARCHAR(10),
    logon_time TIMESTAMP(0) WITH TIME ZONE,
    route TEXT,
    flight_rules VARCHAR(10),
    aircraft_faa VARCHAR(20),
    planned_altitude VARCHAR(10),
    aircraft_short VARCHAR(20),
    cid INTEGER,
    name VARCHAR(100),
    server VARCHAR(50),
    pilot_rating INTEGER,
    military_rating INTEGER,
    controller_callsigns JSONB,  -- JSON array of controller callsigns
    controller_time_percentage DECIMAL(5,2),  -- Percentage of time with ATC contact
    time_online_minutes INTEGER,  -- Total time online in minutes
    primary_enroute_sector VARCHAR(50),  -- Primary sector flown through
    total_enroute_sectors INTEGER,  -- Total number of sectors flown through
    total_enroute_time_minutes INTEGER,  -- Total time in enroute sectors
    sector_breakdown JSONB,  -- Detailed sector breakdown data
    completion_time TIMESTAMP(0) WITH TIME ZONE,  -- When flight completed
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW()
);

-- Flights Archive table for detailed historical records
CREATE TABLE IF NOT EXISTS flights_archive (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    aircraft_type VARCHAR(20),
    departure VARCHAR(10),
    arrival VARCHAR(10),
    logon_time TIMESTAMP(0) WITH TIME ZONE,
    route TEXT,
    flight_rules VARCHAR(10),
    aircraft_faa VARCHAR(20),
    planned_altitude VARCHAR(10),
    aircraft_short VARCHAR(20),
    cid INTEGER,
    name VARCHAR(100),
    server VARCHAR(50),
    pilot_rating INTEGER,
    military_rating INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    altitude INTEGER,
    groundspeed INTEGER,
    heading INTEGER,
    last_updated TIMESTAMP(0) WITH TIME ZONE,
    created_at TIMESTAMP(0) WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for flight_summaries table
CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign ON flight_summaries(callsign);
CREATE INDEX IF NOT EXISTS idx_flight_summaries_completion_time ON flight_summaries(completion_time);
CREATE INDEX IF NOT EXISTS idx_flight_summaries_flight_rules ON flight_summaries(flight_rules);
CREATE INDEX IF NOT EXISTS idx_flight_summaries_controller_time ON flight_summaries(controller_time_percentage);

-- Create indexes for flights_archive table
CREATE INDEX IF NOT EXISTS idx_flights_archive_callsign ON flights_archive(callsign);
CREATE INDEX IF NOT EXISTS idx_flights_archive_logon_time ON flights_archive(logon_time);
CREATE INDEX IF NOT EXISTS idx_flights_archive_last_updated ON flights_archive(last_updated);

-- Create triggers for updated_at columns on new tables
CREATE TRIGGER update_flight_summaries_updated_at 
    BEFORE UPDATE ON flight_summaries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Flight Sector Occupancy table for tracking sector entry/exit
CREATE TABLE IF NOT EXISTS flight_sector_occupancy (
    id BIGSERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    sector_name VARCHAR(10) NOT NULL,
    entry_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_timestamp TIMESTAMP WITH TIME ZONE,     -- NULL until flight exits sector
    duration_seconds INTEGER DEFAULT 0,          -- 0 until flight exits sector
    entry_lat DECIMAL(10, 8) NOT NULL,
    entry_lon DECIMAL(11, 8) NOT NULL,
    exit_lat DECIMAL(10, 8),                    -- NULL until flight exits sector
    exit_lon DECIMAL(11, 8),                    -- NULL until flight exits sector
    entry_altitude INTEGER,                      -- Altitude when entering sector (REQUIRED for sector tracking)
    exit_altitude INTEGER,                       -- Altitude when exiting sector (REQUIRED for sector tracking)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for flight_sector_occupancy table
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_callsign ON flight_sector_occupancy(callsign);
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_sector_name ON flight_sector_occupancy(sector_name);
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_entry_timestamp ON flight_sector_occupancy(entry_timestamp);

-- Verify all tables were created successfully
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
    AND table_name IN ('controllers', 'flights', 'transceivers', 'flight_summaries', 'flights_archive', 'flight_sector_occupancy')
ORDER BY table_name, ordinal_position;

-- ============================================================================
-- MATERIALIZED VIEW OPTIMIZATION REMOVED
-- ============================================================================
-- The controller_weekly_stats materialized view and related objects have been
-- removed to simplify the database schema.
-- 
-- If you need to restore this optimization in the future, see:
-- docs/MATERIALIZED_VIEW_OPTIMIZATION.md
-- ============================================================================ 