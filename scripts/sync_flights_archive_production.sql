-- Production Script: Sync flights_archive table with flight_summaries
-- This script adds missing fields and populates data from flight_summaries
-- Run this in production to ensure flights_archive has all required fields

-- Phase 1: Add missing columns (idempotent - safe to run multiple times)
DO $$
BEGIN
    -- Add deptime column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'deptime') THEN
        ALTER TABLE flights_archive ADD COLUMN deptime TIMESTAMP WITH TIME ZONE;
        COMMENT ON COLUMN flights_archive.deptime IS 'Departure time from flight plan';
    END IF;

    -- Add controller_callsigns column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'controller_callsigns') THEN
        ALTER TABLE flights_archive ADD COLUMN controller_callsigns JSONB;
        COMMENT ON COLUMN flights_archive.controller_callsigns IS 'JSON array of controller callsigns that handled this flight';
    END IF;

    -- Add controller_time_percentage column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'controller_time_percentage') THEN
        ALTER TABLE flights_archive ADD COLUMN controller_time_percentage NUMERIC(5,2);
        COMMENT ON COLUMN flights_archive.controller_time_percentage IS 'Percentage of flight time under ATC control';
    END IF;

    -- Add time_online_minutes column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'time_online_minutes') THEN
        ALTER TABLE flights_archive ADD COLUMN time_online_minutes INTEGER;
        COMMENT ON COLUMN flights_archive.time_online_minutes IS 'Total time online in minutes';
    END IF;

    -- Add primary_enroute_sector column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'primary_enroute_sector') THEN
        ALTER TABLE flights_archive ADD COLUMN primary_enroute_sector TEXT;
        COMMENT ON COLUMN flights_archive.primary_enroute_sector IS 'Primary enroute sector for this flight';
    END IF;

    -- Add total_enroute_sectors column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'total_enroute_sectors') THEN
        ALTER TABLE flights_archive ADD COLUMN total_enroute_sectors INTEGER;
        COMMENT ON COLUMN flights_archive.total_enroute_sectors IS 'Total number of enroute sectors traversed';
    END IF;

    -- Add total_enroute_time_minutes column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'total_enroute_time_minutes') THEN
        ALTER TABLE flights_archive ADD COLUMN total_enroute_time_minutes INTEGER;
        COMMENT ON COLUMN flights_archive.total_enroute_time_minutes IS 'Total time spent in enroute sectors in minutes';
    END IF;

    -- Add sector_breakdown column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'sector_breakdown') THEN
        ALTER TABLE flights_archive ADD COLUMN sector_breakdown JSONB;
        COMMENT ON COLUMN flights_archive.sector_breakdown IS 'Detailed breakdown of sector occupancy times';
    END IF;

    -- Add completion_time column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'completion_time') THEN
        ALTER TABLE flights_archive ADD COLUMN completion_time TIMESTAMP WITH TIME ZONE;
        COMMENT ON COLUMN flights_archive.completion_time IS 'Time when flight summary was completed';
    END IF;

    -- Add updated_at column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'flights_archive' AND column_name = 'updated_at') THEN
        ALTER TABLE flights_archive ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        COMMENT ON COLUMN flights_archive.updated_at IS 'Last update timestamp';
    END IF;
END $$;

-- Phase 2: Create indexes for performance (idempotent)
DO $$
BEGIN
    -- Create index on deptime if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'flights_archive' AND indexname = 'idx_flights_archive_deptime') THEN
        CREATE INDEX idx_flights_archive_deptime ON flights_archive(deptime);
    END IF;

    -- Create index on controller_callsigns if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'flights_archive' AND indexname = 'idx_flights_archive_controller_callsigns') THEN
        CREATE INDEX idx_flights_archive_controller_callsigns ON flights_archive USING GIN(controller_callsigns);
    END IF;

    -- Create index on primary_enroute_sector if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'flights_archive' AND indexname = 'idx_flights_archive_primary_sector') THEN
        CREATE INDEX idx_flights_archive_primary_sector ON flights_archive(primary_enroute_sector);
    END IF;

    -- Create index on sector_breakdown if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'flights_archive' AND indexname = 'idx_flights_archive_sector_breakdown') THEN
        CREATE INDEX idx_flights_archive_sector_breakdown ON flights_archive USING GIN(sector_breakdown);
    END IF;

    -- Create index on controller_time_percentage if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'flights_archive' AND indexname = 'idx_flights_archive_controller_time') THEN
        CREATE INDEX idx_flights_archive_controller_time ON flights_archive(controller_time_percentage);
    END IF;
