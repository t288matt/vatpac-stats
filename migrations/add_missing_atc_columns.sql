-- Add missing columns to flight_summaries table
-- This migration adds total_controller_time_minutes and interactions_detected columns
-- These are used by the ATC detection service but were missing from the schema

DO $$
BEGIN
    -- Add total_controller_time_minutes column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'flight_summaries' 
        AND column_name = 'total_controller_time_minutes'
    ) THEN
        ALTER TABLE flight_summaries 
        ADD COLUMN total_controller_time_minutes INTEGER;
        
        -- Add a comment for documentation
        COMMENT ON COLUMN flight_summaries.total_controller_time_minutes IS 'Total time in minutes that the flight was in contact with controllers';
    END IF;

    -- Add interactions_detected column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'flight_summaries' 
        AND column_name = 'interactions_detected'
    ) THEN
        ALTER TABLE flight_summaries 
        ADD COLUMN interactions_detected INTEGER;
        
        -- Add a comment for documentation
        COMMENT ON COLUMN flight_summaries.interactions_detected IS 'Number of controller interactions detected for this flight';
    END IF;

    -- Update existing records to have default values
    -- This prevents NULL values in existing records
    UPDATE flight_summaries
    SET 
        total_controller_time_minutes = CASE 
            WHEN controller_time_percentage IS NOT NULL AND time_online_minutes IS NOT NULL 
            THEN ROUND(controller_time_percentage * time_online_minutes / 100)
            ELSE 0
        END,
        interactions_detected = CASE
            WHEN controller_callsigns IS NOT NULL AND controller_callsigns != 'null'::jsonb
            THEN jsonb_array_length(controller_callsigns)
            ELSE 0
        END
    WHERE total_controller_time_minutes IS NULL 
    OR interactions_detected IS NULL;

    -- Add constraint to ensure values are not negative
    ALTER TABLE flight_summaries
    ADD CONSTRAINT valid_total_controller_time 
    CHECK (total_controller_time_minutes >= 0);

    ALTER TABLE flight_summaries
    ADD CONSTRAINT valid_interactions_detected 
    CHECK (interactions_detected >= 0);
END$$;

-- Add an index to support queries that filter or order by interactions_detected
CREATE INDEX IF NOT EXISTS idx_flight_summaries_interactions_detected 
ON flight_summaries(interactions_detected);

