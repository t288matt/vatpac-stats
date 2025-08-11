-- Migration 018: Add missing flight plan fields to flights table
-- This migration adds the flight plan fields that are available in the VATSIM API
-- but were not previously stored in our database

-- Add new flight plan fields
ALTER TABLE flights ADD COLUMN IF NOT EXISTS flight_rules VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS aircraft_faa VARCHAR(20);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS alternate VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS cruise_tas VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS planned_altitude VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS deptime VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS enroute_time VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS fuel_time VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS remarks TEXT;

-- Add comments for documentation
COMMENT ON COLUMN flights.flight_rules IS 'IFR/VFR from VATSIM API flight_plan.flight_rules';
COMMENT ON COLUMN flights.aircraft_faa IS 'FAA aircraft code from VATSIM API flight_plan.aircraft_faa';
COMMENT ON COLUMN flights.alternate IS 'Alternate airport from VATSIM API flight_plan.alternate';
COMMENT ON COLUMN flights.cruise_tas IS 'True airspeed from VATSIM API flight_plan.cruise_tas';
COMMENT ON COLUMN flights.planned_altitude IS 'Planned cruise altitude from VATSIM API flight_plan.altitude';
COMMENT ON COLUMN flights.deptime IS 'Departure time from VATSIM API flight_plan.deptime';
COMMENT ON COLUMN flights.enroute_time IS 'Enroute time from VATSIM API flight_plan.enroute_time';
COMMENT ON COLUMN flights.fuel_time IS 'Fuel time from VATSIM API flight_plan.fuel_time';
COMMENT ON COLUMN flights.remarks IS 'Flight plan remarks from VATSIM API flight_plan.remarks';

-- Create indexes for the new fields that are likely to be queried
CREATE INDEX IF NOT EXISTS idx_flights_flight_rules ON flights(flight_rules);
CREATE INDEX IF NOT EXISTS idx_flights_planned_altitude ON flights(planned_altitude);

-- Verify the migration
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'flights' 
    AND column_name IN ('flight_rules', 'aircraft_faa', 'alternate', 'cruise_tas', 'planned_altitude', 'deptime', 'enroute_time', 'fuel_time', 'remarks')
ORDER BY column_name;
