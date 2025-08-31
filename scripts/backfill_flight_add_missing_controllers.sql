-- Add missing controller keys to flight_summaries for overlaps present in controller_summaries

BEGIN;

WITH ctrl_flights AS (
  SELECT
    cs.callsign AS controller_callsign,
    cs.session_start_time,
    COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') AS session_end_time,
    d->>'callsign' AS flight_callsign
  FROM controller_summaries cs
  CROSS JOIN LATERAL jsonb_array_elements(cs.aircraft_details) AS d
)
, cf_overlaps AS (
  SELECT DISTINCT
    fs.id AS flight_summary_id,
    cf.controller_callsign
  FROM ctrl_flights cf
  JOIN flight_summaries fs
    ON fs.callsign = cf.flight_callsign
   AND fs.logon_time <= cf.session_end_time
   AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= cf.session_start_time
)
, missing AS (
  SELECT o.flight_summary_id, o.controller_callsign
  FROM cf_overlaps o
  JOIN flight_summaries fs ON fs.id = o.flight_summary_id
  WHERE fs.controller_callsigns IS NULL
     OR fs.controller_callsigns = '{}'::jsonb
     OR NOT (fs.controller_callsigns ? o.controller_callsign)
)
UPDATE flight_summaries fs
SET controller_callsigns = COALESCE(fs.controller_callsigns, '{}'::jsonb) || jsonb_build_object(m.controller_callsign, '{}'::jsonb),
    updated_at = NOW()
FROM missing m
WHERE fs.id = m.flight_summary_id;

COMMIT;


