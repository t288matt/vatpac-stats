-- Backfill flight_sector_occupancy exit fields using latest flights data
-- Idempotent: only updates rows where exit_timestamp IS NULL and a matching
-- flights row exists with non-null altitude/position.

BEGIN;

-- Preview rows that would be updated
-- Uncomment the SELECT below to preview before running the UPDATE.
-- SELECT fso.id, fso.callsign, fso.entry_timestamp, f.altitude AS flight_altitude, f.latitude AS flight_lat, f.longitude AS flight_lon, f.last_updated
-- FROM flight_sector_occupancy fso
-- JOIN LATERAL (
--   SELECT altitude, latitude, longitude, last_updated
--   FROM flights f
--   WHERE f.callsign = fso.callsign
--   AND f.last_updated <= NOW()
--   ORDER BY last_updated DESC
--   LIMIT 1
-- ) f ON true
-- WHERE fso.exit_timestamp IS NULL
-- AND f.altitude IS NOT NULL
-- ORDER BY fso.entry_timestamp DESC
-- LIMIT 100;

-- Idempotent update: populate exit_timestamp, exit_altitude, exit_lat, exit_lon, duration_seconds
WITH candidates AS (
  SELECT fso.id, fso.entry_timestamp, fso.callsign,
         f.altitude AS flight_altitude, f.latitude AS flight_lat, f.longitude AS flight_lon, f.last_updated
  FROM flight_sector_occupancy fso
  JOIN LATERAL (
    SELECT altitude, latitude, longitude, last_updated
    FROM flights f
    WHERE f.callsign = fso.callsign
      AND f.last_updated <= NOW()
    ORDER BY last_updated DESC
    LIMIT 1
  ) f ON true
  WHERE fso.exit_timestamp IS NULL
    AND f.altitude IS NOT NULL
)
UPDATE flight_sector_occupancy fso
SET exit_timestamp = c.last_updated,
    exit_altitude = c.flight_altitude,
    exit_lat = COALESCE(fso.exit_lat, c.flight_lat),
    exit_lon = COALESCE(fso.exit_lon, c.flight_lon),
    duration_seconds = EXTRACT(EPOCH FROM (c.last_updated - fso.entry_timestamp))::INTEGER
FROM candidates c
WHERE fso.id = c.id
  AND (fso.exit_timestamp IS NULL OR fso.exit_altitude IS NULL OR fso.duration_seconds IS NULL);

-- Report how many rows were updated
SELECT COUNT(*) AS rows_updated FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL AND created_at >= NOW() - INTERVAL '1 minute';

COMMIT;

-- Notes:
-- - Run this during a maintenance window or test on a replica first.
-- - The SELECT preview can be uncommented to verify candidates before executing.
-- - The update uses the latest flights record at or before NOW(); you may prefer
--   to use a different time pivot (e.g., last_updated <= fso.exit_timestamp if exit_timestamp existed).


