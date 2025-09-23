-- =============================================================================
-- CLEANUP INVALID CONTROLLER CALLSIGNS FROM FLIGHT_SUMMARIES JSONB
-- =============================================================================
-- This script removes invalid controller callsigns from the controller_callsigns
-- JSONB field in flight_summaries table, using the controller_callsigns_list.txt
-- file as the validation source.
--
-- Usage:
--   DRY RUN:  Set @dry_run = true  (default)
--   EXECUTE:  Set @dry_run = false
-- =============================================================================

-- Configuration
\set dry_run true  -- Set to false to actually execute the cleanup

-- =============================================================================
-- STEP 1: ANALYSIS - Find invalid controllers in existing data
-- =============================================================================

-- Create temporary table with valid controller callsigns
CREATE TEMP TABLE valid_controllers AS
SELECT unnest(string_to_array(
    pg_read_file('/app/airspace_sector_data/controller_callsigns_list.txt'), 
    E'\n'
)) AS callsign
WHERE unnest(string_to_array(
    pg_read_file('/app/airspace_sector_data/controller_callsigns_list.txt'), 
    E'\n'
)) != '';

-- Analysis query - shows what will be cleaned
SELECT 
    'ANALYSIS: Invalid Controllers Found' as step,
    COUNT(DISTINCT jsonb_object_keys(controller_callsigns)) as total_controllers_in_data,
    COUNT(DISTINCT CASE 
        WHEN jsonb_object_keys(controller_callsigns) NOT IN (SELECT callsign FROM valid_controllers) 
        THEN jsonb_object_keys(controller_callsigns) 
    END) as invalid_controllers_count,
    COUNT(*) as affected_flights
FROM flight_summaries 
WHERE enrichment_status = 'completed'
AND controller_callsigns != '{}'::jsonb;

-- Show sample of invalid controllers
SELECT 
    'SAMPLE INVALID CONTROLLERS' as info,
    jsonb_object_keys(controller_callsigns) as invalid_callsign,
    COUNT(*) as flight_count
FROM flight_summaries 
WHERE enrichment_status = 'completed'
AND controller_callsigns != '{}'::jsonb
AND jsonb_object_keys(controller_callsigns) NOT IN (SELECT callsign FROM valid_controllers)
GROUP BY jsonb_object_keys(controller_callsigns)
ORDER BY flight_count DESC
LIMIT 20;

-- =============================================================================
-- STEP 2: DRY RUN - Show what would be changed (without modifying data)
-- =============================================================================

-- Show flights that would be affected (DRY RUN)
SELECT 
    CASE WHEN :dry_run THEN 'DRY RUN: Flights that would be cleaned' 
         ELSE 'EXECUTING: Cleaning flights' 
    END as status,
    fs.id,
    fs.callsign,
    fs.controller_callsigns as current_data,
    -- This is the cleaned version (what it would become)
    (
        SELECT jsonb_object_agg(key, value)
        FROM jsonb_each(fs.controller_callsigns) AS t(key, value)
        WHERE t.key IN (SELECT callsign FROM valid_controllers)
    ) as cleaned_data,
    -- Count of controllers removed
    (
        SELECT COUNT(*)
        FROM jsonb_object_keys(fs.controller_callsigns) AS t(key)
        WHERE t.key NOT IN (SELECT callsign FROM valid_controllers)
    ) as controllers_removed
FROM flight_summaries fs
WHERE fs.enrichment_status = 'completed'
AND fs.controller_callsigns != '{}'::jsonb
AND EXISTS (
    SELECT 1 
    FROM jsonb_object_keys(fs.controller_callsigns) AS t(key)
    WHERE t.key NOT IN (SELECT callsign FROM valid_controllers)
)
ORDER BY controllers_removed DESC, fs.id
LIMIT 10;

-- =============================================================================
-- STEP 3: EXECUTION - Actually clean the data (only if dry_run = false)
-- =============================================================================

-- Update the controller_callsigns JSONB field to remove invalid controllers
UPDATE flight_summaries 
SET 
    controller_callsigns = (
        SELECT jsonb_object_agg(key, value)
        FROM jsonb_each(controller_callsigns) AS t(key, value)
        WHERE t.key IN (SELECT callsign FROM valid_controllers)
    ),
    -- Update the enrichment_completed_at timestamp to reflect the cleanup
    enrichment_completed_at = CASE 
        WHEN :dry_run THEN enrichment_completed_at  -- Don't update in dry run
        ELSE now()  -- Update timestamp when actually cleaning
    END
WHERE enrichment_status = 'completed'
AND controller_callsigns != '{}'::jsonb
AND EXISTS (
    SELECT 1 
    FROM jsonb_object_keys(controller_callsigns) AS t(key)
    WHERE t.key NOT IN (SELECT callsign FROM valid_controllers)
)
AND NOT :dry_run;  -- Only execute if not dry run

-- =============================================================================
-- STEP 4: VERIFICATION - Show results after cleanup
-- =============================================================================

-- Show summary of cleanup results
SELECT 
    CASE WHEN :dry_run THEN 'DRY RUN COMPLETE' 
         ELSE 'CLEANUP COMPLETE' 
    END as status,
    COUNT(*) as total_flights_with_controllers,
    COUNT(CASE WHEN controller_callsigns = '{}'::jsonb THEN 1 END) as flights_with_no_controllers,
    COUNT(CASE WHEN controller_callsigns != '{}'::jsonb THEN 1 END) as flights_with_valid_controllers
FROM flight_summaries 
WHERE enrichment_status = 'completed';

-- Show remaining controller callsigns (should all be valid now)
SELECT 
    'REMAINING CONTROLLERS' as info,
    jsonb_object_keys(controller_callsigns) as controller_callsign,
    COUNT(*) as flight_count
FROM flight_summaries 
WHERE enrichment_status = 'completed'
AND controller_callsigns != '{}'::jsonb
GROUP BY jsonb_object_keys(controller_callsigns)
ORDER BY flight_count DESC
LIMIT 20;

-- =============================================================================
-- CLEANUP
-- =============================================================================
DROP TABLE valid_controllers;
