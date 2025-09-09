-- diagnostics_controller_sessions.sql
-- List controller_summaries sessions overlapping recent Monday 08:00-12:00 UTC
WITH recent_monday AS (
    SELECT CASE WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
                ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
           END AS monday_date
)
SELECT id, callsign, session_start_time, session_end_time, total_aircraft_handled, frequencies_used, aircraft_details
FROM controller_summaries cs
CROSS JOIN recent_monday rm
WHERE cs.session_start_time < rm.monday_date + INTERVAL '12 hours'
  AND (cs.session_end_time IS NULL OR cs.session_end_time > rm.monday_date + INTERVAL '8 hours')
ORDER BY cs.session_start_time DESC;
