-- DB-side backfill loop: recompute durations and backfill exits until convergence
-- Run inside postgres container: psql postgresql://vatsim_user:... -f /scripts/backfill_loop_db_side.sql

DO $$
DECLARE
  updated_count integer := 1;
  bf_count integer := 1;
  iter integer := 0;
  max_iter integer := 500;
BEGIN
  RAISE NOTICE 'Starting DB-side backfill loop';
  WHILE (updated_count > 0 OR bf_count > 0) AND iter < max_iter LOOP
    iter := iter + 1;
    RAISE NOTICE 'Iteration %', iter;

    -- Phase A: recompute durations for up to 500 rows where exit exists but duration non-positive
    WITH to_fix AS (
      SELECT id
      FROM flight_sector_occupancy
      WHERE exit_timestamp IS NOT NULL
        AND (duration_seconds IS NULL OR duration_seconds <= 0)
      LIMIT 500
    )
    UPDATE flight_sector_occupancy fso
    SET duration_seconds = EXTRACT(EPOCH FROM (exit_timestamp - entry_timestamp))::INTEGER
    FROM to_fix t
    WHERE fso.id = t.id;
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Recomputed durations: %', updated_count;

    -- Reset backfill counter for this iteration
    bf_count := 0;

    -- Phase B1: backfill using flights
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
    )
    UPDATE flight_sector_occupancy fso
    SET exit_timestamp = c.last_updated,
        exit_lat = COALESCE(fso.exit_lat, c.latitude),
        exit_lon = COALESCE(fso.exit_lon, c.longitude),
        exit_altitude = COALESCE(fso.exit_altitude, c.altitude),
        duration_seconds = EXTRACT(EPOCH FROM (c.last_updated - fso.entry_timestamp))::INTEGER
    FROM candidates c
    WHERE fso.id = c.id;
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    bf_count := bf_count + updated_count;
    RAISE NOTICE 'Backfilled from flights: %', updated_count;

    -- Phase B2: backfill using flights_archive
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
    )
    UPDATE flight_sector_occupancy fso
    SET exit_timestamp = c.last_updated,
        exit_lat = COALESCE(fso.exit_lat, c.latitude),
        exit_lon = COALESCE(fso.exit_lon, c.longitude),
        exit_altitude = COALESCE(fso.exit_altitude, c.altitude),
        duration_seconds = EXTRACT(EPOCH FROM (c.last_updated - fso.entry_timestamp))::INTEGER
    FROM candidates c
    WHERE fso.id = c.id;
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    bf_count := bf_count + updated_count;
    RAISE NOTICE 'Backfilled from flights_archive: %', updated_count;

    -- Phase B3: backfill using flight_summaries.completion_time
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
    )
    UPDATE flight_sector_occupancy fso
    SET exit_timestamp = c.completion_time,
        duration_seconds = EXTRACT(EPOCH FROM (c.completion_time - fso.entry_timestamp))::INTEGER
    FROM candidates c
    WHERE fso.id = c.id;
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    bf_count := bf_count + updated_count;
    RAISE NOTICE 'Backfilled from flight_summaries: %', updated_count;

    RAISE NOTICE 'Iteration summary: recompute=% backfill_total=%', updated_count, bf_count;

    -- small pause to avoid heavy IO
    PERFORM pg_sleep(0.1);
  END LOOP;

  RAISE NOTICE 'Loop finished after % iterations', iter;
END$$;

-- Clamp tiny negatives to zero
UPDATE flight_sector_occupancy SET duration_seconds = 0 WHERE duration_seconds < 0;

-- Final diagnostics
SELECT 'final_total' AS label, COUNT(*) FROM flight_sector_occupancy;
SELECT 'final_with_exit' AS label, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL;
SELECT 'final_no_exit' AS label, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NULL;
SELECT 'final_nonpos' AS label, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL AND (duration_seconds IS NULL OR duration_seconds <= 0);

-- Sample a few updated rows
SELECT id, callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds
FROM flight_sector_occupancy
ORDER BY entry_timestamp DESC
LIMIT 20;
