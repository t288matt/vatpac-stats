-- Migration 021: Create Flight Summary Table System
-- Purpose: Implement flight summary tables to reduce storage requirements
-- Date: January 2025
-- Status: Ready for Implementation

-- 1. Create flight_summaries table (completed flight summaries)
CREATE TABLE IF NOT EXISTS flight_summaries (
    id BIGSERIAL PRIMARY KEY,
    
    -- Core Identification Fields
    callsign VARCHAR(50) NOT NULL,
    aircraft_type VARCHAR(20),
    departure VARCHAR(10),
    arrival VARCHAR(10),
    logon_time TIMESTAMP WITH TIME ZONE,
    
    -- Flight Plan Fields
    route TEXT,
    flight_rules VARCHAR(10),
    aircraft_faa VARCHAR(20),
    planned_altitude VARCHAR(10),
    aircraft_short VARCHAR(20),
    
    -- Pilot Information Fields
    cid INTEGER,
    name VARCHAR(100),
    server VARCHAR(50),
    pilot_rating INTEGER,
    military_rating INTEGER,
    
    -- Controller Interaction Fields (JSONB for flexibility)
    controller_callsigns JSONB,
    controller_time_percentage DECIMAL(5,1),
    time_online_minutes INTEGER,
    
    -- Sector Occupancy Fields (JSONB for flexibility)
    primary_enroute_sector VARCHAR(10),
    total_enroute_sectors INTEGER,
    total_enroute_time_minutes INTEGER,
    sector_breakdown JSONB,
    
    -- Metadata Fields
    completion_time TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create flights_archive table (detailed archived records)
CREATE TABLE IF NOT EXISTS flights_archive (
    id BIGSERIAL PRIMARY KEY,
    
    -- Copy all fields from existing flights table
    callsign VARCHAR(50) NOT NULL,
    aircraft_type VARCHAR(20),
    departure VARCHAR(10),
    arrival VARCHAR(10),
    logon_time TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE,
    position_lat DECIMAL(10, 8),
    position_lon DECIMAL(11, 8),
    altitude INTEGER,
    groundspeed INTEGER,
    heading INTEGER,
    vertical_speed INTEGER,
    squawk INTEGER,
    flight_plan TEXT,
    flight_rules VARCHAR(10),
    aircraft_faa VARCHAR(20),
    planned_altitude VARCHAR(10),
    aircraft_short VARCHAR(20),
    cid INTEGER,
    name VARCHAR(100),
    server VARCHAR(50),
    pilot_rating INTEGER,
    military_rating INTEGER,
    transponder_height INTEGER,
    
    -- Archive metadata
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    original_flight_id BIGINT -- Reference to original flight record
);

-- 3. Create flight_sector_occupancy table (real-time sector tracking)
CREATE TABLE IF NOT EXISTS flight_sector_occupancy (
    id BIGSERIAL PRIMARY KEY,
    flight_id VARCHAR(50) NOT NULL,
    sector_name VARCHAR(10) NOT NULL,
    entry_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_timestamp TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    entry_lat DECIMAL(10, 8) NOT NULL,
    entry_lon DECIMAL(11, 8) NOT NULL,
    exit_lat DECIMAL(10, 8),
    exit_lon DECIMAL(11, 8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign ON flight_summaries(callsign);
CREATE INDEX IF NOT EXISTS idx_flight_summaries_completion_time ON flight_summaries(completion_time);
CREATE INDEX IF NOT EXISTS idx_flight_summaries_logon_time ON flight_summaries(logon_time);

CREATE INDEX IF NOT EXISTS idx_flights_archive_callsign ON flights_archive(callsign);
CREATE INDEX IF NOT EXISTS idx_flights_archive_logon_time ON flights_archive(logon_time);
CREATE INDEX IF NOT EXISTS idx_flights_archive_archived_at ON flights_archive(archived_at);

CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_flight_id ON flight_sector_occupancy(flight_id);
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_sector_name ON flight_sector_occupancy(sector_name);
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_entry_time ON flight_sector_occupancy(entry_timestamp);

-- 5. Add comments for documentation
COMMENT ON TABLE flight_summaries IS 'Completed flight summaries with aggregated data for storage optimization';
COMMENT ON TABLE flights_archive IS 'Archived detailed flight records for completed flights';
COMMENT ON TABLE flight_sector_occupancy IS 'Real-time tracking of flight sector entry/exit for occupancy analysis';

-- 6. Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 7. Apply trigger to flight_summaries
CREATE TRIGGER update_flight_summaries_updated_at 
    BEFORE UPDATE ON flight_summaries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Migration complete
-- Next step: Implement flight completion detection and summarization logic
