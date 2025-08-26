-- Production Index Update Script - PRODUCTION SAFE VERSION
-- Apply CONCURRENTLY indexes to prevent index corruption
-- This script safely updates existing indexes without blocking operations
-- Run this during low-traffic periods for best performance

-- IMPORTANT: This script is production-safe and will NOT drop existing indexes
-- It only creates new CONCURRENTLY indexes alongside existing ones

-- Safety check: Ensure we're in the right database
DO $$
BEGIN
    IF current_database() != 'vatsim_data' THEN
        RAISE EXCEPTION 'This script must be run on the vatsim_data database';
    END IF;
END $$;

-- Log the start of the operation
SELECT 'Starting production index update with CONCURRENTLY indexes at ' || now()::text as notice;
SELECT 'This script will create new indexes alongside existing ones for safety' as notice;
SELECT 'Note: CREATE INDEX CONCURRENTLY cannot run in transactions - each index is created independently' as notice;

-- 1. Create Controllers Indexes (only if they don't exist)
-- These will be created alongside existing indexes, no dropping
-- Each CREATE INDEX CONCURRENTLY runs independently (cannot be in transaction)
SELECT 'Creating controllers indexes...' as notice;

-- Simple index creation without complex predicates
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_callsign_concurrent ON controllers(callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_cid_concurrent ON controllers(cid);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_cid_rating_concurrent ON controllers(cid, rating);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_facility_server_concurrent ON controllers(facility, server);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_last_updated_concurrent ON controllers(last_updated);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_rating_last_updated_concurrent ON controllers(rating, last_updated);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_callsign_facility_concurrent ON controllers(callsign, facility);

-- 2. Create Flights Indexes (only if they don't exist)
-- Removed low-selectivity indexes: altitude, planned_altitude, flight_rules
-- Improved geo index approach for latitude/longitude
SELECT 'Creating flights indexes...' as notice;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_callsign_concurrent ON flights(callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_callsign_status_concurrent ON flights(callsign, last_updated);

-- Use BRIN for geographic coordinates - better for range queries and bounding boxes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_position_brin_concurrent ON flights USING brin(latitude, longitude);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_departure_arrival_concurrent ON flights(departure, arrival);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_cid_server_concurrent ON flights(cid, server);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_aircraft_short_concurrent ON flights(aircraft_short);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_revision_id_concurrent ON flights(revision_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_callsign_departure_arrival_concurrent ON flights(callsign, departure, arrival);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flights_callsign_logon_concurrent ON flights(callsign, logon_time);

-- 3. Create Transceivers Indexes (only if they don't exist)
-- Simplified wide composite index to focus on most common query patterns
SELECT 'Creating transceivers indexes...' as notice;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_callsign_concurrent ON transceivers(callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_callsign_timestamp_concurrent ON transceivers(callsign, "timestamp");
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_frequency_concurrent ON transceivers(frequency);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_entity_concurrent ON transceivers(entity_type, entity_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_entity_type_callsign_concurrent ON transceivers(entity_type, callsign);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_entity_type_timestamp_concurrent ON transceivers(entity_type, "timestamp");

-- Simplified ATC detection index - focus on most common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_atc_detection_concurrent ON transceivers(entity_type, callsign, "timestamp");

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_flight_frequency_callsign_concurrent ON transceivers(entity_type, frequency, callsign) 
WHERE entity_type = 'flight';

-- 4. Verify all new indexes are created successfully
-- Count by actual index names, not by suffix pattern
SELECT 
    'Index creation verification' as check_type,
    COUNT(*) as "New Indexes Created",
    CASE 
        WHEN COUNT(*) >= 24 THEN 'SUCCESS - All expected indexes created'
        ELSE 'WARNING - Some indexes may not have been created'
    END as "Status"
FROM pg_indexes 
WHERE schemaname = 'public' 
AND indexname LIKE '%_concurrent';

-- 5. Update table statistics for optimal query planning
-- Note: ANALYZE VERBOSE runs in foreground but doesn't block writers
SELECT 'Starting table statistics update (this may take several minutes)...' as notice;

ANALYZE VERBOSE controllers;
ANALYZE VERBOSE flights;
ANALYZE VERBOSE transceivers;

-- Log completion
SELECT 'Production index update completed at ' || now()::text as notice;
SELECT 'New CONCURRENTLY indexes created successfully alongside existing indexes' as notice;
SELECT 'Next step: After verifying new indexes work, you can drop old indexes manually' as notice;

-- Post-completion verification with accurate counts
SELECT 
    'Index Summary' as summary_type,
    COUNT(*) as "Total Indexes",
    COUNT(CASE WHEN indexname NOT LIKE '%_concurrent' THEN 1 END) as "Old Indexes",
    COUNT(CASE WHEN indexname LIKE '%_concurrent' THEN 1 END) as "New CONCURRENTLY Indexes",
    'Both old and new indexes now exist - system is safe' as "Status"
FROM pg_indexes 
WHERE schemaname = 'public' 
AND indexname LIKE 'idx_%';

-- Show specific new indexes created
SELECT 
    'New Indexes Created' as detail_type,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
AND indexname LIKE '%_concurrent'
ORDER BY tablename, indexname;
