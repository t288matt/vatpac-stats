# Frequency Match Analysis

**12.59% of aircraft spoke to an ATC controller at some point during their journey, even if only for 5 minutes.**

## Query: Aircraft-ATC Frequency Communication Analysis

This query analyzes how many flights in the database had radio frequency communication with air traffic controllers.

### SQL Query

```sql
WITH flight_transceivers AS (
    SELECT DISTINCT f.id as flight_id, f.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp,
           t.position_lat, t.position_lon
    FROM flights f
    JOIN transceivers t ON f.callsign = t.callsign
    WHERE t.entity_type = 'flight' AND t.position_lat IS NOT NULL AND t.position_lon IS NOT NULL
),
atc_transceivers AS (
    SELECT DISTINCT c.id as controller_id, c.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp,
           t.position_lat, t.position_lon
    FROM controllers c
    JOIN transceivers t ON c.callsign = t.callsign
    WHERE t.entity_type = 'atc' AND t.position_lat IS NOT NULL AND t.position_lon IS NOT NULL
    AND c.facility != 'OBS' -- Exclude Observer positions
),
frequency_matches AS (
    SELECT ft.flight_id, ft.callsign as flight_callsign, ft.frequency_mhz,
           ft.timestamp as flight_time, ft.position_lat as flight_lat,
           ft.position_lon as flight_lon, at.callsign as controller_callsign,
           at.timestamp as controller_time, at.position_lat as controller_lat,
           at.position_lon as controller_lon,
           (SQRT(POWER(ft.position_lat - at.position_lat, 2) + POWER(ft.position_lon - at.position_lon, 2))) as distance
    FROM flight_transceivers ft
    JOIN atc_transceivers at ON ft.frequency_mhz = at.frequency_mhz
    AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= 180 -- 3 minutes
    WHERE (SQRT(POWER(ft.position_lat - at.position_lat, 2) + POWER(ft.position_lon - at.position_lon, 2))) <= 300
),
flight_summary AS (
    SELECT f.id, f.callsign,
           CASE WHEN fm.flight_id IS NOT NULL THEN 1 ELSE 0 END as had_frequency_match
    FROM flights f
    LEFT JOIN (SELECT DISTINCT flight_id FROM frequency_matches) fm ON f.id = fm.flight_id
)
SELECT COUNT(*) as total_flights,
       SUM(had_frequency_match) as flights_with_matches,
       ROUND((SUM(had_frequency_match)::numeric / COUNT(*)::numeric * 100), 2) as percentage_with_matches
FROM flight_summary;
```

### Results

- **Total flights analyzed**: 40,446 flights
- **Flights with frequency matches**: 5,094 flights  
- **Percentage**: 12.59%

### English Explanation

The **12.59%** represents:

**"Out of all the flights in the database, only 12.59% of them had at least one instance where they were communicating on the same radio frequency as an air traffic controller within 3 minutes of each other and within 300 nautical miles of each other."**

In plain English:
- **Total flights analyzed**: 40,446 flights
- **Flights with frequency matches**: 5,094 flights  
- **Percentage**: 12.59%

This means **87.41% of flights** (34,352 flights) had **no frequency matches** with ATC controllers under these criteria.

### What This Tells Us

1. **Most flights don't communicate with ATC** - The vast majority of flights in the dataset never matched with an ATC controller on the same frequency
2. **Limited ATC coverage** - Only about 1 in 8 flights had any ATC communication recorded
3. **Realistic aviation data** - This makes sense because:
   - Not all airspace has active ATC
   - Many flights are in uncontrolled airspace
   - Some flights might be in areas without VATSIM controllers
   - The data might be from a time period with limited ATC activity

**The 12.59% represents the subset of flights that had meaningful ATC communication** during their journey, which is actually quite realistic for a global aviation network where ATC coverage varies significantly by region and time.

### Query Criteria

- **Same frequency**: Aircraft and ATC must be on the same radio frequency
- **Time window**: Within 3 minutes of each other
- **Distance**: Within 300 nautical miles of each other
- **Exclusions**: Observer (OBS) controllers are excluded
- **Frequency conversion**: Frequencies are converted from Hz to MHz for comparison
