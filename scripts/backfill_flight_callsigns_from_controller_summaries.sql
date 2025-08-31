-- Backfill flight_summaries.controller_callsigns from controller_summaries
-- Strategy: For each flight summary lacking ATC data, find overlapping controller sessions
-- that list the flight in cs.aircraft_details and aggregate controller callsigns into a JSONB object.

BEGIN;

WITH candidate AS (
  SELECT fs.id,
         fs.callsign,
         fs.logon_time,
         COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time
  FROM flight_summaries fs
  WHERE fs.controller_callsigns IS NULL OR fs.controller_callsigns = '{}'::jsonb
), matches AS (
  SELECT
    c.id AS flight_summary_id,
    cs.callsign AS controller_callsign
  FROM candidate c
  JOIN controller_summaries cs
    ON cs.session_start_time <= c.completion_time
   AND (cs.session_end_time IS NULL OR cs.session_end_time >= c.logon_time)
  WHERE EXISTS (
    SELECT 1
    FROM jsonb_array_elements(cs.aircraft_details) AS d
    WHERE d->>'callsign' = c.callsign
  )
), agg AS (
  SELECT flight_summary_id,
         jsonb_object_agg(controller_callsign, '{}'::jsonb) AS controller_map
  FROM matches
  GROUP BY flight_summary_id
)
UPDATE flight_summaries fs
SET controller_callsigns = COALESCE(fs.controller_callsigns, '{}'::jsonb) || a.controller_map,
    updated_at = NOW()
FROM agg a
WHERE fs.id = a.flight_summary_id;

COMMIT;


