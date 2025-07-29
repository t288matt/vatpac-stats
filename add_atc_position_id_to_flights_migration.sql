-- Migration: Add atc_position_id column to flights table
-- This links flights to ATC positions instead of controllers

-- Add the foreign key column
ALTER TABLE flights ADD COLUMN atc_position_id INTEGER REFERENCES atc_positions(id);

-- Create an index for better performance
CREATE INDEX idx_flights_atc_position_id ON flights(atc_position_id);

-- Add a comment to document the change
COMMENT ON COLUMN flights.atc_position_id IS 'Foreign key to atc_positions table';

-- Verify the migration
SELECT column_name, data_type, is_nullable FROM information_schema.columns 
WHERE table_name = 'flights' AND column_name = 'atc_position_id'; 