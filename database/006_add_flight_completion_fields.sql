-- Migration 006: Add Flight Completion System Fields
-- Adds completion tracking fields to support hybrid landing detection + time-based fallback

-- Add completion tracking fields to flights table
ALTER TABLE flights ADD COLUMN completed_at TIMESTAMP;
ALTER TABLE flights ADD COLUMN completion_method VARCHAR(20); -- 'landing', 'time', 'manual'
ALTER TABLE flights ADD COLUMN completion_confidence FLOAT;

-- Add completion tracking fields to traffic_movements table
ALTER TABLE traffic_movements ADD COLUMN flight_completion_triggered BOOLEAN DEFAULT FALSE;
ALTER TABLE traffic_movements ADD COLUMN completion_timestamp TIMESTAMP;
ALTER TABLE traffic_movements ADD COLUMN completion_confidence FLOAT;

-- Add indexes for completion queries
CREATE INDEX idx_flights_completion_method ON flights(completion_method, completed_at);
CREATE INDEX idx_traffic_movements_completion ON traffic_movements(aircraft_callsign, movement_type, flight_completion_triggered);
CREATE INDEX idx_traffic_movements_completion_time ON traffic_movements(completion_timestamp);

-- Add check constraint for completion_method
ALTER TABLE flights ADD CONSTRAINT check_completion_method 
CHECK (completion_method IN ('landing', 'time', 'manual') OR completion_method IS NULL);

-- Update existing completed flights to have completion method
UPDATE flights 
SET completion_method = 'time', completed_at = last_updated 
WHERE status = 'completed' AND completion_method IS NULL;

-- Add comment to document the migration
COMMENT ON TABLE flights IS 'Enhanced with flight completion tracking fields';
COMMENT ON TABLE traffic_movements IS 'Enhanced with flight completion trigger tracking'; 