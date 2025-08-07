-- Migration: Remove Flight Status System Fields
-- This migration removes all flight status related fields from the database
-- as the status system is being completely removed from the application.

-- Remove status-related fields from flights table
ALTER TABLE flights DROP COLUMN IF EXISTS status;
ALTER TABLE flights DROP COLUMN IF EXISTS landed_at;
ALTER TABLE flights DROP COLUMN IF EXISTS completed_at;
ALTER TABLE flights DROP COLUMN IF EXISTS completion_method;
ALTER TABLE flights DROP COLUMN IF EXISTS completion_confidence;
ALTER TABLE flights DROP COLUMN IF EXISTS pilot_disconnected_at;
ALTER TABLE flights DROP COLUMN IF EXISTS disconnect_method;

-- Remove status-related fields from traffic_movements table
ALTER TABLE traffic_movements DROP COLUMN IF EXISTS flight_completion_triggered;
ALTER TABLE traffic_movements DROP COLUMN IF EXISTS completion_timestamp;
ALTER TABLE traffic_movements DROP COLUMN IF EXISTS completion_confidence;

-- Remove status-related fields from flight_summaries table
ALTER TABLE flight_summaries DROP COLUMN IF EXISTS completed_at;

-- Remove status-related fields from frequency_matches table
ALTER TABLE frequency_matches DROP COLUMN IF EXISTS is_active;

-- Remove status-related indexes
DROP INDEX IF EXISTS idx_flights_status;
DROP INDEX IF EXISTS idx_flight_summaries_completed;
DROP INDEX IF EXISTS idx_frequency_matches_active_timestamp;

-- Update the default value for last_updated to ensure it's properly set
ALTER TABLE flights ALTER COLUMN last_updated SET DEFAULT NOW();

-- Add comment to document the removal
COMMENT ON TABLE flights IS 'Flight data without status system - simplified for core tracking only';
COMMENT ON TABLE traffic_movements IS 'Traffic movements without flight completion tracking';
COMMENT ON TABLE flight_summaries IS 'Flight summaries without completion timestamps';
COMMENT ON TABLE frequency_matches IS 'Frequency matches without active status tracking';
