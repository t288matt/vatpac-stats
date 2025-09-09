-- diagnostics_controllers_search.sql
-- Check controllers table for reconnections/records for ML-BLA_CTR around the session window
WITH recent_monday AS (
    SELECT CASE WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
                ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
           END AS monday_date
)
SELECT c.id, c.callsign, c.logon_time, c.last_updated, c.frequency, c.server
FROM controllers c
WHERE c.callsign = 'ML-BLA_CTR'
  AND (c.logon_time >= (SELECT monday_date + INTERVAL '8 hours' FROM recent_monday) - INTERVAL '1 hour'
       AND c.logon_time <= (SELECT monday_date + INTERVAL '12 hours' FROM recent_monday) + INTERVAL '1 hour')
ORDER BY c.logon_time DESC;
