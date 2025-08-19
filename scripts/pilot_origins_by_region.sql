-- Pilot Origins Analysis by Region
-- 
-- This script analyzes pilot origins using the 4th last character of pilot names
-- and maps them to geographic regions for both current online pilots and completed flights.
-- Excludes pilots from regions not covered by specific letter mappings.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/pilot_origins_by_region.sql
--

-- Query 1: Identify pilot origins by region for pilots currently online (top 6)
SELECT 
    CASE 
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) IN ('L', 'E') THEN 'Europe'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) IN ('V', 'W') THEN 'S & SE Asia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'R' THEN 'East Asia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'Y' THEN 'Australia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'K' THEN 'United States'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'Z' THEN 'China'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'N' THEN 'NZ & Oceania'
    END as region_name,
    COUNT(DISTINCT cid) as unique_pilots
FROM flights
WHERE name IS NOT NULL 
    AND LENGTH(name) >= 4
    AND last_updated >= NOW() - INTERVAL '1 month'  -- pilots active in last month
    AND SUBSTRING(name, LENGTH(name) - 3, 1) IN ('L', 'E', 'V', 'W', 'R', 'Y', 'K', 'Z', 'N')  -- Only include mapped regions
GROUP BY 
    CASE 
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) IN ('L', 'E') THEN 'Europe'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) IN ('V', 'W') THEN 'S & SE Asia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'R' THEN 'East Asia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'Y' THEN 'Australia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'K' THEN 'United States'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'Z' THEN 'China'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'N' THEN 'NZ & Oceania'
    END
ORDER BY unique_pilots DESC
LIMIT 6;

-- Query 2: Identify pilot origins by region and count completed flights (top 10)
SELECT 
    CASE 
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) IN ('L', 'E') THEN 'Europe'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) IN ('V', 'W') THEN 'S & SE Asia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'R' THEN 'East Asia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'Y' THEN 'Australia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'K' THEN 'United States'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'Z' THEN 'China'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'N' THEN 'NZ & Oceania'
    END as region_name,
    COUNT(DISTINCT cid) as unique_pilots
FROM flight_summaries
WHERE name IS NOT NULL 
    AND LENGTH(name) >= 4
    AND completion_time >= NOW() - INTERVAL '1 month'
    AND SUBSTRING(name, LENGTH(name) - 3, 1) IN ('L', 'E', 'V', 'W', 'R', 'Y', 'K', 'Z', 'N')  -- Only include mapped regions
GROUP BY 
    CASE 
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) IN ('L', 'E') THEN 'Europe'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) IN ('V', 'W') THEN 'S & SE Asia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'R' THEN 'East Asia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'Y' THEN 'Australia'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'K' THEN 'United States'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'Z' THEN 'China'
        WHEN SUBSTRING(name, LENGTH(name) - 3, 1) = 'N' THEN 'NZ & Oceania'
    END
ORDER BY unique_pilots DESC
LIMIT 10;
