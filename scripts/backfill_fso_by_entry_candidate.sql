-- Create a batchable, idempotent backfill script for flight_sector_occupancy
-- Usage: run in psql against a test DB snapshot. Adjust LIMIT and logging as needed.

-- Phase 0: diagnostics
-- Count total rows and problematic rows
SELECT 'total_fso' AS metric, COUNT(*) FROM flight_sector_occupancy;
SELECT 'fso_no_exit' AS metric, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NULL;
SELECT 'fso_exit_nonpos' AS metric, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL AND (duration_seconds IS NULL OR duration_seconds <= 0);

-- Phase 1: Recompute durations where exit_timestamp exists (safe)
-- Run in batches to avoid long transactions
\echo 'Phase 1: recompute durations for rows with exit_timestamp'
WITH to_fix AS (
  SELECT id
  FROM flight_sector_occupancy
  WHERE exit_timestamp IS NOT NULL
    AND (duration_seconds IS NULL OR duration_seconds <= 0)
  LIMIT 500
), updated AS (
  UPDATE flight_sector_occupancy fso
  SET duration_seconds = EXTRACT(EPOCH FROM (exit_timestamp - entry_timestamp))::INTEGER
  FROM to_fix t
  WHERE fso.id = t.id
  RETURNING fso.id
)
SELECT COUNT(*) AS updated_count FROM updated;

-- Phase 2: Backfill exit using flights (earliest flights.last_updated >= entry_timestamp)
\echo 'Phase 2: backfill using flights'
WITH to_process AS (
  SELECT fso.id, fso.callsign, fso.entry_timestamp
  FROM flight_sector_occupancy fso
  WHERE fso.exit_timestamp IS NULL
  ORDER BY fso.entry_timestamp
  LIMIT 500
), candidates AS (
  SELECT t.id, f.latitude, f.longitude, f.altitude, f.last_updated
  FROM to_process t
  JOIN LATERAL (
    SELECT latitude, longitude, altitude, last_updated
    FROM flights f
    WHERE f.callsign = t.callsign AND f.last_updated >= t.entry_timestamp
    ORDER BY f.last_updated ASC
    LIMIT 1
  ) f ON true
), updated AS (
  UPDATE flight_sector_occupancy fso
  SET exit_timestamp = c.last_updated,
      exit_lat = COALESCE(fso.exit_lat, c.latitude),
      exit_lon = COALESCE(fso.exit_lon, c.longitude),
      exit_altitude = COALESCE(fso.exit_altitude, c.altitude),
      duration_seconds = EXTRACT(EPOCH FROM (c.last_updated - fso.entry_timestamp))::INTEGER
  FROM candidates c
  WHERE fso.id = c.id
  RETURNING fso.id
)
SELECT COUNT(*) AS updated_count FROM updated;

-- Phase 3: Backfill using flights_archive (earliest archive.last_updated >= entry_timestamp)
\echo 'Phase 3: backfill using flights_archive'
WITH to_process AS (
  SELECT fso.id, fso.callsign, fso.entry_timestamp
  FROM flight_sector_occupancy fso
  WHERE fso.exit_timestamp IS NULL
  ORDER BY fso.entry_timestamp
  LIMIT 500
), candidates AS (
  SELECT t.id, fa.latitude, fa.longitude, fa.altitude, fa.last_updated
  FROM to_process t
  JOIN LATERAL (
    SELECT latitude, longitude, altitude, last_updated
    FROM flights_archive fa
    WHERE fa.callsign = t.callsign AND fa.last_updated >= t.entry_timestamp
    ORDER BY fa.last_updated ASC
    LIMIT 1
  ) fa ON true
), updated AS (
  UPDATE flight_sector_occupancy fso
  SET exit_timestamp = c.last_updated,
      exit_lat = COALESCE(fso.exit_lat, c.latitude),
      exit_lon = COALESCE(fso.exit_lon, c.longitude),
      exit_altitude = COALESCE(fso.exit_altitude, c.altitude),
      duration_seconds = EXTRACT(EPOCH FROM (c.last_updated - fso.entry_timestamp))::INTEGER
  FROM candidates c
  WHERE fso.id = c.id
  RETURNING fso.id
)
SELECT COUNT(*) AS updated_count FROM updated;

-- Phase 4: Backfill using flight_summaries.completion_time (earliest completion_time >= entry_timestamp)
\echo 'Phase 4: backfill using flight_summaries'
WITH to_process AS (
  SELECT fso.id, fso.callsign, fso.entry_timestamp
  FROM flight_sector_occupancy fso
  WHERE fso.exit_timestamp IS NULL
  ORDER BY fso.entry_timestamp
  LIMIT 500
), candidates AS (
  SELECT t.id, fs.completion_time
  FROM to_process t
  JOIN LATERAL (
    SELECT completion_time
    FROM flight_summaries fs
    WHERE fs.callsign = t.callsign AND fs.completion_time >= t.entry_timestamp
    ORDER BY fs.completion_time ASC
    LIMIT 1
  ) fs ON true
), updated AS (
  UPDATE flight_sector_occupancy fso
  SET exit_timestamp = c.completion_time,
      duration_seconds = EXTRACT(EPOCH FROM (c.completion_time - fso.entry_timestamp))::INTEGER
  FROM candidates c
  WHERE fso.id = c.id
  RETURNING fso.id
)
SELECT COUNT(*) AS updated_count FROM updated;

-- Phase 5: diagnostics after a run
SELECT 'post_total_fso' AS metric, COUNT(*) FROM flight_sector_occupancy;
SELECT 'post_fso_no_exit' AS metric, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NULL;
SELECT 'post_fso_exit_nonpos' AS metric, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL AND (duration_seconds IS NULL OR duration_seconds <= 0);
