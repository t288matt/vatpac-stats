-- Migration to add missing VATSIM API fields to controllers table
-- This adds the fields that map from VATSIM API to our database

-- Add controller_id field (from API "cid")
ALTER TABLE controllers ADD COLUMN IF NOT EXISTS controller_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_controllers_controller_id ON controllers(controller_id);

-- Add controller_name field (from API "name") 
ALTER TABLE controllers ADD COLUMN IF NOT EXISTS controller_name VARCHAR(100);

-- Add controller_rating field (from API "rating")
ALTER TABLE controllers ADD COLUMN IF NOT EXISTS controller_rating INTEGER;

-- Update existing records to set default values
UPDATE controllers SET 
    controller_id = NULL,
    controller_name = NULL,
    controller_rating = NULL
WHERE controller_id IS NULL;

-- Add comments to document the field mapping
COMMENT ON COLUMN controllers.controller_id IS 'VATSIM API cid - Controller ID from VATSIM';
COMMENT ON COLUMN controllers.controller_name IS 'VATSIM API name - Controller name from VATSIM';
COMMENT ON COLUMN controllers.controller_rating IS 'VATSIM API rating - Controller rating from VATSIM'; 