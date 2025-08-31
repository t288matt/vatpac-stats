-- Backfill controller_summaries.aircraft_details from flight_summaries.controller_callsigns
-- For each flight summary referencing a controller, ensure the overlapping controller session
-- contains that flight in its aircraft_details JSON array.

BEGIN;

WITH flight_ctrl AS (
  SELECT fs.id AS flight_summary_id,
         fs.callsign AS flight_callsign,
         fs.logon_time,
         COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time,
         key AS controller_callsign
  FROM flight_summaries fs
  CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
  WHERE fs.controller_callsigns IS NOT NULL
    AND fs.controller_callsigns <> '{}'::jsonb
), overlap AS (
  SELECT 
    fc.flight_callsign,
    fc.controller_callsign,
    cs.id AS controller_summary_id,
    cs.aircraft_details
  FROM flight_ctrl fc
  JOIN controller_summaries cs
    ON cs.callsign = fc.controller_callsign
   AND cs.session_start_time <= fc.completion_time
   AND (cs.session_end_time IS NULL OR cs.session_end_time >= fc.logon_time)
), missing AS (
  SELECT DISTINCT 
    controller_summary_id,
    controller_callsign,
    flight_callsign
  FROM overlap o
  WHERE NOT EXISTS (
    SELECT 1
    FROM jsonb_array_elements(COALESCE(o.aircraft_details, '[]'::jsonb)) AS d
    WHERE d->>'callsign' = o.flight_callsign
  )
)
UPDATE controller_summaries cs
SET aircraft_details = COALESCE(cs.aircraft_details, '[]'::jsonb) || jsonb_build_array(jsonb_build_object('callsign', m.flight_callsign)),
    updated_at = NOW()
FROM missing m
WHERE cs.id = m.controller_summary_id;

COMMIT;


