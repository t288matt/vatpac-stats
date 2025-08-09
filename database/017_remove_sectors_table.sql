-- Migration: Remove sectors table (VATSIM API limitation)
-- Description: Removes sectors table due to missing data source
-- Date: January 2025
-- Reason: VATSIM API v3 does not provide sectors data

-- Record current state
SELECT 'BEFORE REMOVAL - Sectors count:' as info;
SELECT COUNT(*) as sectors_count FROM sectors;

-- Remove foreign key constraints first (CASCADE handles this)
DROP TABLE IF EXISTS sectors CASCADE;
SELECT 'Dropped sectors table and all dependencies' as status;

-- Verify removal
SELECT 'AFTER REMOVAL - Remaining tables:' as info;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

SELECT 'Sectors table cleanup completed successfully' as final_status;
