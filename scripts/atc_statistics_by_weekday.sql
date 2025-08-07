-- ATC Communication Statistics by Weekday
-- 
-- This query shows the overall statistics for all flights broken down by weekday:
-- "Number of flight data records in contact with ATC" over "Total flight data records" by weekday
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/atc_statistics_by_weekday.sql
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
    SELECT ft.callsign as flight_callsign, ft.frequency_mhz, ft.timestamp as flight_time
    FROM flight_transceivers ft 
    JOIN atc_transceivers at ON ft.frequency_mhz = at.frequency_mhz 
    AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= 180
    WHERE (SQRT(POWER(ft.position_lat - at.position_lat, 2) + POWER(ft.position_lon - at.position_lon, 2))) <= 300
),
flight_records_with_atc AS (
    SELECT f.callsign, EXTRACT(DOW FROM f.last_updated) as weekday, COUNT(*) as records_with_atc
    FROM flights f 
    WHERE EXISTS (
        SELECT 1 FROM frequency_matches fm 
        WHERE fm.flight_callsign = f.callsign 
        AND ABS(EXTRACT(EPOCH FROM (f.last_updated - fm.flight_time))) <= 180
    )
    GROUP BY f.callsign, EXTRACT(DOW FROM f.last_updated)
),
flight_records_total AS (
    SELECT callsign, EXTRACT(DOW FROM last_updated) as weekday, COUNT(*) as total_records 
    FROM flights 
    GROUP BY callsign, EXTRACT(DOW FROM last_updated)
)
SELECT 
    CASE fr.weekday
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as weekday_name,
    fr.weekday as weekday_number,
    COUNT(DISTINCT fr.callsign) as total_flights_in_weekday,
    SUM(fr.total_records) as total_flight_data_records,
    SUM(COALESCE(fa.records_with_atc, 0)) as flight_data_records_in_contact_with_atc,
    ROUND((SUM(COALESCE(fa.records_with_atc, 0))::numeric / SUM(fr.total_records)::numeric * 100), 2) as percentage_with_atc
FROM flight_records_total fr
LEFT JOIN flight_records_with_atc fa ON fr.callsign = fa.callsign AND fr.weekday = fa.weekday
GROUP BY fr.weekday
ORDER BY fr.weekday;
