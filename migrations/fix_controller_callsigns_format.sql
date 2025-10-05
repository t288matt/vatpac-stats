-- Migration to fix controller_callsigns format in the database
-- 
-- This migration addresses the issue with controller_callsigns sometimes being stored
-- as empty objects ({}) instead of arrays ([]), which causes problems with
-- jsonb_array_length() functions.

DO $$
BEGIN
    -- First, check if we have any controller_callsigns values that aren't arrays
    PERFORM count(*)
    FROM flight_summaries
    WHERE controller_callsigns IS NOT NULL
      AND jsonb_typeof(controller_callsigns) != 'array';

    -- If we have empty objects, convert them to empty arrays
    UPDATE flight_summaries
    SET controller_callsigns = '[]'::jsonb
    WHERE controller_callsigns = '{}'::jsonb;

    -- For any other non-array types, we need to handle them specially
    -- For objects with keys (dictionaries from ATC detection), create an array of the values
    UPDATE flight_summaries
    SET controller_callsigns = (
        SELECT jsonb_agg(value)
        FROM jsonb_each(controller_callsigns)
    )
    WHERE controller_callsigns IS NOT NULL
      AND jsonb_typeof(controller_callsigns) = 'object'
      AND controller_callsigns != '{}'::jsonb;

    -- For any remaining non-array types (should be rare or none), set to empty array
    UPDATE flight_summaries
    SET controller_callsigns = '[]'::jsonb
    WHERE controller_callsigns IS NOT NULL
      AND jsonb_typeof(controller_callsigns) != 'array';

    -- Log the completion of the migration
    RAISE NOTICE 'Migration to fix controller_callsigns format completed successfully';
END $$;

-- Add a comment to the table to document this migration
COMMENT ON COLUMN flight_summaries.controller_callsigns IS 'JSON array of controller callsigns - always stored as an array, even when empty (never as an object/dictionary)';

