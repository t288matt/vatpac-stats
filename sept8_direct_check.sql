-- Direct check of raw flight data on Sept 8
-- This query examines the raw flight data with minimal filtering

-- Check 1: Raw record counts throughout the morning
SELECT
    EXTRACT(HOUR FROM last_updated) AS hour,
    EXTRACT(MINUTE FROM last_updated)::int / 5 * 5 AS minute_bucket,
    COUNT(*) AS record_count,
    COUNT(DISTINCT callsign) AS unique_aircraft
FROM flights
WHERE DATE(last_updated) = '2025-09-08'
  AND EXTRACT(HOUR FROM last_updated) BETWEEN 7 AND 12
GROUP BY hour, minute_bucket
ORDER BY hour, minute_bucket;

-- Check 2: Direct examination of data around 09:45
SELECT
    callsign,
    aircraft_type,
    altitude,
    groundspeed,
    last_updated,
    departure,
    arrival
FROM flights
WHERE DATE(last_updated) = '2025-09-08'
  AND last_updated BETWEEN '2025-09-08 09:30:00' AND '2025-09-08 10:00:00'
ORDER BY last_updated;

-- Check 3: Check for data across a wider time window to see if there's a complete gap
SELECT
    DATE_TRUNC('hour', last_updated) AS hour_bucket,
    COUNT(*) AS record_count
FROM flights
WHERE DATE(last_updated) = '2025-09-08'
GROUP BY hour_bucket
ORDER BY hour_bucket;

-- Check 4: Compare with the previous Monday to see if this is a systemic issue
SELECT
    EXTRACT(HOUR FROM last_updated) AS hour,
    EXTRACT(MINUTE FROM last_updated)::int / 5 * 5 AS minute_bucket,
    COUNT(*) AS record_count,
    COUNT(DISTINCT callsign) AS unique_aircraft
FROM flights
WHERE DATE(last_updated) = '2025-09-01'
  AND EXTRACT(HOUR FROM last_updated) BETWEEN 7 AND 12
GROUP BY hour, minute_bucket
ORDER BY hour, minute_bucket;

-- Check 5: Look for any airborne aircraft with minimal criteria
SELECT
    callsign,
    COUNT(*) as position_reports,
    MIN(last_updated) as first_seen,
    MAX(last_updated) as last_seen,
    MAX(altitude) as max_altitude,
    MAX(groundspeed) as max_groundspeed
FROM flights
WHERE DATE(last_updated) = '2025-09-08'
  AND EXTRACT(HOUR FROM last_updated) BETWEEN 9 AND 10
  AND altitude > 0
GROUP BY callsign
ORDER BY callsign;

