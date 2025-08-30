-- Controller -> Flight bidirectional integrity check
-- Returns controller session flight references not reciprocated by any overlapping flight summary

WITH params AS (
  SELECT 
    TIMESTAMPTZ '2025-08-29 12:00:00+00' AS window_start,
    TIMESTAMPTZ '2025-08-30 00:00:00+00' AS window_end
),
ctrl_flights AS (
  SELECT
    cs.id AS controller_summary_id,
    cs.callsign AS controller_callsign,
    cs.session_start_time,
    COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') AS session_end_time,
    d->>'callsign' AS flight_callsign
  FROM controller_summaries cs
  CROSS JOIN LATERAL jsonb_array_elements(cs.aircraft_details) AS d
  CROSS JOIN params p
  WHERE cs.session_start_time <= p.window_end
    AND COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') >= p.window_start
)
SELECT cf.*
FROM ctrl_flights cf
LEFT JOIN flight_summaries fs
  ON fs.callsign = cf.flight_callsign
  AND fs.logon_time <= cf.session_end_time
  AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= cf.session_start_time
WHERE fs.id IS NULL
   OR fs.controller_callsigns IS NULL
   OR fs.controller_callsigns = '{}'::jsonb
   OR NOT (fs.controller_callsigns ? cf.controller_callsign);


