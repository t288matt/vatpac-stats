-- Production Controller Tables Creation Script
-- This script creates the controller_summaries and controllers_archive tables
-- along with all necessary indexes and triggers for production use

-- =====================================================
-- 1. CREATE CONTROLLER SUMMARIES TABLE
-- =====================================================

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

-- =====================================================
-- 2. CREATE CONTROLLERS ARCHIVE TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS controllers_archive (
    id INTEGER PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    frequency VARCHAR(20),
    cid INTEGER,
    name VARCHAR(100),
    rating INTEGER,
    facility INTEGER,
    visual_range INTEGER,
    text_atis TEXT,
    server VARCHAR(50),
    last_updated TIMESTAMP(0) WITH TIME ZONE,
    logon_time TIMESTAMP(0) WITH TIME ZONE,
    created_at TIMESTAMP(0) WITH TIME ZONE,
    updated_at TIMESTAMP(0) WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add comment to table
COMMENT ON TABLE controllers_archive IS 'Archive table for old controller records before deletion from main table';

-- =====================================================
-- 3. CREATE INDEXES FOR CONTROLLER SUMMARIES
-- =====================================================

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

-- Add comments for indexes
COMMENT ON INDEX idx_controller_summaries_callsign IS 'Optimizes callsign lookups';
COMMENT ON INDEX idx_controller_summaries_session_time IS 'Optimizes time range queries';
COMMENT ON INDEX idx_controller_summaries_frequencies IS 'Optimizes frequency-based queries using GIN';
COMMENT ON INDEX idx_controller_summaries_callsign_session IS 'Optimizes callsign + time range queries';

-- =====================================================
-- 4. CREATE INDEXES FOR CONTROLLERS ARCHIVE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_controllers_archive_callsign ON controllers_archive(callsign);
CREATE INDEX IF NOT EXISTS idx_controllers_archive_cid ON controllers_archive(cid);
CREATE INDEX IF NOT EXISTS idx_controllers_archive_archived_at ON controllers_archive(archived_at);
CREATE INDEX IF NOT EXISTS idx_controllers_archive_logon_time ON controllers_archive(logon_time);

-- =====================================================
-- 5. CREATE TRIGGERS
-- =====================================================

-- First, ensure the update_updated_at_column function exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at timestamp for controller_summaries
DROP TRIGGER IF EXISTS update_controller_summaries_updated_at ON controller_summaries;
CREATE TRIGGER update_controller_summaries_updated_at 
    BEFORE UPDATE ON controller_summaries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comment for trigger
COMMENT ON TRIGGER update_controller_summaries_updated_at ON controller_summaries IS 'Automatically updates updated_at timestamp on row updates';

-- =====================================================
-- 6. VERIFICATION QUERIES
-- =====================================================

-- Verify tables were created
SELECT 
    table_name,
    table_type
FROM information_schema.tables 
WHERE table_name IN ('controller_summaries', 'controllers_archive')
ORDER BY table_name;

-- Verify indexes were created
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('controller_summaries', 'controllers_archive')
ORDER BY tablename, indexname;

-- Verify triggers were created
SELECT 
    trigger_name,
    event_manipulation,
    event_object_table,
    action_statement
FROM information_schema.triggers 
WHERE event_object_table IN ('controller_summaries', 'controllers_archive')
ORDER BY event_object_table, trigger_name;


