-- ===========================================
-- AUSTRALIAN AIRPORTS VIEW (SQLite Version)
-- ===========================================
-- This view provides a centralized reference for Australian airports
-- Used by Grafana dashboards to avoid hardcoded airport codes

DROP VIEW IF EXISTS australian_airports;
CREATE VIEW australian_airports AS
SELECT 
    icao_code,
    name,
    latitude,
    longitude,
    country,
    region
FROM airports 
WHERE icao_code LIKE 'Y%' AND is_active = 1;

-- ===========================================
-- AUSTRALIAN FLIGHTS VIEW (SQLite Version)
-- ===========================================
-- View that automatically filters for Australian flights
-- based on departure/arrival from Australian airports

DROP VIEW IF EXISTS australian_flights;
CREATE VIEW australian_flights AS
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