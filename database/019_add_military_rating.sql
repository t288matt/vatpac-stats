-- Migration 019: Add military_rating field to flights table
-- This migration adds the military_rating field that is available in the VATSIM API
-- but was not previously stored in our database

-- Add military_rating field
ALTER TABLE flights ADD COLUMN IF NOT EXISTS military_rating INTEGER;

-- Add comment for documentation
COMMENT ON COLUMN flights.military_rating IS 'Military rating from VATSIM API "military_rating" field';

-- Verify the migration
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'flights' 
    AND column_name = 'military_rating';
