-- Migration: Remove unused system_config table
-- Description: Drops the system_config table as it's not used by any application code
-- Date: 2025-01-27
-- Reason: Code analysis revealed no reads/writes to this table - only environment variables are used

-- Check if table exists before dropping
DO $$ 
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'system_config') THEN
        -- Drop the table and all its dependencies
        DROP TABLE system_config CASCADE;
        RAISE NOTICE 'system_config table dropped successfully';
    ELSE
        RAISE NOTICE 'system_config table does not exist, skipping';
    END IF;
END $$;

-- Verify table has been removed
SELECT 
    CASE 
        WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'system_config') 
        THEN 'ERROR: system_config table still exists'
        ELSE 'SUCCESS: system_config table removed'
    END as migration_status;
