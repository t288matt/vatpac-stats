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
ALTER INDEX controllers_vatsim_id_idx RENAME TO atc_positions_operator_id_idx;
ALTER INDEX controllers_rating_idx RENAME TO atc_positions_operator_rating_idx;
ALTER INDEX idx_controllers_status_last_seen RENAME TO idx_atc_positions_status_last_seen;
ALTER INDEX idx_controllers_callsign RENAME TO idx_atc_positions_callsign;
ALTER INDEX idx_controllers_vatsim_id RENAME TO idx_atc_positions_operator_id;
ALTER INDEX idx_controllers_rating RENAME TO idx_atc_positions_operator_rating;

-- Rename columns for clarity
ALTER TABLE atc_positions RENAME COLUMN vatsim_id TO operator_id;
ALTER TABLE atc_positions RENAME COLUMN controller_name TO operator_name;
ALTER TABLE atc_positions RENAME COLUMN controller_rating TO operator_rating;

-- Update column comments
COMMENT ON COLUMN atc_positions.operator_id IS 'VATSIM user ID that links multiple positions controlled by the same operator';
COMMENT ON COLUMN atc_positions.operator_name IS 'Operator real name from VATSIM API';
COMMENT ON COLUMN atc_positions.operator_rating IS 'Operator rating (1-11) from VATSIM API';

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