-- Migration to remove old speed fields and use only groundspeed and cruise_tas
-- This migration removes the old 'speed' and 'ground_speed' columns from flights and traffic_movements tables

-- Remove old speed columns from flights table
ALTER TABLE flights DROP COLUMN IF EXISTS speed;
ALTER TABLE flights DROP COLUMN IF EXISTS ground_speed;

-- Remove old speed column from traffic_movements table
ALTER TABLE traffic_movements DROP COLUMN IF EXISTS speed;

-- Update comments to reflect the new field structure
COMMENT ON COLUMN flights.groundspeed IS 'Ground speed from VATSIM API';
COMMENT ON COLUMN flights.cruise_tas IS 'True airspeed from VATSIM API flight plan';

-- Verify the changes
DO $$
BEGIN
    -- Check that old columns are removed
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'flights' AND column_name = 'speed') THEN
        RAISE EXCEPTION 'Old speed column still exists in flights table';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'flights' AND column_name = 'ground_speed') THEN
        RAISE EXCEPTION 'Old ground_speed column still exists in flights table';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'traffic_movements' AND column_name = 'speed') THEN
        RAISE EXCEPTION 'Old speed column still exists in traffic_movements table';
    END IF;
    
    -- Check that new columns exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'flights' AND column_name = 'groundspeed') THEN
        RAISE EXCEPTION 'New groundspeed column missing from flights table';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'flights' AND column_name = 'cruise_tas') THEN
        RAISE EXCEPTION 'New cruise_tas column missing from flights table';
    END IF;
    
    RAISE NOTICE 'Migration completed successfully - old speed fields removed, new fields verified';
END $$; 