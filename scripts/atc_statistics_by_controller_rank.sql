-- ATC Communication Statistics by Controller Rank
-- 
-- This query shows the overall statistics for all flights broken down by controller rank:
-- "Number of flight data records in contact with ATC" over "Total flight data records" by controller rank
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/atc_statistics_by_controller_rank.sql
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
    JOIN atc_transceivers at ON ft.frequency_mhz = at.frequency_mhz 
    AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= 180
    WHERE (SQRT(POWER(ft.position_lat - at.position_lat, 2) + POWER(ft.position_lon - at.position_lon, 2))) <= 300
),
flight_records_with_atc AS (
    SELECT f.callsign, c.controller_rating as controller_rank, COUNT(*) as records_with_atc
    FROM flights f 
    JOIN frequency_matches fm ON fm.flight_callsign = f.callsign 
    AND ABS(EXTRACT(EPOCH FROM (f.last_updated - fm.flight_time))) <= 180
    JOIN controllers c ON fm.controller_callsign = c.callsign
    WHERE c.facility != 'OBS'
    GROUP BY f.callsign, c.controller_rating
),
flight_records_total AS (
    SELECT callsign, COUNT(*) as total_records 
    FROM flights 
    GROUP BY callsign
)
SELECT 
    fr.controller_rank,
    CASE fr.controller_rank
        WHEN 1 THEN 'Observer'
        WHEN 2 THEN 'Student'
        WHEN 3 THEN 'Student 2'
        WHEN 4 THEN 'Student 3'
        WHEN 5 THEN 'Controller'
        WHEN 6 THEN 'Controller 2'
        WHEN 7 THEN 'Instructor'
        WHEN 8 THEN 'Instructor 2'
        WHEN 9 THEN 'Supervisor'
        WHEN 10 THEN 'Administrator'
        ELSE 'Unknown'
    END as rank_name,
    COUNT(DISTINCT fr.callsign) as total_flights_with_rank,
    SUM(fr.total_records) as total_flight_data_records,
    SUM(COALESCE(fa.records_with_atc, 0)) as flight_data_records_in_contact_with_atc,
    ROUND((SUM(COALESCE(fa.records_with_atc, 0))::numeric / SUM(fr.total_records)::numeric * 100), 2) as percentage_with_atc
FROM flight_records_total fr
LEFT JOIN flight_records_with_atc fa ON fr.callsign = fa.callsign
GROUP BY fr.controller_rank
ORDER BY fr.controller_rank;
