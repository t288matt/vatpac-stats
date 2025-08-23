-- Migration Script: Add airborne_controller_time_percentage field
-- This script adds the new field to existing flight_summaries and flights_archive tables
-- Run this script to update existing database schemas

-- Add field to flight_summaries table
ALTER TABLE flight_summaries 
ADD COLUMN IF NOT EXISTS airborne_controller_time_percentage DECIMAL(5,2);

-- Add field to flights_archive table  
ALTER TABLE flights_archive 
ADD COLUMN IF NOT EXISTS airborne_controller_time_percentage DECIMAL(5,2);

-- Add constraint to flight_summaries table
ALTER TABLE flight_summaries 
ADD CONSTRAINT IF NOT EXISTS valid_airborne_controller_time 
CHECK (airborne_controller_time_percentage >= 0 AND airborne_controller_time_percentage <= 100);

-- Add constraint to flights_archive table
ALTER TABLE flights_archive 
ADD CONSTRAINT IF NOT EXISTS valid_airborne_controller_time 
CHECK (airborne_controller_time_percentage >= 0 AND airborne_controller_time_percentage <= 100);

-- Update existing records to have NULL value (will be calculated when summaries are recreated)
UPDATE flight_summaries 
SET airborne_controller_time_percentage = NULL 
WHERE airborne_controller_time_percentage IS NOT NULL;

UPDATE flights_archive 
SET airborne_controller_time_percentage = NULL 
WHERE airborne_controller_time_percentage IS NOT NULL;

-- Add comment to document the new field
COMMENT ON COLUMN flight_summaries.airborne_controller_time_percentage IS 
'Percentage of airborne time spent in ATC contact (calculated from sector occupancy and transceiver data)';

COMMENT ON COLUMN flights_archive.airborne_controller_time_percentage IS 
'Percentage of airborne time spent in ATC contact (calculated from sector occupancy and transceiver data)';

-- Verify the changes
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name IN ('flight_summaries', 'flights_archive')
AND column_name = 'airborne_controller_time_percentage'
ORDER BY table_name;

