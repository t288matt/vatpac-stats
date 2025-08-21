-- Flights in the last week grouped by CID prefix (ignoring last 5 digits)
-- Excludes flights with CID prefix 0
-- 
-- This query groups VATSIM CIDs by their prefix (first few digits)
-- and shows total flights and unique pilots for each group
-- 
-- Usage: Run this to see pilot activity patterns by VATSIM user ID ranges
-- 
-- CID prefix represents approximately 100,000 users per group

WITH cid_ranges AS (
    SELECT 
        FLOOR(cid / 100000) as cid_group, 
        cid 
    FROM flight_summaries 
    WHERE completion_time >= NOW() - INTERVAL '7 days'
        AND cid IS NOT NULL
        AND FLOOR(cid / 100000) > 0  -- Exclude CID prefix 0
)
SELECT 
    cid_group,
    COUNT(*) as total_flights,
    COUNT(DISTINCT cid) as unique_pilots
FROM cid_ranges 
GROUP BY cid_group 
ORDER BY cid_group;

-- Alternative view with more details (uncomment if needed):
/*
WITH cid_ranges AS (
    SELECT 
        FLOOR(cid / 100000) as cid_group, 
        cid,
        time_online_minutes,
        controller_time_percentage
    FROM flight_summaries 
    WHERE completion_time >= NOW() - INTERVAL '7 days'
        AND cid IS NOT NULL
        AND FLOOR(cid / 100000) > 0  -- Exclude CID prefix 0
)
SELECT 
    cid_group,
    COUNT(*) as total_flights,
    COUNT(DISTINCT cid) as unique_pilots,
    ROUND(AVG(time_online_minutes), 1) as avg_flight_duration_minutes,
    ROUND(AVG(controller_time_percentage), 1) as avg_atc_contact_percentage
FROM cid_ranges 
GROUP BY cid_group 
ORDER BY cid_group;
*/
