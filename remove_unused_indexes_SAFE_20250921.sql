-- SAFE UNUSED INDEX REMOVAL SCRIPT
-- Generated: 2025-09-21 16:55:16 (CORRECTED VERSION)
-- Total indexes to remove: 18 (EXCLUDING PRIMARY KEYS)
-- Estimated storage recovery: 20.6MB
--
-- CRITICAL SAFETY NOTES:
-- 1. PRIMARY KEY indexes (flights_pkey, controllers_pkey, controllers_archive_pkey) are EXCLUDED
-- 2. These are essential for data integrity and referential constraints
-- 3. Run during maintenance window
-- 4. Verify no active queries using these indexes
-- 5. Have backup ready for rollback if needed
-- 6. Monitor system performance after removal

-- Begin transaction for safety
BEGIN;

-- Drop unused index: idx_controller_summaries_aircraft_count (Table: controller_summaries)
DROP INDEX IF EXISTS idx_controller_summaries_aircraft_count;

-- Drop unused index: idx_controller_summaries_aircraft_details (Table: controller_summaries)
DROP INDEX IF EXISTS idx_controller_summaries_aircraft_details;

-- Drop unused index: idx_controller_summaries_rating_facility (Table: controller_summaries)
DROP INDEX IF EXISTS idx_controller_summaries_rating_facility;

-- Drop unused index: idx_controllers_archive_callsign (Table: controllers_archive)
DROP INDEX IF EXISTS idx_controllers_archive_callsign;

-- Drop unused index: idx_flights_aircraft_short (Table: flights)
DROP INDEX IF EXISTS idx_flights_aircraft_short;

-- Drop unused index: idx_flights_altitude (Table: flights)
DROP INDEX IF EXISTS idx_flights_altitude;

-- Drop unused index: idx_flights_archive_controller_callsigns (Table: flights_archive)
DROP INDEX IF EXISTS idx_flights_archive_controller_callsigns;

-- Drop unused index: idx_flights_archive_controller_time (Table: flights_archive)
DROP INDEX IF EXISTS idx_flights_archive_controller_time;

-- Drop unused index: idx_flights_archive_deptime (Table: flights_archive)
DROP INDEX IF EXISTS idx_flights_archive_deptime;

-- Drop unused index: idx_flights_archive_primary_sector (Table: flights_archive)
DROP INDEX IF EXISTS idx_flights_archive_primary_sector;

-- Drop unused index: idx_flights_archive_sector_breakdown (Table: flights_archive)
DROP INDEX IF EXISTS idx_flights_archive_sector_breakdown;

-- Drop unused index: idx_flights_departure_arrival (Table: flights)
DROP INDEX IF EXISTS idx_flights_departure_arrival;

-- Drop unused index: idx_flights_planned_altitude (Table: flights)
DROP INDEX IF EXISTS idx_flights_planned_altitude;

-- Drop unused index: idx_flights_position (Table: flights)
DROP INDEX IF EXISTS idx_flights_position;

-- Drop unused index: idx_transceivers_atc_simple (Table: transceivers)
DROP INDEX IF EXISTS idx_transceivers_atc_simple;

-- Drop unused index: idx_transceivers_entity (Table: transceivers)
DROP INDEX IF EXISTS idx_transceivers_entity;

-- Drop unused index: idx_transceivers_flight_frequency_callsign (Table: transceivers)
DROP INDEX IF EXISTS idx_transceivers_flight_frequency_callsign;

-- Drop unused index: idx_transceivers_frequency (Table: transceivers)
DROP INDEX IF EXISTS idx_transceivers_frequency;

-- Commit the changes
COMMIT;

-- Post-removal verification query:
-- Run this to verify indexes were removed:
/*
SELECT indexrelname as removed_index 
FROM pg_stat_user_indexes 
WHERE indexrelname IN (
    'idx_transceivers_atc_simple', 
    'idx_flights_archive_controller_time', 
    'idx_transceivers_entity', 
    'idx_transceivers_frequency', 
    'idx_transceivers_flight_frequency_callsign', 
    'idx_flights_archive_primary_sector', 
    'idx_controller_summaries_aircraft_details', 
    'idx_flights_archive_deptime', 
    'idx_flights_archive_sector_breakdown', 
    'idx_flights_archive_controller_callsigns', 
    'idx_flights_altitude', 
    'idx_flights_departure_arrival', 
    'idx_flights_planned_altitude', 
    'idx_flights_aircraft_short', 
    'idx_flights_position', 
    'idx_controller_summaries_aircraft_count', 
    'idx_controller_summaries_rating_facility', 
    'idx_controllers_archive_callsign'
);
-- This query should return 0 rows if removal was successful
*/

-- EXCLUDED PRIMARY KEY INDEXES (DO NOT REMOVE):
-- flights_pkey (Table: flights) - ESSENTIAL FOR DATA INTEGRITY
-- controllers_pkey (Table: controllers) - ESSENTIAL FOR DATA INTEGRITY  
-- controllers_archive_pkey (Table: controllers_archive) - ESSENTIAL FOR DATA INTEGRITY
