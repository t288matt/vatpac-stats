-- Migration script to remove unique constraint on controllers.callsign
-- This allows duplicate callsigns as requested

-- Drop the unique constraint
ALTER TABLE controllers DROP CONSTRAINT IF EXISTS controllers_callsign_key;

-- Verify the constraint is removed
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name = 'controllers' AND constraint_type = 'UNIQUE';
