-- Migration 011: Remove unused flight_plan field from flights table
-- 
-- BACKGROUND:
-- The flight_plan JSONB field exists in the database but is not used by any production code.
-- All flight plan data is stored in individual normalized fields (departure, arrival, route, etc.)
-- The field is not defined in the SQLAlchemy model and has no functional purpose.
--
-- SAFETY:
-- - No production code reads from or writes to this field
-- - No SQL queries reference this field
-- - Only debug scripts and test files mention it
-- - Safe to remove without data loss (all flight plan data is in other fields)

-- Remove the unused flight_plan field
ALTER TABLE flights DROP COLUMN IF EXISTS flight_plan;

-- Add comment explaining the removal
COMMENT ON TABLE flights IS 'Flight tracking table - flight_plan JSONB field removed in migration 011 (unused, data preserved in normalized fields)';

-- Verify the column was removed
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'flights' 
        AND column_name = 'flight_plan'
    ) THEN
        RAISE EXCEPTION 'Migration failed: flight_plan column still exists';
    ELSE
        RAISE NOTICE 'Migration successful: flight_plan column removed from flights table';
    END IF;
END $$;
