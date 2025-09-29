-- Add new enrichment status types for better failure classification
-- This migration adds 'technical_failure' and 'data_error' status types
-- and adds an enrichment_error JSONB column for structured error reporting

DO $$
BEGIN
    -- Check if the values already exist to avoid errors
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'enrichment_status_enum' AND typelem <> 0) THEN
        -- Create the type if it doesn't exist
        CREATE TYPE enrichment_status_enum AS ENUM (
            'pending', 'in_progress', 'completed', 'failed', 
            'wait_for_completion', 'technical_failure', 'data_error'
        );
    ELSE
        -- Add new values if they don't exist
        BEGIN
            ALTER TYPE enrichment_status_enum ADD VALUE 'wait_for_completion' AFTER 'failed';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
        
        BEGIN
            ALTER TYPE enrichment_status_enum ADD VALUE 'technical_failure' AFTER 'wait_for_completion';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
        
        BEGIN
            ALTER TYPE enrichment_status_enum ADD VALUE 'data_error' AFTER 'technical_failure';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
    END IF;
    
    -- Add enrichment_error column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'flight_summaries' AND column_name = 'enrichment_error') THEN
        ALTER TABLE flight_summaries ADD COLUMN enrichment_error JSONB;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'controller_summaries' AND column_name = 'enrichment_error') THEN
        ALTER TABLE controller_summaries ADD COLUMN enrichment_error JSONB;
    END IF;
END$$;
