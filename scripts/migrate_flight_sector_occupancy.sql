-- Migration Script: Add flight identification fields to flight_sector_occupancy table
-- This script adds cid, logon_time, departure, and arrival columns to enable
-- unique flight identification and proper ATC coverage calculations.

-- Add new columns
ALTER TABLE flight_sector_occupancy 
ADD COLUMN IF NOT EXISTS cid INTEGER,
ADD COLUMN IF NOT EXISTS logon_time TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS departure VARCHAR(10),
ADD COLUMN IF NOT EXISTS arrival VARCHAR(10);

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_cid ON flight_sector_occupancy(cid);
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_logon_time ON flight_sector_occupancy(logon_time);
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_departure ON flight_sector_occupancy(departure);
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_arrival ON flight_sector_occupancy(arrival);

-- Create composite index for unique flight identification
CREATE INDEX IF NOT EXISTS idx_flight_sector_occupancy_flight_identifier 
ON flight_sector_occupancy(callsign, cid, logon_time, departure, arrival);

-- Update existing records to populate the new fields where possible
-- This will link existing sector records to flight data
UPDATE flight_sector_occupancy fso
SET 
    cid = f.cid,
    logon_time = f.logon_time,
    departure = f.departure,
    arrival = f.arrival
FROM flights f
WHERE fso.callsign = f.callsign
AND fso.entry_timestamp BETWEEN f.logon_time AND COALESCE(f.logon_time + INTERVAL '24 hours', f.logon_time + INTERVAL '24 hours')
AND fso.cid IS NULL;

-- Verify the migration
SELECT 
    'Migration completed' as status,
    COUNT(*) as total_records,
    COUNT(cid) as records_with_cid,
    COUNT(logon_time) as records_with_logon_time,
    COUNT(departure) as records_with_departure,
    COUNT(arrival) as records_with_arrival
FROM flight_sector_occupancy;