END $$;

-- Phase 2.5: Create triggers for updated_at columns
DO $$
BEGIN
    -- Create trigger for updated_at on flights_archive if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_flights_archive_updated_at') THEN
        CREATE TRIGGER update_flights_archive_updated_at 
            BEFORE UPDATE ON flights_archive 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Phase 3: Populate missing data from flight_summaries
-- Update deptime
UPDATE flights_archive 
SET deptime = fs.deptime
FROM flight_summaries fs 
WHERE flights_archive.callsign = fs.callsign 
  AND flights_archive.deptime IS NULL 
  AND fs.deptime IS NOT NULL;

-- Update controller_callsigns
UPDATE flights_archive 
SET controller_callsigns = fs.controller_callsigns
FROM flight_summaries fs 
WHERE flights_archive.callsign = fs.callsign 
  AND flights_archive.controller_callsigns IS NULL 
  AND fs.controller_callsigns IS NOT NULL;

-- Update controller_time_percentage
UPDATE flights_archive 
SET controller_time_percentage = fs.controller_time_percentage
FROM flight_summaries fs 
WHERE flights_archive.callsign = fs.callsign 
  AND flights_archive.controller_time_percentage IS NULL 
  AND fs.controller_time_percentage IS NOT NULL;

-- Update time_online_minutes
UPDATE flights_archive 
SET time_online_minutes = fs.time_online_minutes
FROM flight_summaries fs 
WHERE flights_archive.callsign = fs.callsign 
  AND flights_archive.time_online_minutes IS NULL 
  AND fs.time_online_minutes IS NOT NULL;

-- Update primary_enroute_sector
UPDATE flights_archive 
SET primary_enroute_sector = fs.primary_enroute_sector
FROM flight_summaries fs 
WHERE flights_archive.callsign = fs.callsign 
  AND flights_archive.primary_enroute_sector IS NULL 
  AND fs.primary_enroute_sector IS NOT NULL;

-- Update total_enroute_sectors
UPDATE flights_archive 
SET total_enroute_sectors = fs.total_enroute_sectors
FROM flight_summaries fs 
WHERE flights_archive.callsign = fs.callsign 
  AND flights_archive.total_enroute_sectors IS NULL 
  AND fs.total_enroute_sectors IS NOT NULL;

-- Update total_enroute_time_minutes
UPDATE flights_archive 
SET total_enroute_time_minutes = fs.total_enroute_time_minutes
FROM flight_summaries fs 
WHERE flights_archive.callsign = fs.callsign 
  AND flights_archive.total_enroute_time_minutes IS NULL 
  AND fs.total_enroute_time_minutes IS NOT NULL;

-- Update sector_breakdown
UPDATE flights_archive 
SET sector_breakdown = fs.sector_breakdown
FROM flight_summaries fs 
WHERE flights_archive.callsign = fs.callsign 
  AND flights_archive.sector_breakdown IS NULL 
  AND fs.sector_breakdown IS NOT NULL;

-- Update completion_time
UPDATE flights_archive 
SET completion_time = fs.completion_time
FROM flight_summaries fs 
WHERE flights_archive.callsign = fs.callsign 
  AND flights_archive.completion_time IS NULL 
  AND fs.completion_time IS NOT NULL;

-- Phase 4: Report results
SELECT 
    'Sync completed' as status,
    COUNT(*) as total_flights_archive_records,
    COUNT(deptime) as records_with_deptime,
    COUNT(controller_callsigns) as records_with_controller_callsigns,
    COUNT(controller_time_percentage) as records_with_controller_time,
    COUNT(time_online_minutes) as records_with_time_online,
    COUNT(primary_enroute_sector) as records_with_primary_sector,
    COUNT(total_enroute_sectors) as records_with_total_sectors,
    COUNT(total_enroute_time_minutes) as records_with_total_time,
    COUNT(sector_breakdown) as records_with_sector_breakdown,
    COUNT(completion_time) as records_with_completion_time
FROM flights_archive;
