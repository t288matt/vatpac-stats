-- Flight Tracking Enhancement Migration
-- This script adds database constraints and indexes to ensure every flight position update is preserved

-- Add unique constraint to prevent duplicate flight records for same callsign and timestamp
ALTER TABLE flights ADD CONSTRAINT unique_flight_timestamp 
UNIQUE (callsign, last_updated);

-- Add index for performance on callsign and timestamp
CREATE INDEX idx_flights_callsign_timestamp ON flights(callsign, last_updated);

-- Add index for flight track queries (optimized for time-based queries)
CREATE INDEX idx_flights_callsign_last_updated ON flights(callsign, last_updated);

-- Add comment for documentation
COMMENT ON CONSTRAINT unique_flight_timestamp ON flights IS 'Prevents duplicate flight records for same callsign and timestamp';

-- Verify the migration was successful
SELECT 
    constraint_name,
    constraint_type,
    table_name
FROM information_schema.table_constraints 
WHERE table_name = 'flights' 
    AND constraint_name = 'unique_flight_timestamp';

-- Show the new indexes
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes 
WHERE tablename = 'flights' 
    AND indexname LIKE '%callsign%'; 