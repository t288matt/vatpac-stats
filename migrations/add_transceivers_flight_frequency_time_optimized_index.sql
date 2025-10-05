-- Migration: Add transceivers flight frequency time optimized index
-- This index was added to production to improve performance for flight frequency queries
-- Date: 2025-01-27

-- Add the production performance index for flight frequency queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_flight_frequency_time_optimized 
ON transceivers (frequency, timestamp) 
WHERE entity_type = 'flight';

-- Verify the index was created
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'transceivers' 
    AND indexname = 'idx_transceivers_flight_frequency_time_optimized';

