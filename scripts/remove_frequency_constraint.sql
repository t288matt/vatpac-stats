-- Migration script to remove the 122.8 MHz frequency constraint from transceivers table
-- This allows 122.8 MHz frequencies to be stored in the database
-- The frequency filtering will now be handled only at the application level

-- Drop the constraint if it exists
ALTER TABLE transceivers 
DROP CONSTRAINT IF EXISTS exclude_122_8_mhz_range;

-- Verify the constraint has been removed
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'transceivers'::regclass
    AND contype = 'c'
    AND conname = 'exclude_122_8_mhz_range';

-- If no rows are returned, the constraint has been successfully removed

