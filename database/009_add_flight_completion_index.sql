-- Add index for flight completion queries
-- This optimizes queries that find the most recent flight record by callsign

CREATE INDEX IF NOT EXISTS idx_flights_callsign_last_updated 
ON flights(callsign, last_updated DESC);

-- Add index for completion method queries
CREATE INDEX IF NOT EXISTS idx_flights_completion_method 
ON flights(completion_method) WHERE completion_method IS NOT NULL;

-- Add index for status queries
CREATE INDEX IF NOT EXISTS idx_flights_status_completion 
ON flights(status, completed_at) WHERE status = 'completed';

COMMENT ON INDEX idx_flights_callsign_last_updated IS 'Optimizes queries for finding most recent flight record by callsign';
COMMENT ON INDEX idx_flights_completion_method IS 'Optimizes queries for completion method analysis';
COMMENT ON INDEX idx_flights_status_completion IS 'Optimizes queries for completed flight analysis';
