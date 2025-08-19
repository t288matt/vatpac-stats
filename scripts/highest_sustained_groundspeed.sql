-- Find Aircraft with Highest Sustained Groundspeed (High Performance Version)
-- 
-- This query finds the highest peak groundspeeds for aircraft with valid destinations.
-- Each aircraft (callsign) appears only once with their highest performance.
-- Excludes supersonic jets, military aircraft, business jets, and turboprops.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/highest_sustained_groundspeed.sql
--

-- Find top peak groundspeeds in the past month (unique by callsign)
WITH top_peak_speeds AS (
    SELECT 
        callsign,
        aircraft_type,
        departure,
        arrival,
        groundspeed as peak_speed_knots,
        altitude as altitude_feet,
        latitude,
        longitude,
        last_updated as peak_time,
        name as pilot_name
    FROM (
        SELECT 
            callsign,
            aircraft_type,
            departure,
            arrival,
            groundspeed,
            altitude,
            latitude,
            longitude,
            last_updated,
            name,
            ROW_NUMBER() OVER (PARTITION BY callsign ORDER BY groundspeed DESC) as rn
        FROM flights 
        WHERE groundspeed IS NOT NULL 
            AND groundspeed > 100  -- Higher threshold for better performance
            AND groundspeed <= 750  -- Filter out unrealistic speeds
            AND altitude > 1000  -- Must be airborne
            AND last_updated >= NOW() - INTERVAL '1 month'  -- Last month only
            AND arrival IS NOT NULL  -- Must have destination
            AND arrival != ''  -- Destination cannot be empty
            -- Exclude supersonic jets and military aircraft
            AND aircraft_type NOT IN (
                'CONC', 'TU144', 'TU160', 'MIG21', 'MIG23', 'MIG25', 'MIG29', 'MIG31',
                'SU27', 'SU30', 'SU33', 'SU35', 'SU57', 'F14', 'F15', 'F16', 'F18',
                'F22', 'F35', 'TYPH', 'RAF', 'GRIP', 'MIR2', 'MIR4', 'HAR', 'JAG',
                'TORN', 'VIGG', 'M2K', 'RAPH', 'EF2K', 'GR4', 'FGR4', 'F4', 'F5',
                'A4', 'A6', 'A7', 'F111', 'F117', 'B1', 'B2', 'SR71', 'U2', 'TR1'
            )
            -- Exclude business jets
            AND aircraft_type NOT IN (
                'C550', 'C560', 'C680', 'C750', 'C850',  -- Citation series
                'BE20', 'BE30', 'BE40', 'BE90', 'BE99',  -- Beechcraft
                'GLF4', 'GLF5', 'GLF6', 'GLF7',          -- Gulfstream
                'FAL7', 'FAL8', 'FAL9', 'FAL0',          -- Falcon series
                'LJ35', 'LJ45', 'LJ60', 'LJ75',          -- Learjet series
                'CL30', 'CL60', 'CL65', 'CL85',          -- Challenger series
                'GL5T', 'GL6T', 'GL7T', 'GL8T',          -- Global series
                'E135', 'E145', 'E170', 'E175', 'E190', 'E195'  -- Embraer business jets
            )
            -- Exclude turboprops
            AND aircraft_type NOT IN (
                'AT72', 'AT76', 'AT42', 'AT45',          -- ATR series
                'DH8A', 'DH8B', 'DH8C', 'DH8D', 'DH8Q', -- Dash 8 series
                'B350', 'B190', 'B200', 'B300', 'B360', -- Beechcraft King Air
                'PC12', 'PC21', 'PC24',                  -- Pilatus series
                'AN24', 'AN26', 'AN32', 'AN72', 'AN74', -- Antonov series
                'SF34', 'SF50',                          -- Saab series
                'DHC6', 'DHC7', 'DHC8', 'K350',                 -- De Havilland Canada
                'EMB1', 'EMB2', 'EMB3', 'EMB4', 'EMB5'  -- Embraer turboprops
            )
            -- Also exclude aircraft types that start with common military prefixes
            AND aircraft_type NOT LIKE 'F-%'
            AND aircraft_type NOT LIKE 'MIG%'
            AND aircraft_type NOT LIKE 'SU-%'
            AND aircraft_type NOT LIKE 'TU-%'
            AND aircraft_type NOT LIKE 'MIR%'
    ) ranked_flights
    WHERE rn = 1  -- Only the highest speed for each callsign
    ORDER BY peak_speed_knots DESC
    LIMIT 20
)
SELECT 
    callsign,
    pilot_name,
    aircraft_type,
    departure,
    arrival,
    peak_speed_knots,
    altitude_feet,
    peak_time
FROM top_peak_speeds
ORDER BY peak_speed_knots DESC;
