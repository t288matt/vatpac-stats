-- Migration Script: Add airborne_controller_time_percentage field to flight_summaries
-- Run this script on existing databases to add the new field
-- 
-- This field tracks the percentage of airborne time a flight spent under ATC control
-- (as opposed to total time including ground operations)

-- Check if the column already exists before adding it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'flight_summaries' 
        AND column_name = 'airborne_controller_time_percentage'
    ) THEN
        -- Add the new column
        ALTER TABLE flight_summaries 
        ADD COLUMN airborne_controller_time_percentage DECIMAL(5,2);
        
        -- Add comment for documentation
        COMMENT ON COLUMN flight_summaries.airborne_controller_time_percentage 
        IS 'Percentage of airborne time on ATC (0.00 to 999.99)';
        
        -- Add constraint to ensure valid percentage range
        ALTER TABLE flight_summaries 
        ADD CONSTRAINT valid_airborne_controller_time 
        CHECK (airborne_controller_time_percentage >= 0 AND airborne_controller_time_percentage <= 100);
        
        RAISE NOTICE 'Successfully added airborne_controller_time_percentage field to flight_summaries table';
    ELSE
        RAISE NOTICE 'Column airborne_controller_time_percentage already exists in flight_summaries table';
    END IF;
END $$;

-- Verify the column was added
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'flight_summaries' 
    AND column_name = 'airborne_controller_time_percentage';

-- Show the updated table structure
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'flight_summaries' 
ORDER BY ordinal_position;
