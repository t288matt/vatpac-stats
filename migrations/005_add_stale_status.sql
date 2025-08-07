-- Migration: Add Stale Status to Flight Status System
-- Add 'stale' as a valid flight status
-- Date: 2025-08-07

-- Step 1: Drop the existing constraint
ALTER TABLE flights DROP CONSTRAINT IF EXISTS check_flight_status;

-- Step 2: Add the new constraint with 'stale' status
ALTER TABLE flights ADD CONSTRAINT check_flight_status 
CHECK (status IN ('active', 'stale', 'completed', 'cancelled', 'unknown'));

-- Step 3: Add index on status for better query performance (if not exists)
CREATE INDEX IF NOT EXISTS idx_flights_status ON flights(status);

-- Step 4: Add index for status and last_updated for stale detection
CREATE INDEX IF NOT EXISTS idx_flights_status_last_updated ON flights(status, last_updated);

-- Verify the changes
SELECT 
    'Stale status added' as message,
    COUNT(*) as total_flights,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_flights,
    COUNT(CASE WHEN status = 'stale' THEN 1 END) as stale_flights,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_flights,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_flights,
    COUNT(CASE WHEN status = 'unknown' THEN 1 END) as unknown_flights
FROM flights; 