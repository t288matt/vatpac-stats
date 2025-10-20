# ATC Detection Service Database Index Optimization

## Problem Description

The ATC detection service was experiencing timeouts during flight processing, specifically with the error:
```
Database session rolled back due to exception:
ATC detection timed out after 30.0 seconds for flight VHHAL
```

This document describes the indexes added to optimize the database queries in the ATC detection service.

## Index Optimization Strategy

After analyzing the queries in the `atc_detection_service.py` module, we identified several missing indexes that were causing performance issues. The key queries that needed optimization were:

1. Frequency matching between flight and ATC transceivers
2. Querying flight altitude data from flights and flights_archive tables
3. Looking up flight completion times from flight_summaries

## Added Indexes

### 1. Transceivers Table Indexes

```sql
-- Index for entity_type + callsign + timestamp lookups
CREATE INDEX IF NOT EXISTS idx_transceivers_entity_type_callsign_timestamp 
ON transceivers (entity_type, callsign, timestamp);

-- Index for flight-specific transceiver lookups
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign_timestamp_entity_flight 
ON transceivers (callsign, timestamp)
WHERE entity_type = 'flight';

-- Index for ATC-specific transceiver lookups
CREATE INDEX IF NOT EXISTS idx_transceivers_callsign_timestamp_entity_atc 
ON transceivers (callsign, timestamp)
WHERE entity_type = 'atc';

-- Index to optimize frequency matching with position data
CREATE INDEX IF NOT EXISTS idx_transceivers_frequency_pos_timestamp 
ON transceivers (frequency, position_lat, position_lon, timestamp);
```

These indexes significantly optimize the JOINs and WHERE clauses in the frequency matching queries used by `_find_matches_for_controller()` and `_find_frequency_matches()`.

### 2. Flight Summaries Table Indexes

```sql
-- Index for looking up flight completion times
CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign_dep_arr_logon 
ON flight_summaries (callsign, departure, arrival, logon_time);

-- Index for completion time queries
CREATE INDEX IF NOT EXISTS idx_flight_summaries_callsign_completion
ON flight_summaries (callsign, completion_time);
```

These indexes improve the performance of `_get_flight_completion_time()` which is used multiple times during ATC detection.

### 3. Flights and Flights Archive Table Indexes

```sql
-- Index for flight records with altitude data
CREATE INDEX IF NOT EXISTS idx_flights_callsign_altitude_last_updated 
ON flights (callsign, last_updated) 
WHERE altitude IS NOT NULL;

-- Same index for archive table
CREATE INDEX IF NOT EXISTS idx_flights_archive_callsign_altitude_last_updated 
ON flights_archive (callsign, last_updated) 
WHERE altitude IS NOT NULL;

-- Index for airborne detection (altitude > 1500)
CREATE INDEX IF NOT EXISTS idx_flights_callsign_altitude_gt1500 
ON flights (callsign, last_updated) 
WHERE altitude > 1500;

-- Same index for archive table
CREATE INDEX IF NOT EXISTS idx_flights_archive_callsign_altitude_gt1500 
ON flights_archive (callsign, last_updated) 
WHERE altitude > 1500;
```

These indexes optimize the queries in `_get_flight_record_count()`, `_get_airborne_time_from_flights()`, and `_count_airborne_controller_contacts()`.

### 4. Controllers Table Index

```sql
-- Index for controller lookup by facility status
CREATE INDEX IF NOT EXISTS idx_controllers_callsign_facility_last_updated 
ON controllers (callsign, facility, last_updated);
```

This index improves the performance of controller lookups in the ATC pre-filtering query.

## Expected Impact

These indexes are expected to have the following impact:

1. Eliminate or significantly reduce timeouts in the ATC detection service
2. Improve the overall performance of flight enrichment
3. Reduce database load during peak processing periods

## Monitoring and Next Steps

After implementing these indexes, the following should be monitored:

1. ATC detection timeouts in the logs
2. Query execution times for the optimized queries
3. Overall system performance during peak loads

If any issues persist, additional query optimization strategies may be needed.

