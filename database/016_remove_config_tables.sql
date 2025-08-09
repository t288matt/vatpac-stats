-- Migration: Remove unused configuration tables
-- Description: Removes movement_detection_config and airport_config tables
-- Date: January 2025
-- Reason: Zero records, minimal usage, redundant functionality

-- Record current state
SELECT 'BEFORE REMOVAL - Config table counts:' as info;
SELECT 'movement_detection_config' as table_name, COUNT(*) as row_count FROM movement_detection_config
UNION ALL
SELECT 'airport_config', COUNT(*) FROM airport_config;

-- Drop tables in safe order
DROP TABLE IF EXISTS movement_detection_config CASCADE;
SELECT 'Dropped movement_detection_config table' as status;

DROP TABLE IF EXISTS airport_config CASCADE;
SELECT 'Dropped airport_config table' as status;

-- Verify removal
SELECT 'AFTER REMOVAL - Remaining tables:' as info;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

SELECT 'Config tables cleanup completed successfully' as final_status;
