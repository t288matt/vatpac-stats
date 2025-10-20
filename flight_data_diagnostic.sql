-- Flight Data Diagnostic Query
-- Investigate anomalously low aircraft count on Sept 8, 2025 at 0910

-- First, check total flight records available on Sept 8 around 0910
SELECT 
    COUNT(*) AS total_flight_records,
    COUNT(DISTINCT callsign) AS distinct_callsigns
FROM flights
WHERE last_updated BETWEEN '2025-09-08 09:05:00' AND '2025-09-08 09:15:00';

-- Second, look at the altitude/groundspeed distribution on Sept 8 around 0910
SELECT 
    COUNT(*) AS count,
    CASE 
        WHEN altitude IS NULL THEN 'missing_altitude'
        WHEN altitude <= 0 THEN 'ground_or_negative'
        WHEN altitude <= 1000 THEN 'below_1000'
        ELSE 'above_1000'
    END AS altitude_category,
    CASE 
        WHEN groundspeed IS NULL THEN 'missing_groundspeed'
        WHEN groundspeed < 30 THEN 'stationary_or_slow'
        WHEN groundspeed < 60 THEN '30_to_60'
        ELSE '60_or_above'
    END AS speed_category
FROM flights
WHERE last_updated BETWEEN '2025-09-08 09:05:00' AND '2025-09-08 09:15:00'
GROUP BY altitude_category, speed_category
ORDER BY altitude_category, speed_category;

-- Third, compare with a time when we had normal traffic levels
SELECT 
    COUNT(*) AS total_flight_records,
    COUNT(DISTINCT callsign) AS distinct_callsigns
FROM flights
WHERE last_updated BETWEEN '2025-09-22 09:05:00' AND '2025-09-22 09:15:00';

-- Fourth, check if there are any data gaps or issues with timestamps
SELECT
    date_trunc('minute', last_updated) AS minute,
    COUNT(*) AS record_count,
    COUNT(DISTINCT callsign) AS distinct_callsigns
FROM flights
WHERE last_updated BETWEEN '2025-09-08 09:00:00' AND '2025-09-08 09:20:00'
GROUP BY minute
ORDER BY minute;

-- Fifth, try a more relaxed version of our original aircraft counting logic
SELECT
    COUNT(DISTINCT f.callsign) AS relaxed_airborne_count
FROM flights f
WHERE f.last_updated BETWEEN '2025-09-08 09:05:00' AND '2025-09-08 09:15:00'
  AND (f.altitude > 500 OR f.altitude IS NULL)  -- Reduced altitude threshold
  AND (f.groundspeed >= 30 OR f.groundspeed IS NULL);  -- Reduced speed threshold

