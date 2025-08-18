-- Create Controllers Archive Table
-- This table stores old controller records before deletion from main table

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
