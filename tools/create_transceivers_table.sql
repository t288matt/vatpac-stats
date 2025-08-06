-- Create transceivers table for VATSIM radio frequency and position data
-- This table stores real-time transceiver information from the VATSIM transceivers API

CREATE TABLE IF NOT EXISTS transceivers (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    transceiver_id INTEGER NOT NULL,
    frequency INTEGER NOT NULL,  -- Frequency in Hz
    position_lat DOUBLE PRECISION,
    position_lon DOUBLE PRECISION,
    height_msl DOUBLE PRECISION,  -- Height above mean sea level in meters
    height_agl DOUBLE PRECISION,  -- Height above ground level in meters
    entity_type VARCHAR(20) NOT NULL,  -- 'flight' or 'atc'
    entity_id INTEGER,  -- Foreign key to flights.id or atc_positions.id
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign_timestamp ON transceivers(callsign, timestamp);
CREATE INDEX IF NOT EXISTS idx_transceivers_entity_type ON transceivers(entity_type);
CREATE INDEX IF NOT EXISTS idx_transceivers_frequency ON transceivers(frequency);
CREATE INDEX IF NOT EXISTS idx_transceivers_timestamp ON transceivers(timestamp);

-- Add comments for documentation
COMMENT ON TABLE transceivers IS 'Stores real-time transceiver data from VATSIM transceivers API';
COMMENT ON COLUMN transceivers.callsign IS 'Aircraft or controller callsign';
COMMENT ON COLUMN transceivers.transceiver_id IS 'Transceiver ID from VATSIM API';
COMMENT ON COLUMN transceivers.frequency IS 'Radio frequency in Hz';
COMMENT ON COLUMN transceivers.position_lat IS 'Latitude position of transceiver';
COMMENT ON COLUMN transceivers.position_lon IS 'Longitude position of transceiver';
COMMENT ON COLUMN transceivers.height_msl IS 'Height above mean sea level in meters';
COMMENT ON COLUMN transceivers.height_agl IS 'Height above ground level in meters';
COMMENT ON COLUMN transceivers.entity_type IS 'Type of entity: flight or atc';
COMMENT ON COLUMN transceivers.entity_id IS 'Foreign key to flights.id or atc_positions.id';
COMMENT ON COLUMN transceivers.timestamp IS 'Timestamp when data was recorded';

-- Create view for flights with transceiver data
CREATE OR REPLACE VIEW flights_with_transceivers AS
SELECT 
    f.*,
    t.frequency as radio_frequency,
    t.position_lat as radio_lat,
    t.position_lon as radio_lon,
    t.height_msl as radio_height_msl,
    t.height_agl as radio_height_agl
FROM flights f
LEFT JOIN transceivers t ON f.callsign = t.callsign AND t.entity_type = 'flight'
WHERE f.status = 'active';

-- Create view for ATC positions with transceiver data
CREATE OR REPLACE VIEW atc_with_transceivers AS
SELECT 
    a.*,
    t.frequency as radio_frequency,
    t.position_lat as radio_lat,
    t.position_lon as radio_lon,
    t.height_msl as radio_height_msl,
    t.height_agl as radio_height_agl
FROM atc_positions a
LEFT JOIN transceivers t ON a.callsign = t.callsign AND t.entity_type = 'atc'
WHERE a.status = 'online';

-- Create view for all active radio frequencies
CREATE OR REPLACE VIEW active_radio_frequencies AS
SELECT 
    callsign,
    frequency,
    position_lat,
    position_lon,
    entity_type,
    timestamp
FROM transceivers
WHERE timestamp > NOW() - INTERVAL '5 minutes'
ORDER BY frequency, callsign; 