-- Migration: Remove Traffic Movements Table
-- Phase 3: Traffic Analysis Service Removal
-- Date: 2025-08-09
-- Description: Remove traffic_movements table, indexes, and triggers

-- Begin transaction for atomic operation
BEGIN;

-- Check if table exists before attempting to drop
DO $$ 
BEGIN 
    -- Drop trigger if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.triggers 
        WHERE trigger_name = 'update_traffic_movements_updated_at'
    ) THEN
        DROP TRIGGER IF EXISTS update_traffic_movements_updated_at ON traffic_movements;
        RAISE NOTICE 'Dropped trigger: update_traffic_movements_updated_at';
    END IF;

    -- Drop indexes if they exist
    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_traffic_movements_airport'
    ) THEN
        DROP INDEX IF EXISTS idx_traffic_movements_airport;
        RAISE NOTICE 'Dropped index: idx_traffic_movements_airport';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_traffic_movements_timestamp'
    ) THEN
        DROP INDEX IF EXISTS idx_traffic_movements_timestamp;
        RAISE NOTICE 'Dropped index: idx_traffic_movements_timestamp';
    END IF;

    -- Drop table if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'traffic_movements' AND table_schema = 'public'
    ) THEN
        DROP TABLE IF EXISTS traffic_movements CASCADE;
        RAISE NOTICE 'Dropped table: traffic_movements';
    ELSE
        RAISE NOTICE 'Table traffic_movements does not exist, skipping drop';
    END IF;

END $$;

-- Verify the removal
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'traffic_movements' AND table_schema = 'public'
        ) 
        THEN 'ERROR: traffic_movements table still exists'
        ELSE 'SUCCESS: traffic_movements table removed'
    END as migration_status;

-- List remaining tables to confirm
SELECT 'Remaining tables:' as info;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

COMMIT;

-- Log migration completion
INSERT INTO migration_log (migration_file, applied_at, description) 
VALUES (
    '018_remove_traffic_movements_table.sql', 
    NOW(), 
    'Removed traffic_movements table, indexes, and triggers - Traffic Analysis Service removal Phase 3'
) ON CONFLICT DO NOTHING;
