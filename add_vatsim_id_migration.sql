-- Migration: Add vatsim_id field to controllers table
-- This allows tracking multiple sectors controlled by the same VATSIM user

-- Add vatsim_id column to controllers table
ALTER TABLE controllers ADD COLUMN vatsim_id VARCHAR(50);

-- Create index on vatsim_id for efficient queries
CREATE INDEX idx_controllers_vatsim_id ON controllers(vatsim_id);

-- Add comment explaining the field
COMMENT ON COLUMN controllers.vatsim_id IS 'VATSIM user ID that links multiple sectors controlled by the same controller';

-- Update existing controllers (placeholder - will be populated by VATSIM API data)
-- UPDATE controllers SET vatsim_id = 'unknown' WHERE vatsim_id IS NULL;

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'controllers' 
AND column_name = 'vatsim_id'; 