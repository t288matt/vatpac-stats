-- Migration: Remove unused database tables
-- Description: Removes 4 unused tables (events, flight_summaries, movement_summaries, vatsim_status)
-- Date: January 2025
-- Author: Database Cleanup Sprint - Story 4
-- Sprint: Database Schema Cleanup

-- Start transaction for atomic operation
BEGIN;

-- Log migration start
SELECT 'DATABASE CLEANUP MIGRATION STARTED' as migration_status, NOW() as timestamp;

-- Pre-migration validation: Show current table count
SELECT 'PRE-MIGRATION TABLE COUNT' as check_type;
SELECT COUNT(*) as table_count FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- Show tables to be removed
SELECT 'TABLES TO BE REMOVED' as check_type;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
  AND table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status')
ORDER BY table_name;

-- Check for foreign key constraints
SELECT 'FOREIGN KEY CONSTRAINTS CHECK' as check_type;
SELECT 
    tc.constraint_name,
    tc.table_name as source_table,
    kcu.column_name as source_column,
    ccu.table_name as target_table
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu 
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu 
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status')
ORDER BY tc.table_name;

-- STEP 1: Drop flight_summaries FIRST (has FK constraints)
SELECT 'STEP 1: Dropping flight_summaries' as step;
DROP TABLE IF EXISTS flight_summaries CASCADE;

-- STEP 2: Drop events
SELECT 'STEP 2: Dropping events' as step;
DROP TABLE IF EXISTS events CASCADE;

-- STEP 3: Drop movement_summaries  
SELECT 'STEP 3: Dropping movement_summaries' as step;
DROP TABLE IF EXISTS movement_summaries CASCADE;

-- STEP 4: Drop vatsim_status
SELECT 'STEP 4: Dropping vatsim_status' as step;
DROP TABLE IF EXISTS vatsim_status CASCADE;

-- Post-migration validation
SELECT 'POST-MIGRATION VALIDATION' as validation_phase;

-- Verify tables are removed
SELECT 'CHECKING REMOVED TABLES' as check_type;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
  AND table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status');

-- Show final table count
SELECT 'FINAL TABLE COUNT' as check_type;
SELECT COUNT(*) as table_count FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- Show remaining tables
SELECT 'REMAINING TABLES' as check_type;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Commit the transaction
COMMIT;

SELECT 'DATABASE CLEANUP MIGRATION COMPLETED SUCCESSFULLY' as final_status, NOW() as completion_timestamp;
