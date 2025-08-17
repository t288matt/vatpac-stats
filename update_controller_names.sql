-- SQL Script to update all controller names to 'x'
-- WARNING: This will update ALL records in the controllers table

-- First, let's see how many records we're about to update
SELECT COUNT(*) as total_records FROM controllers;

-- Show a sample of current names
SELECT DISTINCT name FROM controllers LIMIT 5;

-- Update all controller names to 'x' and set updated_at to current timestamp
UPDATE controllers 
SET name = 'x', 
    updated_at = NOW();

-- Verify the update
SELECT COUNT(*) as updated_records FROM controllers WHERE name = 'x';

-- Show a sample of updated records
SELECT id, callsign, name, updated_at FROM controllers ORDER BY id DESC LIMIT 5;


