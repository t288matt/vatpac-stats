-- Migration: Cleanup Flight Schema
-- Remove duplicate fields and improve status management
-- Date: 2025-08-07

-- Step 1: Copy squawk data to transponder (in case there are differences)
UPDATE flights 
SET transponder = COALESCE(squawk, transponder) 
WHERE squawk IS NOT NULL AND (transponder IS NULL OR transponder != squawk);

-- Step 2: Update status field to be more meaningful
UPDATE flights 
SET status = CASE 
    WHEN is_active = true THEN 'active'
    WHEN is_active = false THEN 'completed'
    ELSE 'unknown'
END;

-- Step 3: Remove duplicate columns
ALTER TABLE flights DROP COLUMN IF EXISTS squawk;
ALTER TABLE flights DROP COLUMN IF EXISTS is_active;
ALTER TABLE flights DROP COLUMN IF EXISTS flight_plan;

-- Step 4: Remove indexes on deleted columns
DROP INDEX IF EXISTS idx_flights_transponder;

-- Step 5: Add index on status for better query performance
CREATE INDEX IF NOT EXISTS idx_flights_status ON flights(status);

-- Step 6: Update status column to have a check constraint for valid values
ALTER TABLE flights ADD CONSTRAINT check_flight_status 
CHECK (status IN ('active', 'completed', 'cancelled', 'unknown'));

-- Step 7: Set default status to 'active'
ALTER TABLE flights ALTER COLUMN status SET DEFAULT 'active';

-- Step 8: Update existing records to have proper status
UPDATE flights 
SET status = 'active' 
WHERE status IS NULL OR status = '';

-- Verify the changes
SELECT 
    'Schema cleanup completed' as message,
    COUNT(*) as total_flights,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_flights,
    COUNT(CASE WHEN transponder IS NOT NULL THEN 1 END) as flights_with_transponder
FROM flights; 