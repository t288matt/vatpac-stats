-- Migration script to add missing VATSIM API fields
-- This script adds all missing fields using 1:1 mapping with API field names

-- Add missing fields to flights table
ALTER TABLE flights ADD COLUMN IF NOT EXISTS cid INTEGER;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS name VARCHAR(100);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS server VARCHAR(50);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS pilot_rating INTEGER;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS military_rating INTEGER;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS latitude FLOAT;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS longitude FLOAT;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS groundspeed INTEGER;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS transponder VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS heading INTEGER;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS qnh_i_hg DECIMAL(4,2);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS qnh_mb INTEGER;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS logon_time TIMESTAMP;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS last_updated_api TIMESTAMP;

-- Flight plan fields (nested object)
ALTER TABLE flights ADD COLUMN IF NOT EXISTS flight_rules VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS aircraft_faa VARCHAR(20);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS aircraft_short VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS alternate VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS cruise_tas INTEGER;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS planned_altitude INTEGER;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS deptime VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS enroute_time VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS fuel_time VARCHAR(10);
ALTER TABLE flights ADD COLUMN IF NOT EXISTS remarks TEXT;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS revision_id INTEGER;
ALTER TABLE flights ADD COLUMN IF NOT EXISTS assigned_transponder VARCHAR(10);

-- Add missing fields to controllers table
ALTER TABLE controllers ADD COLUMN IF NOT EXISTS visual_range INTEGER;
ALTER TABLE controllers ADD COLUMN IF NOT EXISTS text_atis TEXT;

