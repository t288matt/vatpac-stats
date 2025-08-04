-- ===========================================
-- AUSTRALIAN AIRPORTS VIEW
-- ===========================================
-- This view provides a centralized reference for Australian airports
-- Used by Grafana dashboards to avoid hardcoded airport codes

CREATE OR REPLACE VIEW australian_airports AS
SELECT 
    icao_code,
    name,
    latitude,
    longitude,
    region
FROM airport_config 
WHERE icao_code LIKE 'Y%';

-- ===========================================
-- AUSTRALIAN AIRPORTS FUNCTION
-- ===========================================
-- Function to get Australian airport codes as a comma-separated string
-- for use in Grafana dashboard queries

CREATE OR REPLACE FUNCTION get_australian_airport_codes()
RETURNS TEXT AS $$
DECLARE
    airport_codes TEXT;
BEGIN
    SELECT string_agg(icao_code, ',') 
    INTO airport_codes
    FROM australian_airports;
    
    RETURN airport_codes;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- AUSTRALIAN FLIGHTS VIEW
-- ===========================================
-- View that automatically filters for Australian flights
-- based on departure/arrival from Australian airports

CREATE OR REPLACE VIEW australian_flights AS
SELECT 
    f.*,
    CASE 
        WHEN f.departure IN (SELECT icao_code FROM australian_airports) 
             AND f.arrival NOT IN (SELECT icao_code FROM australian_airports) 
        THEN 'International Outbound'
        WHEN f.arrival IN (SELECT icao_code FROM australian_airports) 
             AND f.departure NOT IN (SELECT icao_code FROM australian_airports) 
        THEN 'International Inbound'
        WHEN f.departure IN (SELECT icao_code FROM australian_airports) 
             AND f.arrival IN (SELECT icao_code FROM australian_airports) 
        THEN 'Domestic'
        ELSE 'Other'
    END as route_type
FROM flights f
WHERE f.departure IN (SELECT icao_code FROM australian_airports)
   OR f.arrival IN (SELECT icao_code FROM australian_airports); 