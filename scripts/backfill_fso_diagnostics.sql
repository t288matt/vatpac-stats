-- Diagnostics script for flight_sector_occupancy (post-backfill)

-- 1) Overall counts
SELECT 'total_rows' AS metric, COUNT(*) FROM flight_sector_occupancy;
SELECT 'with_exit' AS metric, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL;
SELECT 'without_exit' AS metric, COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NULL;

-- 2) Duration distribution buckets
SELECT
  CASE
    WHEN duration_seconds IS NULL THEN 'NULL'
    WHEN duration_seconds < 0 THEN '<0'
    WHEN duration_seconds = 0 THEN '0'
    WHEN duration_seconds <= 60 THEN '0-60s'
    WHEN duration_seconds <= 300 THEN '1-5m'
    WHEN duration_seconds <= 1800 THEN '5-30m'
    WHEN duration_seconds <= 3600 THEN '30-60m'
    ELSE '>60m'
  END AS bucket, COUNT(*)
FROM flight_sector_occupancy
GROUP BY bucket ORDER BY COUNT(*) DESC;

-- 3) Per-sector aggregates (top 20 by rows)
SELECT sector_name, COUNT(*) AS cnt, AVG(duration_seconds) FILTER (WHERE duration_seconds > 0) AS avg_pos_seconds, MAX(duration_seconds) AS max_seconds
FROM flight_sector_occupancy
GROUP BY sector_name
ORDER BY cnt DESC
LIMIT 20;

-- 4) Sample negative-duration rows (if any)
SELECT id, callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds, EXTRACT(EPOCH FROM (exit_timestamp - entry_timestamp))::INT AS computed_seconds
FROM flight_sector_occupancy
WHERE duration_seconds IS NOT NULL AND duration_seconds < 0
ORDER BY entry_timestamp DESC
LIMIT 50;

-- 5) Sample rows updated recently (last hour)
SELECT id, callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds
FROM flight_sector_occupancy
WHERE entry_timestamp >= now() - interval '1 hour'
ORDER BY entry_timestamp DESC
LIMIT 100;

-- 6) Quick sanity: fraction of positive durations and average positive duration
SELECT
  SUM(CASE WHEN duration_seconds > 0 THEN 1 ELSE 0 END) AS positive_count,
  SUM(CASE WHEN duration_seconds > 0 THEN duration_seconds ELSE 0 END) AS positive_sum,
  (CASE WHEN SUM(CASE WHEN duration_seconds > 0 THEN 1 ELSE 0 END) = 0 THEN NULL ELSE (SUM(CASE WHEN duration_seconds > 0 THEN duration_seconds ELSE 0 END) / SUM(CASE WHEN duration_seconds > 0 THEN 1 ELSE 0 END)) END) AS avg_positive_seconds
FROM flight_sector_occupancy;

-- End diagnostics
