-- Count of unique controllers who logged on last week, broken down by rank groups
-- Shows how many controllers of each rank level were active in the past week

SELECT 
    CASE 
        WHEN cs.rating = 1 THEN 'Rank 1'
        WHEN cs.rating = 2 THEN 'S1'
        WHEN cs.rating = 3 THEN 'S2'
        WHEN cs.rating = 4 THEN 'S3'
        WHEN cs.rating >= 5 THEN 'C1+'
        ELSE 'Unknown'
    END as rank_group,
    COUNT(DISTINCT cs.name) as unique_controllers
FROM controller_summaries cs
WHERE cs.session_start_time >= NOW() - INTERVAL '1 week'  -- Last week's data
    AND cs.total_aircraft_handled > 0  -- Only controllers who handled aircraft
GROUP BY 
    CASE 
        WHEN cs.rating = 1 THEN 'Rank 1'
        WHEN cs.rating = 2 THEN 'S1'
        WHEN cs.rating = 3 THEN 'S2'
        WHEN cs.rating = 4 THEN 'S3'
        WHEN cs.rating >= 5 THEN 'C1+'
        ELSE 'Unknown'
    END
ORDER BY rank_group;
