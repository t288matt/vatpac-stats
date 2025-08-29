-- ATC Communication Statistics by Position Type
-- 
-- This query shows the overall statistics for all flights broken down by ATC position type:
-- "Number of flight data records in contact with ATC" over "Total flight data records" by position
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/percentage_of_time_all_acft_on_atc_by_position.sql
--

WITH flight_transceivers AS (
    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
    FROM transceivers t 
    WHERE t.entity_type = 'flight'
),
atc_transceivers AS (
    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
    FROM transceivers t 
    WHERE t.entity_type = 'atc' 
    AND t.callsign IN (SELECT DISTINCT c.callsign FROM controllers c WHERE c.facility != 'OBS')
),
frequency_matches AS (
    SELECT ft.callsign as flight_callsign, ft.frequency_mhz, ft.timestamp as flight_time, at.callsign as controller_callsign
    FROM flight_transceivers ft 
    JOIN atc_transceivers at
      ON ABS(ft.frequency_mhz - at.frequency_mhz) <= 0.005 
    AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= 180
    WHERE (SQRT(POWER(ft.position_lat - at.position_lat, 2) + POWER(ft.position_lon - at.position_lon, 2))) <= 300
),
flight_records_with_atc AS (
    SELECT f.callsign, 
           CASE 
               WHEN c.position LIKE '%FSS%' THEN 'FSS'
               WHEN c.position LIKE '%CTR%' THEN 'CTR'
               WHEN c.position LIKE '%APP%' THEN 'APP'
               WHEN c.position LIKE '%TWR%' THEN 'TWR'
               WHEN c.position LIKE '%GND%' THEN 'GND'
               WHEN c.position LIKE '%DEL%' THEN 'DEL'
               ELSE 'OTHER'
           END as position_type,
           COUNT(*) as records_with_atc
    FROM flights f 
    JOIN frequency_matches fm ON fm.flight_callsign = f.callsign 
    AND ABS(EXTRACT(EPOCH FROM (f.last_updated - fm.flight_time))) <= 180
    JOIN controllers c ON fm.controller_callsign = c.callsign
    WHERE c.facility != 'OBS'
    GROUP BY f.callsign, 
             CASE 
                 WHEN c.position LIKE '%FSS%' THEN 'FSS'
                 WHEN c.position LIKE '%CTR%' THEN 'CTR'
                 WHEN c.position LIKE '%APP%' THEN 'APP'
                 WHEN c.position LIKE '%TWR%' THEN 'TWR'
                 WHEN c.position LIKE '%GND%' THEN 'GND'
                 WHEN c.position LIKE '%DEL%' THEN 'DEL'
                 ELSE 'OTHER'
             END
),
flight_records_total AS (
    SELECT callsign, COUNT(*) as total_records 
    FROM flights 
    GROUP BY callsign
)
SELECT 
    fa.position_type,
    COUNT(DISTINCT fr.callsign) as total_flights_with_position,
    SUM(fr.total_records) as total_flight_data_records,
    SUM(COALESCE(fa.records_with_atc, 0)) as flight_data_records_in_contact_with_atc,
    ROUND((SUM(COALESCE(fa.records_with_atc, 0))::numeric / SUM(fr.total_records)::numeric * 100), 2) as percentage_with_atc
FROM flight_records_total fr
LEFT JOIN flight_records_with_atc fa ON fr.callsign = fa.callsign
GROUP BY fa.position_type
ORDER BY percentage_with_atc DESC, total_flight_data_records DESC;
