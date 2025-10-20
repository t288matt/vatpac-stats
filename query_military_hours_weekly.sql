-- Query to find military hours flown per week over last 98 days
-- Using flight_summaries table with time_online_minutes field
-- Comprehensive military aircraft list including fighters, bombers, transport, helicopters, etc.

SELECT 
    DATE_TRUNC('week', fs.completion_time) as week_end,
    ROUND(SUM(COALESCE(fs.time_online_minutes, 0)) / 60.0, 0) as military_hours
FROM flight_summaries fs
INNER JOIN flights f ON fs.callsign = f.callsign AND fs.cid = f.cid AND fs.logon_time = f.logon_time
WHERE f.remarks ILIKE '%RAAFVIRTUAL.ORG%'
    AND fs.completion_time >= NOW() - INTERVAL '98 days'
    AND fs.completion_time < NOW()
    AND fs.cid IS NOT NULL
GROUP BY DATE_TRUNC('week', fs.completion_time)
ORDER BY week_end DESC;
