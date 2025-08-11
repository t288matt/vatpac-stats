-- Migration 020: Add height fields to transceivers table
-- This migration adds the height fields that are available in the VATSIM API
-- but were not previously stored in our database

-- Add new height fields
ALTER TABLE transceivers ADD COLUMN IF NOT EXISTS height_msl DOUBLE PRECISION;
ALTER TABLE transceivers ADD COLUMN IF NOT EXISTS height_agl DOUBLE PRECISION;

-- Add comments for documentation
COMMENT ON COLUMN transceivers.height_msl IS 'Height above mean sea level in meters from VATSIM API heightMslM';
COMMENT ON COLUMN transceivers.height_agl IS 'Height above ground level in meters from VATSIM API heightAglM';

-- Verify the migration
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'transceivers' 
    AND column_name IN ('height_msl', 'height_agl')
ORDER BY column_name;
