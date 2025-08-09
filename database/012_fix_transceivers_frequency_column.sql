-- Migration: Fix transceivers frequency column to handle large frequency values
-- Date: 2025-08-09
-- Issue: VATSIM frequency values can exceed INTEGER limit (2,147,483,647)
-- Solution: Change frequency column from INTEGER to BIGINT

-- Change frequency column from INTEGER to BIGINT to handle larger frequency values
ALTER TABLE transceivers ALTER COLUMN frequency TYPE BIGINT;

-- Add comment to document the change
COMMENT ON COLUMN transceivers.frequency IS 'Radio frequency in Hz from VATSIM API (changed to BIGINT to handle values > 2.1B)';
