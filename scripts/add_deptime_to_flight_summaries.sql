-- Migration script to add deptime column to flight_summaries table
-- This script adds the deptime field that was missing from existing deployments

-- Add deptime column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'flight_summaries' 
        AND column_name = 'deptime'
    ) THEN
        ALTER TABLE flight_summaries ADD COLUMN deptime VARCHAR(10);
        COMMENT ON COLUMN flight_summaries.deptime IS 'Departure time from flight plan';
        
        RAISE NOTICE 'Added deptime column to flight_summaries table';
    ELSE
        RAISE NOTICE 'deptime column already exists in flight_summaries table';
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'flight_summaries' 
AND column_name = 'deptime';
