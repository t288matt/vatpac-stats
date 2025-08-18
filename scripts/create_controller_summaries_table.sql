-- Create Controller Summaries Table
-- This table stores pre-computed summary data for completed controller sessions

CREATE TABLE IF NOT EXISTS controller_summaries (
    id BIGSERIAL PRIMARY KEY,
    
    -- Controller Identity
    callsign VARCHAR(50) NOT NULL,
    cid INTEGER,
    name VARCHAR(100),
    
    -- Session Summary
    session_start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    session_end_time TIMESTAMP WITH TIME ZONE,
    session_duration_minutes INTEGER DEFAULT 0,
    
    -- Controller Details
    rating INTEGER,
    facility INTEGER,
    server VARCHAR(50),
    
    -- Aircraft Activity
    total_aircraft_handled INTEGER DEFAULT 0,
    peak_aircraft_count INTEGER DEFAULT 0,
    hourly_aircraft_breakdown JSONB,
    frequencies_used JSONB,
    aircraft_details JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_session_duration CHECK (
        session_duration_minutes = EXTRACT(EPOCH FROM (session_end_time - session_start_time)) / 60
        OR session_end_time IS NULL
    ),
    CONSTRAINT valid_aircraft_counts CHECK (
        total_aircraft_handled >= 0 
        AND peak_aircraft_count >= 0 
        AND peak_aircraft_count <= total_aircraft_handled
    ),
    CONSTRAINT valid_session_times CHECK (
        session_end_time IS NULL OR session_end_time > session_start_time
    ),
    CONSTRAINT valid_rating CHECK (rating >= 1 AND rating <= 11)
);

-- Add comment to table
COMMENT ON TABLE controller_summaries IS 'Pre-computed summary data for completed controller sessions to improve query performance';
