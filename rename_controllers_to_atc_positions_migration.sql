-- Migration: Rename controllers table to atc_positions for clearer nomenclature
-- This makes it clear that each record represents an ATC position, not necessarily a controller

-- Rename the table
ALTER TABLE controllers RENAME TO atc_positions;

-- Rename the primary key sequence
ALTER SEQUENCE controllers_id_seq RENAME TO atc_positions_id_seq;

-- Update the primary key constraint
ALTER TABLE atc_positions ALTER COLUMN id SET DEFAULT nextval('atc_positions_id_seq');

-- Rename indexes
ALTER INDEX controllers_callsign_key RENAME TO atc_positions_callsign_key;
ALTER INDEX controllers_callsign_idx RENAME TO atc_positions_callsign_idx;
ALTER INDEX controllers_vatsim_id_idx RENAME TO atc_positions_controller_id_idx;
ALTER INDEX controllers_rating_idx RENAME TO atc_positions_controller_rating_idx;
ALTER INDEX idx_controllers_status_last_seen RENAME TO idx_atc_positions_status_last_seen;
ALTER INDEX idx_controllers_callsign RENAME TO idx_atc_positions_callsign;
ALTER INDEX idx_controllers_vatsim_id RENAME TO idx_atc_positions_controller_id;
ALTER INDEX idx_controllers_rating RENAME TO idx_atc_positions_controller_rating;

-- Rename columns for clarity
ALTER TABLE atc_positions RENAME COLUMN vatsim_id TO controller_id;
ALTER TABLE atc_positions RENAME COLUMN controller_name TO controller_name;
ALTER TABLE atc_positions RENAME COLUMN controller_rating TO controller_rating;

-- Update column comments
COMMENT ON COLUMN atc_positions.controller_id IS 'VATSIM user ID that links multiple positions controlled by the same controller';
COMMENT ON COLUMN atc_positions.controller_name IS 'Controller real name from VATSIM API';
COMMENT ON COLUMN atc_positions.controller_rating IS 'Controller rating (1-11) from VATSIM API';

-- Update table comment
COMMENT ON TABLE atc_positions IS 'ATC positions that can be controlled or uncontrolled';

-- Verify the migration
SELECT 
    table_name,
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'atc_positions' 
ORDER BY ordinal_position; 