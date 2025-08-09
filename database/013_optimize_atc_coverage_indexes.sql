-- ATC Service Coverage Analysis - Index Optimization
-- This migration adds indexes specifically optimized for the Grafana ATC Service Coverage dashboard queries
-- Based on analysis of the complex CTEs and JOIN patterns used in the dashboard

-- ============================================================================
-- CRITICAL MISSING INDEXES FOR ATC SERVICE COVERAGE QUERIES
-- ============================================================================

-- 1. TRANSCEIVERS TABLE OPTIMIZATION
-- The queries heavily filter transceivers by entity_type and join on frequency + timestamp

-- Primary index for entity_type filtering (most selective filter)
CREATE INDEX IF NOT EXISTS idx_transceivers_entity_type 
ON transceivers(entity_type);

-- Composite index for flight transceivers CTE
CREATE INDEX IF NOT EXISTS idx_transceivers_flight_frequency_timestamp 
ON transceivers(entity_type, frequency, timestamp) 
WHERE entity_type = 'flight';

-- Composite index for ATC transceivers CTE  
CREATE INDEX IF NOT EXISTS idx_transceivers_atc_frequency_timestamp 
ON transceivers(entity_type, frequency, timestamp) 
WHERE entity_type = 'atc';

-- Index for position-based filtering (distance calculations)
CREATE INDEX IF NOT EXISTS idx_transceivers_position_lat_lon 
ON transceivers(position_lat, position_lon) 
WHERE position_lat IS NOT NULL AND position_lon IS NOT NULL;

-- Composite index for frequency matching with position
CREATE INDEX IF NOT EXISTS idx_transceivers_freq_pos_time 
ON transceivers(frequency, position_lat, position_lon, timestamp);

-- 2. CONTROLLERS TABLE OPTIMIZATION
-- Queries filter out observers and join on callsign

-- Index for facility filtering (excludes OBS)
CREATE INDEX IF NOT EXISTS idx_controllers_facility_callsign 
ON controllers(facility, callsign) 
WHERE facility != 'OBS';

-- Index for position classification in dashboard queries
CREATE INDEX IF NOT EXISTS idx_controllers_position 
ON controllers(position) 
WHERE position IS NOT NULL;

-- 3. FLIGHTS TABLE OPTIMIZATION
-- The queries count flight records and filter by last_updated timestamp

-- Critical index for flight record counting by callsign
CREATE INDEX IF NOT EXISTS idx_flights_callsign_last_updated_count 
ON flights(callsign, last_updated);

-- Index for time-based filtering (24-hour queries)
CREATE INDEX IF NOT EXISTS idx_flights_last_updated_desc 
ON flights(last_updated DESC);

-- 4. COMPOSITE INDEXES FOR COMPLEX JOINS

-- Index for frequency matching join optimization
-- This covers the most expensive join: transceivers frequency + timestamp window
CREATE INDEX IF NOT EXISTS idx_transceivers_frequency_entity_timestamp 
ON transceivers(frequency, entity_type, timestamp);

-- Index for EXISTS subquery optimization in flight_records_with_atc CTE
CREATE INDEX IF NOT EXISTS idx_flights_exists_optimization 
ON flights(callsign, last_updated);

-- ============================================================================
-- TIME-BASED PARTITIONING PREPARATION (Future Optimization)
-- ============================================================================

-- Add comments for future partitioning strategy
COMMENT ON INDEX idx_transceivers_flight_frequency_timestamp IS 'Optimizes flight transceiver filtering - consider partitioning by timestamp';
COMMENT ON INDEX idx_transceivers_atc_frequency_timestamp IS 'Optimizes ATC transceiver filtering - consider partitioning by timestamp';
COMMENT ON INDEX idx_flights_last_updated_desc IS 'Optimizes time-based flight queries - candidate for partitioning';

-- ============================================================================
-- ADDITIONAL PERFORMANCE OPTIMIZATIONS
-- ============================================================================

-- 5. FREQUENCY TABLE (if exists) - for frequency normalization
-- The queries convert frequency/1000000.0 - consider storing normalized values

-- 6. STATISTICS UPDATE
-- Force statistics update on key tables after index creation
ANALYZE transceivers;
ANALYZE controllers; 
ANALYZE flights;

-- ============================================================================
-- INDEX USAGE MONITORING
-- ============================================================================

-- Query to monitor index usage after deployment:
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes 
WHERE schemaname = 'public' 
    AND tablename IN ('transceivers', 'controllers', 'flights')
    AND indexname LIKE 'idx_%'
ORDER BY idx_scan DESC;
*/

-- ============================================================================
-- QUERY PERFORMANCE TESTING
-- ============================================================================

-- Test query performance with EXPLAIN ANALYZE:
/*
EXPLAIN (ANALYZE, BUFFERS) 
WITH flight_transceivers AS (
    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
    FROM transceivers t 
    WHERE t.entity_type = 'flight'
),
atc_transceivers AS (
    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
    FROM transceivers t 
    WHERE t.entity_type = 'atc' 
    AND t.callsign IN (SELECT DISTINCT c.callsign FROM controllers c WHERE c.facility != 'OBS')
)
SELECT COUNT(*) FROM flight_transceivers ft 
JOIN atc_transceivers at ON ft.frequency_mhz = at.frequency_mhz 
AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= 180;
*/

-- ============================================================================
-- MAINTENANCE NOTES
-- ============================================================================

-- 1. Monitor index bloat regularly
-- 2. Consider partial indexes for large tables with sparse data
-- 3. Evaluate query plans after data growth
-- 4. Consider table partitioning for transceivers table by timestamp
-- 5. Monitor disk space usage - these indexes will require significant space

-- Estimated index sizes (approximate):
-- - idx_transceivers_freq_pos_time: Large (4 columns, all records)
-- - idx_transceivers_entity_type: Small (single column, low cardinality) 
-- - idx_controllers_facility_callsign: Medium (partial index)
-- - idx_flights_callsign_last_updated_count: Large (all flight records)

COMMENT ON INDEX idx_transceivers_entity_type IS 'Primary filter for ATC coverage analysis queries';
COMMENT ON INDEX idx_transceivers_freq_pos_time IS 'Optimizes frequency matching with position and time constraints';
COMMENT ON INDEX idx_controllers_facility_callsign IS 'Optimizes ATC controller filtering excluding observers';
COMMENT ON INDEX idx_flights_callsign_last_updated_count IS 'Critical for flight record counting in ATC coverage analysis';
