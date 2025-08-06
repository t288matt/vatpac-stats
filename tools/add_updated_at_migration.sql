-- Migration script to add updated_at columns to existing tables
-- This ensures all tables have consistent updated_at fields

-- Add updated_at to traffic_movements table if it doesn't exist
ALTER TABLE IF EXISTS traffic_movements 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add updated_at to airport_config table if it doesn't exist
ALTER TABLE IF EXISTS airport_config 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add updated_at to movement_detection_config table if it doesn't exist
ALTER TABLE IF EXISTS movement_detection_config 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add updated_at to system_config table if it doesn't exist
ALTER TABLE IF EXISTS system_config 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add updated_at to transceivers table if it doesn't exist
ALTER TABLE IF EXISTS transceivers 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Create or replace the update_updated_at_column function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns (if they don't exist)
-- Note: These will fail if triggers already exist, which is fine

-- Traffic movements trigger
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_traffic_movements_updated_at'
    ) THEN
        CREATE TRIGGER update_traffic_movements_updated_at 
            BEFORE UPDATE ON traffic_movements 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Airport config trigger
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_airport_config_updated_at'
    ) THEN
        CREATE TRIGGER update_airport_config_updated_at 
            BEFORE UPDATE ON airport_config 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Movement detection config trigger
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_movement_detection_config_updated_at'
    ) THEN
        CREATE TRIGGER update_movement_detection_config_updated_at 
            BEFORE UPDATE ON movement_detection_config 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- System config trigger
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_system_config_updated_at'
    ) THEN
        CREATE TRIGGER update_system_config_updated_at 
            BEFORE UPDATE ON system_config 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Transceivers trigger
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_transceivers_updated_at'
    ) THEN
        CREATE TRIGGER update_transceivers_updated_at 
            BEFORE UPDATE ON transceivers 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Verify the migration
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_name IN ('traffic_movements', 'airport_config', 'movement_detection_config', 'system_config', 'transceivers')
    AND column_name = 'updated_at'
ORDER BY table_name, column_name; 