-- Manual Migration: Add altitude fields to flight_sector_occupancy table
-- Run this SQL directly in your PostgreSQL database

-- Add the new altitude fields
ALTER TABLE flight_sector_occupancy 
ADD COLUMN IF NOT EXISTS entry_altitude INTEGER,
ADD COLUMN IF NOT EXISTS exit_altitude INTEGER;

-- Add comments for documentation
COMMENT ON COLUMN flight_sector_occupancy.entry_altitude IS 'Altitude in feet when flight entered the sector';
COMMENT ON COLUMN flight_sector_occupancy.exit_altitude IS 'Altitude in feet when flight exited the sector';

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'flight_sector_occupancy' 
    AND column_name IN ('entry_altitude', 'exit_altitude')
ORDER BY column_name;

-- Show the complete table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'flight_sector_occupancy'
ORDER BY ordinal_position;
