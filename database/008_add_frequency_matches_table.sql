-- Migration: Add frequency_matches table
-- Description: Creates table for storing frequency matching events between pilots and ATC controllers
-- Date: 2025-01-27

-- Create frequency_matches table
CREATE TABLE IF NOT EXISTS frequency_matches (
    id SERIAL PRIMARY KEY,
    pilot_callsign VARCHAR(50) NOT NULL,
    controller_callsign VARCHAR(50) NOT NULL,
    frequency INTEGER NOT NULL,
    pilot_lat FLOAT,
    pilot_lon FLOAT,
    controller_lat FLOAT,
    controller_lon FLOAT,
    distance_nm FLOAT,
    match_timestamp TIMESTAMP NOT NULL,
    duration_seconds INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    match_confidence FLOAT DEFAULT 1.0,
    communication_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_frequency_matches_pilot_callsign ON frequency_matches(pilot_callsign);
CREATE INDEX IF NOT EXISTS idx_frequency_matches_controller_callsign ON frequency_matches(controller_callsign);
CREATE INDEX IF NOT EXISTS idx_frequency_matches_frequency ON frequency_matches(frequency);
CREATE INDEX IF NOT EXISTS idx_frequency_matches_match_timestamp ON frequency_matches(match_timestamp);
CREATE INDEX IF NOT EXISTS idx_frequency_matches_is_active ON frequency_matches(is_active);
CREATE INDEX IF NOT EXISTS idx_frequency_matches_communication_type ON frequency_matches(communication_type);
CREATE INDEX IF NOT EXISTS idx_frequency_matches_distance ON frequency_matches(distance_nm);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_frequency_matches_pilot_controller ON frequency_matches(pilot_callsign, controller_callsign);
CREATE INDEX IF NOT EXISTS idx_frequency_matches_frequency_timestamp ON frequency_matches(frequency, match_timestamp);
CREATE INDEX IF NOT EXISTS idx_frequency_matches_active_timestamp ON frequency_matches(is_active, match_timestamp);

-- Add check constraint for communication_type
ALTER TABLE frequency_matches ADD CONSTRAINT check_communication_type 
CHECK (communication_type IN ('approach', 'departure', 'enroute', 'ground', 'tower', 'hf_enroute', 'unknown'));

-- Add check constraint for match_confidence
ALTER TABLE frequency_matches ADD CONSTRAINT check_match_confidence 
CHECK (match_confidence >= 0.0 AND match_confidence <= 1.0);

-- Add check constraint for frequency (valid VHF/HF ranges)
ALTER TABLE frequency_matches ADD CONSTRAINT check_frequency 
CHECK (frequency >= 20000000 AND frequency <= 136000000);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_frequency_matches_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_frequency_matches_updated_at
    BEFORE UPDATE ON frequency_matches
    FOR EACH ROW
    EXECUTE FUNCTION update_frequency_matches_updated_at();

-- Add comment to table
COMMENT ON TABLE frequency_matches IS 'Frequency matching events between pilots and ATC controllers for communication analysis';
COMMENT ON COLUMN frequency_matches.pilot_callsign IS 'Pilot callsign (aircraft identifier)';
COMMENT ON COLUMN frequency_matches.controller_callsign IS 'ATC controller callsign';
COMMENT ON COLUMN frequency_matches.frequency IS 'Frequency in Hz';
COMMENT ON COLUMN frequency_matches.distance_nm IS 'Distance between pilot and controller in nautical miles';
COMMENT ON COLUMN frequency_matches.match_timestamp IS 'When the frequency match was detected';
COMMENT ON COLUMN frequency_matches.duration_seconds IS 'Duration of the frequency match in seconds';
COMMENT ON COLUMN frequency_matches.is_active IS 'Whether the frequency match is currently active';
COMMENT ON COLUMN frequency_matches.match_confidence IS 'Confidence score for the frequency match (0.0 to 1.0)';
COMMENT ON COLUMN frequency_matches.communication_type IS 'Type of communication (approach, departure, enroute, ground, tower, hf_enroute, unknown)';
