-- Create Indexes for Controller Summaries Table
-- These indexes optimize query performance for common access patterns

-- Basic lookup indexes
CREATE INDEX IF NOT EXISTS idx_controller_summaries_callsign ON controller_summaries(callsign);
CREATE INDEX IF NOT EXISTS idx_controller_summaries_session_time ON controller_summaries(session_start_time, session_end_time);
CREATE INDEX IF NOT EXISTS idx_controller_summaries_aircraft_count ON controller_summaries(total_aircraft_handled);
CREATE INDEX IF NOT EXISTS idx_controller_summaries_rating ON controller_summaries(rating);
CREATE INDEX IF NOT EXISTS idx_controller_summaries_facility ON controller_summaries(facility);

-- JSONB indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_controller_summaries_frequencies ON controller_summaries USING GIN(frequencies_used);
CREATE INDEX IF NOT EXISTS idx_controller_summaries_aircraft_details ON controller_summaries USING GIN(aircraft_details);
CREATE INDEX IF NOT EXISTS idx_controller_summaries_hourly_breakdown ON controller_summaries USING GIN(hourly_aircraft_breakdown);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_controller_summaries_callsign_session ON controller_summaries(callsign, session_start_time);
CREATE INDEX IF NOT EXISTS idx_controller_summaries_rating_facility ON controller_summaries(rating, facility);
CREATE INDEX IF NOT EXISTS idx_controller_summaries_duration_aircraft ON controller_summaries(session_duration_minutes, total_aircraft_handled);

-- Add comments
COMMENT ON INDEX idx_controller_summaries_callsign IS 'Optimizes callsign lookups';
COMMENT ON INDEX idx_controller_summaries_session_time IS 'Optimizes time range queries';
COMMENT ON INDEX idx_controller_summaries_frequencies IS 'Optimizes frequency-based queries using GIN';
COMMENT ON INDEX idx_controller_summaries_callsign_session IS 'Optimizes callsign + time range queries';