-- Create vatsim_status table for general/status data
CREATE TABLE IF NOT EXISTS vatsim_status (
    id SERIAL PRIMARY KEY,
    api_version INTEGER,
    reload INTEGER,
    update_timestamp TIMESTAMP,
    connected_clients INTEGER,
    unique_users INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_flights_cid ON flights(cid);
CREATE INDEX IF NOT EXISTS idx_flights_server ON flights(server);
CREATE INDEX IF NOT EXISTS idx_flights_pilot_rating ON flights(pilot_rating);
CREATE INDEX IF NOT EXISTS idx_flights_transponder ON flights(transponder);
CREATE INDEX IF NOT EXISTS idx_flights_logon_time ON flights(logon_time);
CREATE INDEX IF NOT EXISTS idx_flights_last_updated_api ON flights(last_updated_api);

-- Add indexes for flight plan fields
CREATE INDEX IF NOT EXISTS idx_flights_flight_rules ON flights(flight_rules);
CREATE INDEX IF NOT EXISTS idx_flights_aircraft_faa ON flights(aircraft_faa);
CREATE INDEX IF NOT EXISTS idx_flights_aircraft_short ON flights(aircraft_short);
CREATE INDEX IF NOT EXISTS idx_flights_alternate ON flights(alternate);
CREATE INDEX IF NOT EXISTS idx_flights_cruise_tas ON flights(cruise_tas);
CREATE INDEX IF NOT EXISTS idx_flights_planned_altitude ON flights(planned_altitude);
CREATE INDEX IF NOT EXISTS idx_flights_deptime ON flights(deptime);
CREATE INDEX IF NOT EXISTS idx_flights_enroute_time ON flights(enroute_time);
CREATE INDEX IF NOT EXISTS idx_flights_fuel_time ON flights(fuel_time);
CREATE INDEX IF NOT EXISTS idx_flights_revision_id ON flights(revision_id);
CREATE INDEX IF NOT EXISTS idx_flights_assigned_transponder ON flights(assigned_transponder);

-- Add indexes for controller fields
CREATE INDEX IF NOT EXISTS idx_controllers_visual_range ON controllers(visual_range);

-- Add indexes for vatsim_status table
CREATE INDEX IF NOT EXISTS idx_vatsim_status_api_version ON vatsim_status(api_version);
CREATE INDEX IF NOT EXISTS idx_vatsim_status_update_timestamp ON vatsim_status(update_timestamp);
CREATE INDEX IF NOT EXISTS idx_vatsim_status_connected_clients ON vatsim_status(connected_clients);
CREATE INDEX IF NOT EXISTS idx_vatsim_status_unique_users ON vatsim_status(unique_users);

-- Update existing records to set default values for new columns
UPDATE flights SET 
    cid = NULL,
    name = NULL,
    server = NULL,
    pilot_rating = NULL,
    military_rating = NULL,
    latitude = position_lat,
    longitude = position_lng,
    groundspeed = speed,
    transponder = squawk,
    heading = NULL,
    qnh_i_hg = NULL,
    qnh_mb = NULL,
    logon_time = NULL,
    last_updated_api = last_updated,
    flight_rules = NULL,
    aircraft_faa = NULL,
    aircraft_short = aircraft_type,
    alternate = NULL,
    cruise_tas = NULL,
    planned_altitude = NULL,
    deptime = NULL,
    enroute_time = NULL,
    fuel_time = NULL,
    remarks = NULL,
    revision_id = NULL,
    assigned_transponder = NULL
WHERE cid IS NULL;

UPDATE controllers SET 
    visual_range = NULL,
    text_atis = NULL
WHERE visual_range IS NULL;

-- Insert initial vatsim_status record
INSERT INTO vatsim_status (api_version, reload, update_timestamp, connected_clients, unique_users)
VALUES (3, 1, CURRENT_TIMESTAMP, 0, 0)
ON CONFLICT DO NOTHING;

-- Add comments to document the new fields
COMMENT ON COLUMN flights.cid IS 'VATSIM user ID from API cid field';
COMMENT ON COLUMN flights.name IS 'Pilot name from API name field';
COMMENT ON COLUMN flights.server IS 'Network server from API server field';
COMMENT ON COLUMN flights.pilot_rating IS 'Pilot rating from API pilot_rating field';
COMMENT ON COLUMN flights.military_rating IS 'Military rating from API military_rating field';
COMMENT ON COLUMN flights.latitude IS 'Position latitude from API latitude field';
COMMENT ON COLUMN flights.longitude IS 'Position longitude from API longitude field';
COMMENT ON COLUMN flights.groundspeed IS 'Ground speed from API groundspeed field';
COMMENT ON COLUMN flights.transponder IS 'Transponder code from API transponder field';
COMMENT ON COLUMN flights.heading IS 'Aircraft heading from API heading field';
COMMENT ON COLUMN flights.qnh_i_hg IS 'QNH in inches Hg from API qnh_i_hg field';
COMMENT ON COLUMN flights.qnh_mb IS 'QNH in millibars from API qnh_mb field';
COMMENT ON COLUMN flights.logon_time IS 'When pilot connected from API logon_time field';
COMMENT ON COLUMN flights.last_updated_api IS 'API last_updated timestamp from API last_updated field';

COMMENT ON COLUMN flights.flight_rules IS 'IFR/VFR from API flight_plan.flight_rules field';
COMMENT ON COLUMN flights.aircraft_faa IS 'FAA aircraft code from API flight_plan.aircraft_faa field';
COMMENT ON COLUMN flights.aircraft_short IS 'Short aircraft code from API flight_plan.aircraft_short field';
COMMENT ON COLUMN flights.alternate IS 'Alternate airport from API flight_plan.alternate field';
COMMENT ON COLUMN flights.cruise_tas IS 'True airspeed from API flight_plan.cruise_tas field';
COMMENT ON COLUMN flights.planned_altitude IS 'Planned cruise altitude from API flight_plan.altitude field';
COMMENT ON COLUMN flights.deptime IS 'Departure time from API flight_plan.deptime field';
COMMENT ON COLUMN flights.enroute_time IS 'Enroute time from API flight_plan.enroute_time field';
COMMENT ON COLUMN flights.fuel_time IS 'Fuel time from API flight_plan.fuel_time field';
COMMENT ON COLUMN flights.remarks IS 'Flight plan remarks from API flight_plan.remarks field';
COMMENT ON COLUMN flights.revision_id IS 'Flight plan revision from API flight_plan.revision_id field';
COMMENT ON COLUMN flights.assigned_transponder IS 'Assigned transponder from API flight_plan.assigned_transponder field';

COMMENT ON COLUMN controllers.visual_range IS 'Controller visual range from API visual_range field';
COMMENT ON COLUMN controllers.text_atis IS 'ATIS information from API text_atis field';

COMMENT ON COLUMN vatsim_status.api_version IS 'API version from API version field';
COMMENT ON COLUMN vatsim_status.reload IS 'Reload indicator from API reload field';
COMMENT ON COLUMN vatsim_status.update_timestamp IS 'Update timestamp from API update_timestamp field';
COMMENT ON COLUMN vatsim_status.connected_clients IS 'Connected clients from API connected_clients field';
COMMENT ON COLUMN vatsim_status.unique_users IS 'Unique users from API unique_users field'; 