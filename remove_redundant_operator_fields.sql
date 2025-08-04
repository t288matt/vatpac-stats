-- Remove redundant operator_* fields from atc_positions table
-- These fields were changed to controller_* fields and are no longer used

-- Drop the redundant columns
ALTER TABLE atc_positions DROP COLUMN IF EXISTS operator_id;
ALTER TABLE atc_positions DROP COLUMN IF EXISTS operator_name;
ALTER TABLE atc_positions DROP COLUMN IF EXISTS operator_rating;

-- Verify the changes
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'atc_positions' 
ORDER BY ordinal_position; 