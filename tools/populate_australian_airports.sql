-- ===========================================
-- POPULATE AUSTRALIAN AIRPORTS (UPDATED)
-- ===========================================
-- This script populates the airports table with Australian airports
-- from the airport_coordinates.json file (now handled by populate_global_airports.py)

-- Note: This script is now deprecated. Use populate_global_airports.py instead.
-- The airports table now contains all global airports, including Australian ones.

-- To get Australian airports from the new table:
SELECT 
    icao_code,
    name,
    country,
    region
FROM airports 
WHERE icao_code LIKE 'Y%' AND is_active = true
ORDER BY icao_code; 