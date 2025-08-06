-- Migration script to remove controller_id from flights table
-- This script removes the unused controller_id foreign key and related index

-- Drop the index first
DROP INDEX IF EXISTS idx_flights_controller;

-- Remove the controller_id column from flights table
ALTER TABLE flights DROP COLUMN IF EXISTS controller_id;

-- Verify the changes
-- This will show the current structure of the flights table
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'flights' 
ORDER BY ordinal_position; 