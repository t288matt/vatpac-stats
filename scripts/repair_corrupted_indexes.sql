-- Database Index Corruption Repair Script
-- This script fixes the corrupted index "idx_controllers_callsign_facility"
-- Run this script when you encounter index corruption errors

-- First, let's check the current state of the corrupted index
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    indexdef,
    'Corrupted' as status
FROM pg_indexes 
WHERE indexname = 'idx_controllers_callsign_facility';

-- Check for any other potentially corrupted indexes
SELECT 
    schemaname, 
    tablename, 
    indexname,
    'Check for corruption' as status
FROM pg_indexes 
WHERE tablename = 'controllers';

-- Step 1: Drop the corrupted index
DROP INDEX CONCURRENTLY IF EXISTS idx_controllers_callsign_facility;

-- Step 2: Recreate the index with proper parameters
CREATE INDEX CONCURRENTLY idx_controllers_callsign_facility 
ON controllers(callsign, facility);

-- Step 3: Verify the index was created successfully
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    indexdef,
    'Repaired' as status
FROM pg_indexes 
WHERE indexname = 'idx_controllers_callsign_facility';

-- Step 4: Run VACUUM ANALYZE to clean up any table corruption
VACUUM ANALYZE controllers;

-- Step 5: Check for any other potential issues
SELECT 
    schemaname, 
    tablename, 
    indexname,
    'Verified' as status
FROM pg_indexes 
WHERE tablename = 'controllers'
ORDER BY indexname;

-- Step 6: Verify the table structure is intact
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'controllers' 
ORDER BY ordinal_position;


