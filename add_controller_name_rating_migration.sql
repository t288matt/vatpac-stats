-- Migration: Add controller_name and controller_rating fields to controllers table
-- This allows storing the controller's real name and rating from VATSIM API

-- Add controller_name column to controllers table
ALTER TABLE controllers ADD COLUMN controller_name VARCHAR(100);

-- Add controller_rating column to controllers table
ALTER TABLE controllers ADD COLUMN controller_rating INTEGER;

-- Create index on controller_rating for efficient queries
CREATE INDEX idx_controllers_rating ON controllers(controller_rating);

-- Add comments explaining the fields
COMMENT ON COLUMN controllers.controller_name IS 'Controller real name from VATSIM API';
COMMENT ON COLUMN controllers.controller_rating IS 'Controller rating (0-5) from VATSIM API';

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'controllers' 
AND column_name IN ('controller_name', 'controller_rating')
ORDER BY column_name; 