-- Production Index Optimization Script
-- Run this to optimize indexes for the controller flight counting query

-- Drop unnecessary indexes that were created during testing
DROP INDEX IF EXISTS idx_transceivers_entity_type_callsign_frequency;
DROP INDEX IF EXISTS idx_transceivers_entity_type_frequency;
DROP INDEX IF EXISTS idx_transceivers_atc_frequency_callsign;

-- Create the essential optimized indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_controllers_rating_last_updated 
ON controllers(rating, last_updated);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_flight_frequency_callsign 
ON transceivers(entity_type, frequency, callsign) 
WHERE entity_type = 'flight';

-- Verify the indexes exist
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename IN ('controllers', 'transceivers') 
    AND indexname LIKE '%rating_last_updated%' 
    OR indexname LIKE '%flight_frequency_callsign%'
ORDER BY tablename, indexname;
