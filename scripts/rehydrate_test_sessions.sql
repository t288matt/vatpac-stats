-- Rehydrate ~50 archived sessions back into flights for pipeline testing
-- WARNING: Use in non-production or with caution; inserts rows into flights

BEGIN;

CREATE TEMP TABLE tmp_sessions AS
SELECT 
  callsign,
  cid,
  departure,
  arrival,
  MIN(logon_time) AS session_start,
  MAX(last_updated) AS session_end
FROM flights_archive
WHERE last_updated <= NOW() - INTERVAL '8 hours'
GROUP BY callsign, cid, departure, arrival
ORDER BY session_end DESC
LIMIT 50;

-- Optional: clean any existing rows in flights for these windows to avoid duplication
DELETE FROM flights f
USING tmp_sessions t
WHERE f.callsign = t.callsign
  AND f.cid = t.cid
  AND f.departure = t.departure
  AND f.arrival = t.arrival
  AND f.last_updated BETWEEN t.session_start AND t.session_end;

-- Insert from archive back to flights for the selected windows
INSERT INTO flights (
  callsign, aircraft_type, departure, arrival, logon_time,
  route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
  cid, name, server, pilot_rating, military_rating,
  latitude, longitude, altitude, groundspeed, heading,
  last_updated, deptime, 
  revision_id, assigned_transponder, transponder, qnh_i_hg, qnh_mb, last_updated_api
)
SELECT 
  fa.callsign, fa.aircraft_type, fa.departure, fa.arrival, fa.logon_time,
  fa.route, fa.flight_rules, fa.aircraft_faa, fa.planned_altitude, fa.aircraft_short,
  fa.cid, fa.name, fa.server, fa.pilot_rating, fa.military_rating,
  fa.latitude, fa.longitude, fa.altitude, fa.groundspeed, fa.heading,
  fa.last_updated, fa.deptime,
  NULL::integer AS revision_id, NULL::varchar(10) AS assigned_transponder, NULL::varchar(10) AS transponder,
  NULL::float AS qnh_i_hg, NULL::integer AS qnh_mb, NULL::timestamp with time zone AS last_updated_api
FROM flights_archive fa
JOIN tmp_sessions t
  ON fa.callsign = t.callsign
 AND fa.cid = t.cid
 AND fa.departure = t.departure
 AND fa.arrival = t.arrival
WHERE fa.last_updated BETWEEN t.session_start AND t.session_end;

COMMIT;


