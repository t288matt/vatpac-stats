-- Add missing indexes to fix the timeouts in ATC detection service

-- Index for transceivers table to optimize ATC detection queries
-- This index will speed up the _find_matches_for_controller method's JOIN operation
CREATE INDEX IF NOT EXISTS idx_transceivers_entity_type_callsign_timestamp 
ON transceivers (entity_type, callsign, timestamp);

-- Index for flight + timestamp queries in _count_airborne_controller_contacts and _get_airborne_time_from_flights
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign_timestamp_entity_flight 
ON transceivers (callsign, timestamp)
WHERE entity_type = 'flight';

-- Index for ATC + timestamp queries in _find_frequency_matches
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign_timestamp_entity_atc 
ON transceivers (callsign, timestamp)
WHERE entity_type = 'atc';

-- Add compound index for flight lookups in ATC detection service
CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign_dep_arr_logon 
ON flight_summaries (callsign, departure, arrival, logon_time);

-- Add index for completion_time queries in _get_flight_completion_time
CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign_completion
ON flight_summaries (callsign, completion_time);

-- Add compound index for the flight data lookup queries in _get_flight_record_count
CREATE INDEX IF NOT EXISTS idx_flights_callsign_altitude_last_updated 
ON flights (callsign, last_updated) 
WHERE altitude IS NOT NULL;

-- Add compound index for the flights_archive table used in _get_flight_record_count
CREATE INDEX IF NOT EXISTS idx_flights_archive_callsign_altitude_last_updated 
ON flights_archive (callsign, last_updated) 
WHERE altitude IS NOT NULL;

-- Add compound index for airborne detection in _get_airborne_time_from_flights
CREATE INDEX IF NOT EXISTS idx_flights_callsign_altitude_gt1500 
ON flights (callsign, last_updated) 
WHERE altitude > 1500;

-- Add compound index for airborne detection in _get_airborne_time_from_flights for archive
CREATE INDEX IF NOT EXISTS idx_flights_archive_callsign_altitude_gt1500 
ON flights_archive (callsign, last_updated) 
WHERE altitude > 1500;

-- Add index for controllers table lookup in ATC detection
CREATE INDEX IF NOT EXISTS idx_controllers_callsign_facility_last_updated 
ON controllers (callsign, facility, last_updated);

-- Add index to optimize the frequency matching query
CREATE INDEX IF NOT EXISTS idx_transceivers_frequency_pos_timestamp 
ON transceivers (frequency, position_lat, position_lon, timestamp);

