-- Migration 007: Add landed status and pilot disconnect tracking
-- This migration adds support for the enhanced aircraft status system

-- Add pilot disconnect tracking fields to flights table
ALTER TABLE flights ADD COLUMN IF NOT EXISTS pilot_disconnected_at TIMESTAMP;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS disconnect_method VARCHAR(20);

-- Update status constraint to include 'landed' status
ALTER TABLE flights DROP CONSTRAINT IF EXISTS check_flight_status;
ALTER TABLE flights ADD CONSTRAINT check_flight_status 
CHECK (status IN ('active', 'stale', 'landed', 'completed', 'cancelled', 'unknown'));

-- Add index for landed status queries
CREATE INDEX IF NOT EXISTS idx_flights_status_landed ON flights(status) WHERE status = 'landed';

-- Add index for pilot disconnect tracking
CREATE INDEX IF NOT EXISTS idx_flights_pilot_disconnected ON flights(pilot_disconnected_at) WHERE pilot_disconnected_at IS NOT NULL;

-- Update existing completed flights to have proper completion data
UPDATE flights 
SET completion_method = 'time' 
WHERE status = 'completed' AND completion_method IS NULL;

-- Add comment to document the new status system
COMMENT ON COLUMN flights.status IS 'Flight status: active=flying, stale=no recent updates, landed=landed but pilot connected, completed=pilot disconnected or timeout';
COMMENT ON COLUMN flights.pilot_disconnected_at IS 'Timestamp when pilot disconnected from VATSIM';
COMMENT ON COLUMN flights.disconnect_method IS 'Method of disconnect detection: detected=API detected, timeout=time-based fallback';
