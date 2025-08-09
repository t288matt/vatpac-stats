-- Migration: Remove unused database tables
-- Description: Removes 4 unused tables (events, flight_summaries, movement_summaries, vatsim_status)
-- Date: January 2025
-- Author: Database Cleanup Sprint - Story 4
-- Sprint: Database Schema Cleanup
-- 
-- CRITICAL: Tables must be dropped in specific order due to foreign key constraints
-- flight_summaries has FK constraints to controllers.id and sectors.id

-- ============================================================================
-- PRE-MIGRATION VALIDATION AND LOGGING
-- ============================================================================

-- Start transaction for atomic operation
BEGIN;

-- Log migration start
SELECT 'DATABASE CLEANUP MIGRATION STARTED' as migration_status, NOW() as timestamp;

-- Pre-flight validation: Check if tables exist
DO $$
DECLARE
    table_exists_count integer := 0;
    missing_tables text[] := '{}';
    existing_tables text[] := '{}';
BEGIN
    -- Check each table existence
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'flight_summaries' AND table_schema = 'public') THEN
        existing_tables := array_append(existing_tables, 'flight_summaries');
        table_exists_count := table_exists_count + 1;
    ELSE
        missing_tables := array_append(missing_tables, 'flight_summaries');
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'movement_summaries' AND table_schema = 'public') THEN
        existing_tables := array_append(existing_tables, 'movement_summaries');
        table_exists_count := table_exists_count + 1;
    ELSE
        missing_tables := array_append(missing_tables, 'movement_summaries');
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events' AND table_schema = 'public') THEN
        existing_tables := array_append(existing_tables, 'events');
        table_exists_count := table_exists_count + 1;
    ELSE
        missing_tables := array_append(missing_tables, 'events');
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vatsim_status' AND table_schema = 'public') THEN
        existing_tables := array_append(existing_tables, 'vatsim_status');
        table_exists_count := table_exists_count + 1;
    ELSE
        missing_tables := array_append(missing_tables, 'vatsim_status');
    END IF;
    
    -- Report findings
    RAISE NOTICE 'PRE-MIGRATION CHECK: % of 4 unused tables found', table_exists_count;
    
    IF array_length(existing_tables, 1) > 0 THEN
        RAISE NOTICE 'Tables to be removed: %', array_to_string(existing_tables, ', ');
    END IF;
    
    IF array_length(missing_tables, 1) > 0 THEN
        RAISE NOTICE 'Tables already missing: %', array_to_string(missing_tables, ', ');
    END IF;
    
    -- If no tables exist, this migration may have already run
    IF table_exists_count = 0 THEN
        RAISE WARNING 'No unused tables found - migration may have already been applied';
    END IF;
END $$;

-- Validate foreign key constraints before removal
SELECT 'FOREIGN KEY CONSTRAINT VALIDATION' as validation_step;
SELECT 
    tc.constraint_name,
    tc.table_name as source_table,
    kcu.column_name as source_column,
    ccu.table_name as target_table,
    ccu.column_name as target_column
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu 
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu 
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status')
    AND tc.table_schema = 'public'
ORDER BY tc.table_name;

-- Check row counts for data impact assessment
DO $$
DECLARE
    table_name text;
    row_count integer;
    total_rows_to_delete integer := 0;
BEGIN
    SELECT 'ROW COUNT ASSESSMENT' as assessment_step;
    
    FOR table_name IN SELECT unnest(ARRAY['events', 'flight_summaries', 'movement_summaries', 'vatsim_status'])
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = table_name AND table_schema = 'public') THEN
            EXECUTE format('SELECT COUNT(*) FROM %I', table_name) INTO row_count;
            total_rows_to_delete := total_rows_to_delete + row_count;
            
            IF row_count > 0 THEN
                RAISE WARNING 'Table % contains % rows that will be PERMANENTLY DELETED', table_name, row_count;
            ELSE
                RAISE NOTICE 'Table % is empty (% rows)', table_name, row_count;
            END IF;
        END IF;
    END LOOP;
    
    IF total_rows_to_delete > 0 THEN
        RAISE WARNING 'TOTAL ROWS TO BE DELETED: % rows across all unused tables', total_rows_to_delete;
        RAISE NOTICE 'Proceeding with table removal in 3 seconds...';
        PERFORM pg_sleep(3);
    END IF;
END $$;

-- ============================================================================
-- TABLE REMOVAL (CRITICAL ORDER)
-- ============================================================================

SELECT 'BEGINNING TABLE REMOVAL PROCESS' as removal_status, NOW() as timestamp;

-- STEP 1: Drop flight_summaries FIRST (has FK constraints to controllers & sectors)
SELECT 'STEP 1: Dropping flight_summaries (has foreign key constraints)' as step;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'flight_summaries' AND table_schema = 'public') THEN
        DROP TABLE flight_summaries CASCADE;
        RAISE NOTICE 'SUCCESS: flight_summaries table dropped';
    ELSE
        RAISE NOTICE 'SKIPPED: flight_summaries table does not exist';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'FAILED to drop flight_summaries: %', SQLERRM;
