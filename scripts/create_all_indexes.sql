-- Complete Index Creation Script for Production
-- This creates ALL indexes defined in init.sql for optimal performance

-- Controllers indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_callsign ON controllers(callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_cid ON controllers(cid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_cid_rating ON controllers(cid, rating);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_facility_server ON controllers(facility, server);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_last_updated ON controllers(last_updated);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_rating_last_updated ON controllers(rating, last_updated);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_callsign_facility ON controllers(callsign, facility);

-- Flights indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_callsign ON flights(callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_callsign_status ON flights(callsign, last_updated);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_position ON flights(latitude, longitude);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_departure_arrival ON flights(departure, arrival);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_cid_server ON flights(cid, server);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_altitude ON flights(altitude);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_flight_rules ON flights(flight_rules);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_planned_altitude ON flights(planned_altitude);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_aircraft_short ON flights(aircraft_short);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_revision_id ON flights(revision_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_callsign_departure_arrival ON flights(callsign, departure, arrival);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_callsign_logon ON flights(callsign, logon_time);

-- Transceivers indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_callsign ON transceivers(callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_callsign_timestamp ON transceivers(callsign, timestamp);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_frequency ON transceivers(frequency);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_entity ON transceivers(entity_type, entity_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_entity_type_callsign ON transceivers(entity_type, callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_entity_type_timestamp ON transceivers(entity_type, timestamp);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_atc_detection ON transceivers(entity_type, callsign, timestamp, frequency, position_lat, position_lon);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_flight_frequency_callsign ON transceivers(entity_type, frequency, callsign) WHERE entity_type = 'flight';

-- Flight Sector Occupancy indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_sector_occupancy_callsign ON flight_sector_occupancy(callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_sector_occupancy_entry_timestamp ON flight_sector_occupancy(entry_timestamp);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_sector_occupancy_sector_name ON flight_sector_occupancy(sector_name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_sector_occupancy_callsign_sector ON flight_sector_occupancy(callsign, sector_name);

-- Flight Summaries indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_summaries_callsign ON flight_summaries(callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_summaries_completion_time ON flight_summaries(completion_time);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_summaries_flight_rules ON flight_summaries(flight_rules);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_summaries_controller_time ON flight_summaries(controller_time_percentage);

-- Flights Archive indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_archive_callsign ON flights_archive(callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_archive_logon_time ON flights_archive(logon_time);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_archive_last_updated ON flights_archive(last_updated);

-- Verify all indexes were created
SELECT 
    schemaname, 
    tablename, 
    COUNT(*) as index_count
FROM pg_indexes 
WHERE table_schema = 'public' 
    AND tablename IN ('controllers', 'flights', 'transceivers', 'flight_sector_occupancy', 'flight_summaries', 'flights_archive')
GROUP BY schemaname, tablename
ORDER BY tablename;
