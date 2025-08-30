-- Flight -> Controller bidirectional integrity check
-- Returns flights whose controller references are not reciprocated by any overlapping controller session

WITH params AS (
  SELECT 
    TIMESTAMPTZ '2025-08-29 12:00:00+00' AS window_start,
    TIMESTAMPTZ '2025-08-30 00:00:00+00' AS window_end
),
flight_ctrl AS (
  SELECT
    fs.id AS flight_summary_id,
    fs.callsign AS flight_callsign,
    fs.logon_time,
    COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time,
    key AS controller_callsign
  FROM flight_summaries fs
  CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
  CROSS JOIN params p
  WHERE fs.controller_callsigns IS NOT NULL
    AND fs.controller_callsigns <> '{}'::jsonb
    -- Restrict to flights overlapping the target window
    AND fs.logon_time <= p.window_end
    AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= p.window_start
)
SELECT fc.*
FROM flight_ctrl fc
WHERE NOT EXISTS (
  SELECT 1
  FROM controller_summaries cs
  WHERE cs.callsign = fc.controller_callsign
    AND cs.session_start_time <= fc.completion_time
    AND (cs.session_end_time IS NULL OR cs.session_end_time >= fc.logon_time)
    AND EXISTS (
      SELECT 1
      FROM jsonb_array_elements(cs.aircraft_details) AS d
      WHERE d->>'callsign' = fc.flight_callsign
    )
);


