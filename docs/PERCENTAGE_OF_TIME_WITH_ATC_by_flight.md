# Percentage of Time with ATC

## Query: Flight Records During ATC Communication Analysis

This query calculates what percentage of a flight's position/status records occurred during periods when the aircraft was communicating with air traffic controllers.

### SQL Query

```sql
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
    fr.total_records,
    COALESCE(fa.records_with_atc, 0) as records_with_atc,
    ROUND((COALESCE(fa.records_with_atc, 0)::numeric / fr.total_records::numeric * 100), 2) as percentage_with_atc
FROM flight_records_total fr
LEFT JOIN flight_records_with_atc fa ON fr.callsign = fa.callsign
WHERE fr.callsign = 'JST888';
```

### Results for JST888

- **Total flight records**: 724 records
- **Records with ATC communication**: 6 records
- **Percentage with ATC**: 0.83%

### Overall Results for All Flights

- **Total flights analyzed**: 147 flights
- **Total flight records**: 41,618 records
- **Total records with ATC communication**: 1,107 records
- **Overall percentage with ATC**: 2.66%

### English Explanation

**"Only 6 out of 724 flight records occurred during ATC communication"**

This means that **JST888 spent only 0.83% of its recorded flight time communicating with air traffic controllers.**

**Extrapolated to all flights: "Only 1,107 out of 41,618 flight records occurred during ATC communication"**

This means that **across all flights, aircraft spent only 2.66% of their recorded flight time communicating with air traffic controllers.**

### What This Tells Us

1. **Flight records** represent position/status updates throughout the aircraft's journey
2. **ATC communication periods** are when the aircraft was on the same frequency as an ATC controller
3. **Time window** - Flight records within 3 minutes of a frequency match are considered "during ATC communication"
4. **Very limited ATC contact** - JST888 had minimal ATC communication during its flights

### Query Logic

1. **Find frequency matches** between aircraft and ATC controllers (same frequency, within 3 minutes, within 300nm)
2. **Identify flight records** that occurred during these frequency match periods
3. **Calculate percentage** of total flight records that occurred during ATC communication
4. **Result**: Shows what portion of the flight was spent communicating with ATC

### Real-World Interpretation

- **0.83%** means JST888 was in contact with ATC for less than 1% of its flight time
- **99.17%** of the flight was spent without ATC communication
- This is typical for domestic flights that may fly through uncontrolled airspace or areas with limited ATC coverage

### Query Criteria

- **Same frequency**: Aircraft and ATC must be on the same radio frequency
- **Time window**: Within 3 minutes of each other
- **Distance**: Within 300 nautical miles of each other
- **Exclusions**: Observer (OBS) controllers are excluded
- **Flight records**: Position/status updates from the flights table
