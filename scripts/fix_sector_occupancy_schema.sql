-- Migration script to fix flight_sector_occupancy table schema
-- This script updates the table to use 'callsign' instead of 'flight_id'

-- Drop existing table if it exists
DROP TABLE IF EXISTS flight_sector_occupancy CASCADE;

-- Recreate table with correct column names
CREATE TABLE flight_sector_occupancy (
    id BIGSERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,                    -- Flight callsign (was flight_id)
    sector_name VARCHAR(10) NOT NULL,                 -- Name of the airspace sector
    entry_timestamp TIMESTAMPTZ NOT NULL,             -- When flight entered sector
    exit_timestamp TIMESTAMPTZ,                       -- When flight exited sector (nullable)
    duration_seconds INTEGER DEFAULT 0,               -- Time spent in sector (calculated)
    entry_lat NUMERIC(10,8) NOT NULL,                -- Entry latitude
    entry_lon NUMERIC(11,8) NOT NULL,                -- Entry longitude
    exit_lat NUMERIC(10,8),                          -- Exit latitude (nullable)
    exit_lon NUMERIC(11,8),                          -- Exit longitude (nullable)
    created_at TIMESTAMPTZ DEFAULT NOW(),             -- Record creation timestamp
    entry_altitude INTEGER,                           -- Entry altitude in feet
    exit_altitude INTEGER                             -- Exit altitude in feet
);

-- Create indexes for performance
CREATE INDEX idx_flight_sector_occupancy_callsign ON flight_sector_occupancy(callsign);
CREATE INDEX idx_flight_sector_occupancy_entry_timestamp ON flight_sector_occupancy(entry_timestamp);
CREATE INDEX idx_flight_sector_occupancy_sector_name ON flight_sector_occupancy(sector_name);

-- Add comments for documentation
COMMENT ON TABLE flight_sector_occupancy IS 'Tracks aircraft entry/exit from Australian airspace sectors for real-time monitoring';
COMMENT ON COLUMN flight_sector_occupancy.callsign IS 'Flight callsign (e.g., QFA123, PHENX88)';
COMMENT ON COLUMN flight_sector_occupancy.sector_name IS 'Australian airspace sector identifier (e.g., SYA, BLA, WOL)';
COMMENT ON COLUMN flight_sector_occupancy.entry_altitude IS 'Altitude in feet when entering sector';
COMMENT ON COLUMN flight_sector_occupancy.exit_altitude IS 'Altitude in feet when exiting sector';
