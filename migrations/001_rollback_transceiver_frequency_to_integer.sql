-- Rollback Migration: 001_rollback_transceiver_frequency_to_integer.sql
-- Description: Revert transceiver frequency column from BIGINT back to INTEGER
-- Date: 2024-12-19
-- Author: System Migration
-- WARNING: This will lose any data that exceeds INTEGER range

-- Step 1: Add a new INTEGER column
ALTER TABLE transceivers ADD COLUMN frequency_old INTEGER;

-- Step 2: Copy data from BIGINT column to INTEGER column (with range check)
UPDATE transceivers SET frequency_old = frequency 
WHERE frequency >= -2147483648 AND frequency <= 2147483647;

-- Step 3: Check if any data was lost
-- SELECT COUNT(*) as lost_records FROM transceivers WHERE frequency_old IS NULL;

-- Step 4: Drop the BIGINT column
ALTER TABLE transceivers DROP COLUMN frequency;

-- Step 5: Rename the INTEGER column to the original name
ALTER TABLE transceivers RENAME COLUMN frequency_old TO frequency;

-- Step 6: Recreate the index on the frequency column
CREATE INDEX idx_transceivers_frequency ON transceivers(frequency);

-- Step 7: Add NOT NULL constraint back
ALTER TABLE transceivers ALTER COLUMN frequency SET NOT NULL;

-- Verification query (uncomment to run manually if needed)
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'transceivers' AND column_name = 'frequency';
