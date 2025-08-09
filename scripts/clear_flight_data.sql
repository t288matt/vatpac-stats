-- Database Cleanup Script - Clear Flight Data
-- This script deletes all data from flight-related tables while preserving
-- the airports table data.

-- WARNING: This will permanently delete all flight data!
-- Only run this if you are sure you want to clear all flight data.

-- Usage:
--   docker exec -it vatsim_postgres psql -U vatsim_user -d vatsim_data -f /path/to/clear_flight_data.sql

-- Show current row counts before deletion
SELECT 'BEFORE DELETION - Row counts:' as info;
SELECT 'flights' as table_name, COUNT(*) as row_count FROM flights
UNION ALL
SELECT 'controllers', COUNT(*) FROM controllers
UNION ALL
-- SELECT 'sectors', COUNT(*) FROM sectors  -- Table removed
UNION ALL
-- SELECT 'traffic_movements', COUNT(*) FROM traffic_movements  -- REMOVED: Traffic Analysis Service - Phase 4
UNION ALL
-- SELECT 'airport_config', COUNT(*) FROM airport_config  -- Table removed
UNION ALL
-- SELECT 'movement_detection_config', COUNT(*) FROM movement_detection_config  -- Table removed
UNION ALL
-- SELECT 'system_config', COUNT(*) FROM system_config  -- Table removed
UNION ALL
SELECT 'transceivers', COUNT(*) FROM transceivers
UNION ALL
SELECT 'frequency_matches', COUNT(*) FROM frequency_matches
UNION ALL
SELECT 'airports', COUNT(*) FROM airports
ORDER BY table_name;

-- Disable foreign key checks temporarily
SET session_replication_role = replica;

-- Clear tables in dependency order (child tables first, then parent tables)
-- This prevents foreign key constraint violations

-- 1. Clear frequency_matches (no dependencies)
DELETE FROM frequency_matches;
SELECT 'Cleared frequency_matches' as status;

-- 2. Clear transceivers (no dependencies)
DELETE FROM transceivers;
SELECT 'Cleared transceivers' as status;

-- REMOVED: Traffic Analysis Service - Phase 4
-- 3. Clear traffic_movements (no dependencies) - REMOVED
-- DELETE FROM traffic_movements;
-- SELECT 'Cleared traffic_movements' as status;

-- 4. Clear flights (no dependencies)
DELETE FROM flights;
SELECT 'Cleared flights' as status;

-- 5. Clear sectors (references controllers) - Table removed
-- DELETE FROM sectors;
-- SELECT 'Cleared sectors' as status;

-- 6. Clear controllers (no dependencies)
DELETE FROM controllers;
SELECT 'Cleared controllers' as status;

-- 7. Clear airport_config (no dependencies) - Table removed
-- DELETE FROM airport_config;
-- SELECT 'Cleared airport_config' as status;

-- 8. Clear movement_detection_config (no dependencies) - Table removed
-- DELETE FROM movement_detection_config;
-- SELECT 'Cleared movement_detection_config' as status;

-- 9. Clear system_config (no dependencies) - Table removed
-- DELETE FROM system_config;
-- SELECT 'Cleared system_config' as status;

-- Re-enable foreign key checks
SET session_replication_role = DEFAULT;

-- Show final row counts
SELECT 'AFTER DELETION - Row counts:' as info;
SELECT 'flights' as table_name, COUNT(*) as row_count FROM flights
UNION ALL
SELECT 'controllers', COUNT(*) FROM controllers
UNION ALL
-- SELECT 'sectors', COUNT(*) FROM sectors  -- Table removed
UNION ALL
-- SELECT 'traffic_movements', COUNT(*) FROM traffic_movements  -- REMOVED: Traffic Analysis Service - Phase 4
UNION ALL
-- SELECT 'airport_config', COUNT(*) FROM airport_config  -- Table removed
UNION ALL
-- SELECT 'movement_detection_config', COUNT(*) FROM movement_detection_config  -- Table removed
UNION ALL
-- SELECT 'system_config', COUNT(*) FROM system_config  -- Table removed
UNION ALL
SELECT 'transceivers', COUNT(*) FROM transceivers
UNION ALL
SELECT 'frequency_matches', COUNT(*) FROM frequency_matches
UNION ALL
SELECT 'airports', COUNT(*) FROM airports
ORDER BY table_name;

-- Verify airports table is preserved
SELECT 'VERIFICATION - Airports table preserved:' as info;
SELECT COUNT(*) as airports_count FROM airports;

SELECT 'Database cleanup completed successfully!' as status;
