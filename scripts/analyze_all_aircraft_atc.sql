-- All Aircraft ATC Communication Analysis
-- 
-- This query analyzes all aircraft in the database to determine what percentage
-- of their flight records occurred during ATC communication periods.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/analyze_all_aircraft_atc.sql
--

-- Individual Aircraft Analysis (sorted by ATC percentage, highest first)
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
    SELECT f.callsign, COUNT(*) as records_with_atc
    FROM flights f 
    WHERE EXISTS (
        SELECT 1 FROM frequency_matches fm 
        WHERE fm.flight_callsign = f.callsign 
        AND ABS(EXTRACT(EPOCH FROM (f.last_updated - fm.flight_time))) <= 180
    )
    GROUP BY f.callsign
),
flight_records_total AS (
    SELECT callsign, COUNT(*) as total_records 
    FROM flights 
    GROUP BY callsign
)
SELECT 
    fr.callsign,
    fr.total_records as total_flight_data_records,
    COALESCE(fa.records_with_atc, 0) as flight_data_records_in_contact_with_atc,
    ROUND((COALESCE(fa.records_with_atc, 0)::numeric / fr.total_records::numeric * 100), 2) as percentage_with_atc
FROM flight_records_total fr
LEFT JOIN flight_records_with_atc fa ON fr.callsign = fa.callsign
ORDER BY percentage_with_atc DESC, fr.total_records DESC;
