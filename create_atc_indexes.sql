-- Create indexes for ATC detection performance
-- These indexes will dramatically improve query performance for ATC interaction detection

-- Indexes for transceivers table (most critical for ATC detection)
CREATE INDEX IF NOT EXISTS idx_transceivers_entity_type_callsign ON transceivers(entity_type, callsign);
CREATE INDEX IF NOT EXISTS idx_transceivers_timestamp ON transceivers(timestamp);
CREATE INDEX IF NOT EXISTS idx_transceivers_frequency ON transceivers(frequency);
CREATE INDEX IF NOT EXISTS idx_transceivers_entity_type_timestamp ON transceivers(entity_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign_timestamp ON transceivers(callsign, timestamp);

-- Composite index for the main ATC detection query
CREATE INDEX IF NOT EXISTS idx_transceivers_atc_detection ON transceivers(entity_type, callsign, timestamp, frequency, position_lat, position_lon);

-- Indexes for flights table JOIN conditions
CREATE INDEX IF NOT EXISTS idx_flights_callsign_departure_arrival ON flights(callsign, departure, arrival);
CREATE INDEX IF NOT EXISTS idx_flights_logon_time ON flights(logon_time);
CREATE INDEX IF NOT EXISTS idx_flights_callsign_logon ON flights(callsign, logon_time);

-- Indexes for controllers table
CREATE INDEX IF NOT EXISTS idx_controllers_facility ON controllers(facility);
CREATE INDEX IF NOT EXISTS idx_controllers_callsign_facility ON controllers(callsign, facility);

-- Indexes for flight_summaries table (for updates)
CREATE INDEX IF NOT EXISTS idx_flight_summaries_controller_callsigns ON flight_summaries USING GIN(controller_callsigns);

-- Analyze tables to update statistics
ANALYZE transceivers;
ANALYZE flights;
ANALYZE controllers;
ANALYZE flight_summaries;
