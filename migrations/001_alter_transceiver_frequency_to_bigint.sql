-- Migration: 001_alter_transceiver_frequency_to_bigint.sql
-- Description: Alter transceiver frequency column from INTEGER to BIGINT
-- Date: 2024-12-19
-- Author: System Migration

-- Step 1: Add a new BIGINT column
ALTER TABLE transceivers ADD COLUMN frequency_new BIGINT;

-- Step 2: Copy data from old column to new column
UPDATE transceivers SET frequency_new = frequency;

-- Step 3: Drop the old column
ALTER TABLE transceivers DROP COLUMN frequency;

-- Step 4: Rename the new column to the original name
ALTER TABLE transceivers RENAME COLUMN frequency_new TO frequency;

-- Step 5: Recreate the index on the frequency column
CREATE INDEX idx_transceivers_frequency ON transceivers(frequency);

-- Step 6: Add NOT NULL constraint back
ALTER TABLE transceivers ALTER COLUMN frequency SET NOT NULL;

-- Verification query (uncomment to run manually if needed)
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'transceivers' AND column_name = 'frequency';
