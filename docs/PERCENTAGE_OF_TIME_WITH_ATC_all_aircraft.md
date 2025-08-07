# Percentage of Time with ATC - All Aircraft Analysis

## Query: Flight Records During ATC Communication Analysis (All Aircraft)

This query calculates what percentage of each flight's position/status records occurred during periods when the aircraft was communicating with air traffic controllers, for ALL aircraft in the database.

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
    fr.total_records as total_flight_data_records,
    COALESCE(fa.records_with_atc, 0) as flight_data_records_in_contact_with_atc,
    ROUND((COALESCE(fa.records_with_atc, 0)::numeric / fr.total_records::numeric * 100), 2) as percentage_with_atc
FROM flight_records_total fr
LEFT JOIN flight_records_with_atc fa ON fr.callsign = fa.callsign
ORDER BY percentage_with_atc DESC, fr.total_records DESC;
```

### Query for Overall Statistics

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
    COUNT(*) as total_flights,
    SUM(fr.total_records) as total_flight_records,
    SUM(COALESCE(fa.records_with_atc, 0)) as total_records_with_atc,
    ROUND((SUM(COALESCE(fa.records_with_atc, 0))::numeric / SUM(fr.total_records)::numeric * 100), 2) as overall_percentage_with_atc
FROM flight_records_total fr
LEFT JOIN flight_records_with_atc fa ON fr.callsign = fa.callsign;
```

### Usage

Run the SQL query directly:

```bash
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/analyze_all_aircraft_atc.sql
```

### Expected Results

This query will return:
- **All aircraft** in the database with their individual ATC communication percentages
- **Sorted by percentage** (highest ATC communication first)
- **Complete dataset** showing the full spectrum of ATC communication patterns

### What This Analysis Provides

1. **Individual aircraft analysis** - Each aircraft's ATC communication percentage
2. **Pattern identification** - Which aircraft have high vs low ATC contact
3. **Complete dataset** - No filtering, shows all aircraft in the database
4. **Comparative analysis** - Can identify aircraft with unusual ATC communication patterns

### Query Logic

1. **Find frequency matches** between aircraft and ATC controllers (same frequency, within 3 minutes, within 300nm)
2. **Identify flight records** that occurred during these frequency match periods
3. **Calculate percentage** of total flight records that occurred during ATC communication
4. **Return all aircraft** - No WHERE clause filter, includes all aircraft in database

### Query Criteria

- **Same frequency**: Aircraft and ATC must be on the same radio frequency
- **Time window**: Within 3 minutes of each other
- **Distance**: Within 300 nautical miles of each other
- **Exclusions**: Observer (OBS) controllers are excluded
- **Flight records**: Position/status updates from the flights table
- **All aircraft**: No filtering by specific callsign
