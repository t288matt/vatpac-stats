-- Dry-run: Inspect candidate exit timestamps for flight_sector_occupancy without making changes
-- Place this file in ./scripts and run with psql inside the postgres container.

-- Phase 0: diagnostics counts
SELECT 'total_fso' AS metric, COUNT(*) FROM flight_sector_occupancy;
SELECT 'fso_no_exit' AS metric, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NULL;
SELECT 'fso_exit_nonpos' AS metric, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL AND (duration_seconds IS NULL OR duration_seconds <= 0);

-- Phase 1: show sample rows where exit exists but duration is non-positive and computed value
SELECT id, callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds,
       EXTRACT(EPOCH FROM (exit_timestamp - entry_timestamp))::INTEGER AS computed_seconds
FROM flight_sector_occupancy
WHERE exit_timestamp IS NOT NULL
  AND (duration_seconds IS NULL OR duration_seconds <= 0)
ORDER BY entry_timestamp DESC
LIMIT 100;

-- Phase 2: Show earliest flights.last_updated >= entry_timestamp for a batch of 500 open rows
WITH to_process AS (
  SELECT id, callsign, entry_timestamp
  FROM flight_sector_occupancy
  WHERE exit_timestamp IS NULL
  ORDER BY entry_timestamp
  LIMIT 500
)
SELECT t.id, t.callsign, t.entry_timestamp,
       f.last_updated AS candidate_last_updated, f.latitude AS candidate_lat, f.longitude AS candidate_lon, f.altitude AS candidate_alt,
       CASE WHEN f.last_updated IS NOT NULL THEN EXTRACT(EPOCH FROM (f.last_updated - t.entry_timestamp))::INTEGER ELSE NULL END AS computed_seconds
FROM to_process t
LEFT JOIN LATERAL (
  SELECT latitude, longitude, altitude, last_updated
  FROM flights f
  WHERE f.callsign = t.callsign AND f.last_updated >= t.entry_timestamp
  ORDER BY f.last_updated ASC
  LIMIT 1
) f ON true
ORDER BY t.entry_timestamp;

-- Count how many of the selected batch had a candidate in flights
WITH to_process AS (
  SELECT id, callsign, entry_timestamp
  FROM flight_sector_occupancy
  WHERE exit_timestamp IS NULL
  ORDER BY entry_timestamp
  LIMIT 500
)
SELECT 'batch_size' AS metric, COUNT(*) FROM to_process;
WITH to_process AS (
  SELECT id, callsign, entry_timestamp
  FROM flight_sector_occupancy
  WHERE exit_timestamp IS NULL
  ORDER BY entry_timestamp
  LIMIT 500
)
SELECT 'candidates_in_flights' AS metric, COUNT(*) FROM (
  SELECT 1
  FROM to_process t
  JOIN LATERAL (
    SELECT last_updated
    FROM flights f
    WHERE f.callsign = t.callsign AND f.last_updated >= t.entry_timestamp
    ORDER BY f.last_updated ASC
    LIMIT 1
  ) f ON true
) s;

-- Phase 3: Same for flights_archive
WITH to_process AS (
  SELECT id, callsign, entry_timestamp
  FROM flight_sector_occupancy
  WHERE exit_timestamp IS NULL
  ORDER BY entry_timestamp
  LIMIT 500
)
SELECT t.id, t.callsign, t.entry_timestamp,
       fa.last_updated AS candidate_last_updated, fa.latitude AS candidate_lat, fa.longitude AS candidate_lon, fa.altitude AS candidate_alt,
       CASE WHEN fa.last_updated IS NOT NULL THEN EXTRACT(EPOCH FROM (fa.last_updated - t.entry_timestamp))::INTEGER ELSE NULL END AS computed_seconds
FROM to_process t
LEFT JOIN LATERAL (
  SELECT latitude, longitude, altitude, last_updated
  FROM flights_archive fa
  WHERE fa.callsign = t.callsign AND fa.last_updated >= t.entry_timestamp
  ORDER BY fa.last_updated ASC
  LIMIT 1
) fa ON true
ORDER BY t.entry_timestamp;

WITH to_process AS (
  SELECT id, callsign, entry_timestamp
  FROM flight_sector_occupancy
  WHERE exit_timestamp IS NULL
  ORDER BY entry_timestamp
  LIMIT 500
)
SELECT 'candidates_in_flights_archive' AS metric, COUNT(*) FROM (
  SELECT 1
  FROM to_process t
  JOIN LATERAL (
    SELECT last_updated
    FROM flights_archive fa
    WHERE fa.callsign = t.callsign AND fa.last_updated >= t.entry_timestamp
    ORDER BY fa.last_updated ASC
    LIMIT 1
  ) fa ON true
) s;

-- Phase 4: Same for flight_summaries.completion_time
WITH to_process AS (
  SELECT id, callsign, entry_timestamp
  FROM flight_sector_occupancy
  WHERE exit_timestamp IS NULL
  ORDER BY entry_timestamp
  LIMIT 500
)
SELECT t.id, t.callsign, t.entry_timestamp,
       fs.completion_time AS candidate_time,
       CASE WHEN fs.completion_time IS NOT NULL THEN EXTRACT(EPOCH FROM (fs.completion_time - t.entry_timestamp))::INTEGER ELSE NULL END AS computed_seconds
FROM to_process t
LEFT JOIN LATERAL (
  SELECT completion_time
  FROM flight_summaries fs
  WHERE fs.callsign = t.callsign AND fs.completion_time >= t.entry_timestamp
  ORDER BY fs.completion_time ASC
  LIMIT 1
) fs ON true
ORDER BY t.entry_timestamp;

WITH to_process AS (
  SELECT id, callsign, entry_timestamp
  FROM flight_sector_occupancy
  WHERE exit_timestamp IS NULL
  ORDER BY entry_timestamp
  LIMIT 500
)
SELECT 'candidates_in_flight_summaries' AS metric, COUNT(*) FROM (
  SELECT 1
  FROM to_process t
  JOIN LATERAL (
    SELECT completion_time
    FROM flight_summaries fs
    WHERE fs.callsign = t.callsign AND fs.completion_time >= t.entry_timestamp
    ORDER BY fs.completion_time ASC
    LIMIT 1
  ) fs ON true
) s;

-- Phase 5: sample a set of fully backfilled rows (exit_timestamp IS NOT NULL) and compute statistics
SELECT
  COUNT(*) FILTER (WHERE duration_seconds > 0) AS positive_durations,
  COUNT(*) FILTER (WHERE duration_seconds = 0) AS zero_durations,
  COUNT(*) FILTER (WHERE duration_seconds < 0) AS negative_durations,
  AVG(duration_seconds) FILTER (WHERE duration_seconds > 0) AS avg_positive_seconds
FROM flight_sector_occupancy;

-- End of dry-run
