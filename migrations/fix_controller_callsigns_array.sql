-- Migration to fix controller_callsigns format in the database
-- This migration ensures that all controller_callsigns entries are arrays,
-- converting any objects/dictionaries to arrays of their values.

DO $$
DECLARE
    object_count INTEGER;
    empty_object_count INTEGER;
    fixed_count INTEGER := 0;
BEGIN
    -- Count how many records have non-array controller_callsigns
    SELECT COUNT(*) INTO object_count
    FROM flight_summaries
    WHERE controller_callsigns IS NOT NULL
      AND jsonb_typeof(controller_callsigns) <> 'array';
      
    RAISE NOTICE 'Found % records with non-array controller_callsigns', object_count;
    
    -- Count empty objects
    SELECT COUNT(*) INTO empty_object_count
    FROM flight_summaries
    WHERE controller_callsigns = '{}'::jsonb;
    
    RAISE NOTICE 'Of those, % are empty objects ({})', empty_object_count;
    
    -- Fix empty objects by converting them to empty arrays
    UPDATE flight_summaries
    SET controller_callsigns = '[]'::jsonb
    WHERE controller_callsigns = '{}'::jsonb;
    
    GET DIAGNOSTICS fixed_count = ROW_COUNT;
    RAISE NOTICE 'Converted % empty objects to empty arrays', fixed_count;
    
    -- Fix non-empty objects by converting them to arrays of their values
    -- This extracts the values from the object and creates an array
    WITH object_records AS (
        SELECT id, controller_callsigns
        FROM flight_summaries
        WHERE controller_callsigns IS NOT NULL
          AND jsonb_typeof(controller_callsigns) = 'object'
          AND controller_callsigns <> '{}'::jsonb
    )
    UPDATE flight_summaries fs
    SET controller_callsigns = (
        SELECT jsonb_agg(value)
        FROM jsonb_each(obj_rec.controller_callsigns)
    )
    FROM object_records obj_rec
    WHERE fs.id = obj_rec.id;
    
    GET DIAGNOSTICS fixed_count = ROW_COUNT;
    RAISE NOTICE 'Converted % non-empty objects to arrays of their values', fixed_count;
    
    -- For any other non-array types, set to empty array
    UPDATE flight_summaries
    SET controller_callsigns = '[]'::jsonb
    WHERE controller_callsigns IS NOT NULL
      AND jsonb_typeof(controller_callsigns) <> 'array';
    
    GET DIAGNOSTICS fixed_count = ROW_COUNT;
    RAISE NOTICE 'Converted % other non-array values to empty arrays', fixed_count;
    
    -- Add a comment to the column
    COMMENT ON COLUMN flight_summaries.controller_callsigns IS 'JSON array of controller callsigns - always stored as an array, even when empty';
    
    RAISE NOTICE 'Migration completed successfully';
END $$;
