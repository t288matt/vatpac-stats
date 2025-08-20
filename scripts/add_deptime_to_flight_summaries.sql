-- ============================================================================
-- PRODUCTION MIGRATION: Add deptime field to flight_summaries table
-- ============================================================================
-- This script safely adds the deptime field to existing flight_summaries tables
-- in production environments.
--
-- SAFETY FEATURES:
-- - Checks if field already exists before adding
-- - Uses IF NOT EXISTS to prevent errors
-- - Includes rollback instructions
-- - Logs all operations
--
-- RUNNING INSTRUCTIONS:
-- 1. Backup your database first: pg_dump your_database > backup_before_deptime.sql
-- 2. Run this script in your production database
-- 3. Verify the field was added: \d flight_summaries
-- 4. Test with a sample query
--
-- ROLLBACK INSTRUCTIONS:
-- If you need to rollback, run: ALTER TABLE flight_summaries DROP COLUMN IF EXISTS deptime;
-- ============================================================================

-- Start transaction for safe execution
BEGIN;

-- Log the start of migration
DO $$
BEGIN
    RAISE NOTICE 'Starting deptime field migration for flight_summaries table...';
    RAISE NOTICE 'Timestamp: %', NOW();
END $$;

-- Check if the deptime field already exists
DO $$
DECLARE
    column_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'flight_summaries' 
        AND column_name = 'deptime'
        AND table_schema = 'public'
    ) INTO column_exists;
    
    IF column_exists THEN
        RAISE NOTICE 'deptime field already exists in flight_summaries table. Skipping migration.';
    ELSE
        RAISE NOTICE 'deptime field does not exist. Proceeding with migration...';
    END IF;
END $$;

-- Add the deptime field if it doesn't exist
-- This is safe to run multiple times due to IF NOT EXISTS
ALTER TABLE flight_summaries 
ADD COLUMN IF NOT EXISTS deptime VARCHAR(10);

-- Verify the field was added
DO $$
DECLARE
    column_exists BOOLEAN;
    column_type TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'flight_summaries' 
        AND column_name = 'deptime'
        AND table_schema = 'public'
    ) INTO column_exists;
    
    IF column_exists THEN
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = 'flight_summaries' 
        AND column_name = 'deptime'
        AND table_schema = 'public'
        INTO column_type;
        
        RAISE NOTICE 'SUCCESS: deptime field added to flight_summaries table';
        RAISE NOTICE 'Field type: %', column_type;
        RAISE NOTICE 'Field allows NULL values (existing records will have NULL deptime)';
    ELSE
        RAISE EXCEPTION 'FAILED: deptime field was not added to flight_summaries table';
    END IF;
END $$;

-- Add comment to the new field for documentation
COMMENT ON COLUMN flight_summaries.deptime IS 'Departure time from flight_plan.deptime - represents planned departure time from flight plans';

-- Log the completion
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully at %', NOW();
    RAISE NOTICE 'deptime field is now available in flight_summaries table';
    RAISE NOTICE 'Existing records will have NULL deptime values (this is expected)';
    RAISE NOTICE 'New flight summaries will populate this field when available';
END $$;

-- Commit the transaction
COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES (run these to confirm the migration worked)
-- ============================================================================

-- Check if the field exists
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'flight_summaries' 
    AND column_name = 'deptime'
    AND table_schema = 'public';

-- Check the table structure
\d flight_summaries;

-- Sample query to test the new field
SELECT 
    callsign,
    departure,
    arrival,
    deptime,
    created_at
FROM flight_summaries 
LIMIT 5;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- The deptime field has been successfully added to your flight_summaries table.
-- 
-- NEXT STEPS:
-- 1. Update your application code to use the new deptime field
-- 2. Test the field with new flight summaries
-- 3. Consider backfilling historical data if needed (optional)
-- 4. Monitor for any issues in your logs
--
-- If you encounter any problems, you can rollback using:
-- ALTER TABLE flight_summaries DROP COLUMN IF EXISTS deptime;
-- ============================================================================