END $$;

-- STEP 2: Drop events (no FK constraints)
SELECT 'STEP 2: Dropping events (no foreign key constraints)' as step;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events' AND table_schema = 'public') THEN
        DROP TABLE events CASCADE;
        RAISE NOTICE 'SUCCESS: events table dropped';
    ELSE
        RAISE NOTICE 'SKIPPED: events table does not exist';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'FAILED to drop events: %', SQLERRM;
END $$;

-- STEP 3: Drop movement_summaries (no FK constraints)
SELECT 'STEP 3: Dropping movement_summaries (no foreign key constraints)' as step;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'movement_summaries' AND table_schema = 'public') THEN
        DROP TABLE movement_summaries CASCADE;
        RAISE NOTICE 'SUCCESS: movement_summaries table dropped';
    ELSE
        RAISE NOTICE 'SKIPPED: movement_summaries table does not exist';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'FAILED to drop movement_summaries: %', SQLERRM;
END $$;

-- STEP 4: Drop vatsim_status (no FK constraints)
SELECT 'STEP 4: Dropping vatsim_status (no foreign key constraints)' as step;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vatsim_status' AND table_schema = 'public') THEN
        DROP TABLE vatsim_status CASCADE;
        RAISE NOTICE 'SUCCESS: vatsim_status table dropped';
    ELSE
        RAISE NOTICE 'SKIPPED: vatsim_status table does not exist';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'FAILED to drop vatsim_status: %', SQLERRM;
END $$;

-- ============================================================================
-- POST-MIGRATION VALIDATION
-- ============================================================================

SELECT 'POST-MIGRATION VALIDATION' as validation_phase, NOW() as timestamp;

-- Verify all unused tables are removed
DO $$
DECLARE
    remaining_tables text[] := '{}';
    table_name text;
BEGIN
    FOR table_name IN SELECT unnest(ARRAY['events', 'flight_summaries', 'movement_summaries', 'vatsim_status'])
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = table_name AND table_schema = 'public') THEN
            remaining_tables := array_append(remaining_tables, table_name);
        END IF;
    END LOOP;
    
    IF array_length(remaining_tables, 1) > 0 THEN
        RAISE EXCEPTION 'MIGRATION FAILED: These unused tables still exist: %', array_to_string(remaining_tables, ', ');
    ELSE
        RAISE NOTICE 'VALIDATION SUCCESS: All unused tables successfully removed';
    END IF;
END $$;

-- Verify no orphaned foreign key constraints remain
SELECT 'ORPHANED CONSTRAINT CHECK' as constraint_check;
SELECT 
    tc.constraint_name,
    tc.table_name,
    'ORPHANED FK CONSTRAINT' as issue_type
FROM information_schema.table_constraints AS tc 
JOIN information_schema.constraint_column_usage AS ccu 
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND ccu.table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status')
    AND tc.table_schema = 'public';

-- Show remaining active tables
SELECT 'REMAINING ACTIVE TABLES' as table_inventory;
SELECT 
    table_name,
    CASE 
        WHEN table_name IN ('flights', 'controllers', 'sectors', 'transceivers', 'traffic_movements', 'frequency_matches') THEN 'CORE TABLE'
        WHEN table_name IN ('airports', 'airport_config') THEN 'REFERENCE TABLE'
        WHEN table_name IN ('system_config', 'movement_detection_config') THEN 'CONFIG TABLE'
        ELSE 'OTHER TABLE'
    END as table_category
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
ORDER BY table_category, table_name;

-- Show final table count
SELECT 'FINAL DATABASE SCHEMA SUMMARY' as summary;
SELECT 
    COUNT(*) as total_tables,
    COUNT(CASE WHEN table_name IN ('flights', 'controllers', 'sectors', 'transceivers', 'traffic_movements', 'frequency_matches') THEN 1 END) as core_tables,
    COUNT(CASE WHEN table_name IN ('airports', 'airport_config') THEN 1 END) as reference_tables,
    COUNT(CASE WHEN table_name IN ('system_config', 'movement_detection_config') THEN 1 END) as config_tables
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';

-- ============================================================================
-- MIGRATION COMPLETION
-- ============================================================================

-- Commit the transaction
COMMIT;

SELECT 'DATABASE CLEANUP MIGRATION COMPLETED SUCCESSFULLY' as final_status, NOW() as completion_timestamp;

-- Final success message
SELECT 
    'Schema cleanup complete!' as message,
    'Removed 4 unused tables: events, flight_summaries, movement_summaries, vatsim_status' as details,
    'Database schema simplified and optimized' as result;

-- Recommendations for next steps
SELECT 'NEXT STEPS RECOMMENDATIONS' as recommendations;
SELECT 
    '1. Update application code to remove unused model references' as step_1,
    '2. Update database initialization script (init.sql)' as step_2,
    '3. Update documentation to reflect new schema' as step_3,
    '4. Run comprehensive application tests' as step_4,
    '5. Monitor application performance post-cleanup' as step_5;
