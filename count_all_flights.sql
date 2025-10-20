-- Count all flights and flight summaries
SELECT 
    (SELECT COUNT(*) FROM flights) AS active_flights_count,
    (SELECT COUNT(*) FROM flights_archive) AS archived_flights_count,
    (SELECT COUNT(*) FROM flight_summaries) AS flight_summaries_count,
    (SELECT COUNT(DISTINCT(callsign, cid, departure, arrival)) FROM flights) AS distinct_active_flights,
    (SELECT COUNT(DISTINCT(callsign, cid, departure, arrival)) FROM flights_archive) AS distinct_archived_flights,
    (SELECT COUNT(DISTINCT(callsign, cid, departure, arrival)) FROM flight_summaries) AS distinct_summaries;


