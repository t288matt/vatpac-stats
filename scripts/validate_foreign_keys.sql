-- Foreign Key Dependency Validation Script
-- Purpose: Analyze and validate foreign key constraints before table removal
-- Tables to be removed: events, flight_summaries, movement_summaries, vatsim_status

-- ============================================================================
-- SECTION 1: IDENTIFY ALL FOREIGN KEY CONSTRAINTS
-- ============================================================================

SELECT 'FOREIGN KEY CONSTRAINT ANALYSIS' as analysis_section;
SELECT '=' as separator;

-- Get all foreign key constraints in the database
SELECT 
    tc.constraint_name,
    tc.table_name as source_table,
    kcu.column_name as source_column,
    ccu.table_name as target_table,
    ccu.column_name as target_column,
    CASE 
        WHEN tc.table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status') THEN '🗑️ UNUSED TABLE'
        WHEN ccu.table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status') THEN '⚠️ REFERENCES UNUSED TABLE'
        ELSE '✅ ACTIVE CONSTRAINT'
    END as constraint_status
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu 
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu 
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_name;

-- ============================================================================
-- SECTION 2: ANALYZE UNUSED TABLES SPECIFICALLY
-- ============================================================================

SELECT 'UNUSED TABLE FOREIGN KEY ANALYSIS' as analysis_section;
SELECT '=' as separator;

-- Check if unused tables have any OUTGOING foreign key constraints
SELECT 
    'OUTGOING CONSTRAINTS (unused tables referencing others)' as constraint_type,
    tc.table_name as unused_table,
    tc.constraint_name,
    kcu.column_name as source_column,
    ccu.table_name as referenced_table,
    ccu.column_name as referenced_column
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu 
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu 
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status')
    AND tc.table_schema = 'public'
ORDER BY tc.table_name;

-- Check if any active tables have INCOMING foreign key constraints from unused tables
SELECT 
    'INCOMING CONSTRAINTS (active tables referenced by unused tables)' as constraint_type,
    ccu.table_name as active_table,
    tc.constraint_name,
    tc.table_name as unused_table_source,
    kcu.column_name as source_column,
    ccu.column_name as referenced_column
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu 
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu 
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status')
    AND ccu.table_name NOT IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status')
    AND tc.table_schema = 'public'
ORDER BY ccu.table_name;

-- ============================================================================
-- SECTION 3: TABLE DROP ORDER DETERMINATION
-- ============================================================================

SELECT 'TABLE DROP ORDER ANALYSIS' as analysis_section;
SELECT '=' as separator;

-- Determine safe drop order based on foreign key dependencies
WITH fk_dependencies AS (
    SELECT 
        tc.table_name as source_table,
        ccu.table_name as target_table
    FROM information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu 
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu 
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name IN ('events', 'flight_summaries', 'movement_summaries', 'vatsim_status')
        AND tc.table_schema = 'public'
)
SELECT 
    'RECOMMENDED DROP ORDER:' as recommendation,
    CASE 
        WHEN source_table = 'flight_summaries' THEN '1. DROP flight_summaries FIRST (has FK constraints)'
        WHEN source_table IN ('events', 'movement_summaries', 'vatsim_status') THEN '2-4. DROP ' || source_table || ' (no FK constraints - any order)'
    END as drop_order,
    source_table || ' -> ' || target_table as dependency_chain
FROM fk_dependencies
UNION ALL
SELECT 
    'STANDALONE TABLES (no FK constraints):' as recommendation,
    '2-4. DROP in any order' as drop_order,
    table_name || ' (standalone)' as dependency_chain
FROM (
    SELECT unnest(ARRAY['events', 'movement_summaries', 'vatsim_status']) as table_name
) standalone
WHERE table_name NOT IN (SELECT source_table FROM fk_dependencies)
ORDER BY drop_order;

-- ============================================================================
-- SECTION 4: PRE-MIGRATION VALIDATION CHECKS
-- ============================================================================

SELECT 'PRE-MIGRATION VALIDATION CHECKS' as analysis_section;
SELECT '=' as separator;

-- Check if tables exist and have data
SELECT 
    'TABLE EXISTENCE AND DATA CHECK' as check_type,
    table_name,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = ut.table_name AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as table_exists
FROM (
    SELECT unnest(ARRAY['events', 'flight_summaries', 'movement_summaries', 'vatsim_status']) as table_name
) ut;

-- Check row counts for unused tables (if they exist)
DO $$
DECLARE
    table_name text;
    row_count integer;
    sql_query text;
BEGIN
    SELECT 'ROW COUNT CHECK FOR UNUSED TABLES' as check_type;
    
    FOR table_name IN SELECT unnest(ARRAY['events', 'flight_summaries', 'movement_summaries', 'vatsim_status'])
    LOOP
        -- Check if table exists first
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = table_name AND table_schema = 'public') THEN
            sql_query := 'SELECT COUNT(*) FROM ' || table_name;
            EXECUTE sql_query INTO row_count;
            RAISE NOTICE 'Table %: % rows', table_name, row_count;
            
            IF row_count > 0 THEN
                RAISE WARNING 'Table % contains % rows that will be deleted!', table_name, row_count;
            END IF;
        ELSE
            RAISE NOTICE 'Table % does not exist', table_name;
        END IF;
    END LOOP;
END $$;

-- ============================================================================
-- SECTION 5: FINAL RECOMMENDATIONS
-- ============================================================================

SELECT 'FINAL RECOMMENDATIONS' as analysis_section;
SELECT '=' as separator;

SELECT 
    'SAFE DROP ORDER (CRITICAL):' as recommendation_type,
    '1. DROP TABLE flight_summaries CASCADE;' as step_1,
    '2. DROP TABLE events CASCADE;' as step_2,
    '3. DROP TABLE movement_summaries CASCADE;' as step_3,
    '4. DROP TABLE vatsim_status CASCADE;' as step_4;

SELECT 
    'VALIDATION COMMANDS:' as recommendation_type,
    'Run this script before migration' as validation_step_1,
    'Verify all FK constraints are identified' as validation_step_2,
    'Confirm table drop order is correct' as validation_step_3,
    'Check for any data that needs preservation' as validation_step_4;

SELECT 'Foreign Key Dependency Analysis Complete' as final_status;
