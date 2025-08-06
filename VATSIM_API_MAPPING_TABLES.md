# VATSIM API Field Mapping Documentation

This document outlines the complete field mapping between VATSIM API data and our database schema.

## 1. CONTROLLER (ATC Positions)

| **VATSIM API Field** | **Database Field** | **Type** | **Description** | **Status** |
|----------------------|-------------------|----------|-----------------|------------|
| `"cid"` | `controller_id` | INTEGER | Controller ID from VATSIM | ✅ **MAPPED** |
| `"name"` | `controller_name` | VARCHAR(100) | Controller name from VATSIM | ✅ **MAPPED** |
| `"rating"` | `controller_rating` | INTEGER | Controller rating from VATSIM | ✅ **MAPPED** |
| `"callsign"` | `callsign` | VARCHAR(50) | ATC callsign | ✅ **MAPPED** |
| `"facility"` | `facility` | VARCHAR(50) | Facility type | ✅ **MAPPED** |
| `"frequency"` | `frequency` | VARCHAR(20) | Radio frequency | ✅ **MAPPED** |
| `"position"` | `position` | VARCHAR(50) | Position description | ✅ **MAPPED** |
| `"status"` | `status` | VARCHAR(20) | Online/offline status | ✅ **MAPPED** |
| `"last_seen"` | `last_seen` | TIMESTAMP | Last activity time | ✅ **MAPPED** |
| `"workload_score"` | `workload_score` | DOUBLE PRECISION | Workload metric | ✅ **MAPPED** |
| `"preferences"` | `preferences` | TEXT | JSON preferences | ✅ **MAPPED** |

## 2. FLIGHT

| **VATSIM API Field** | **Database Field** | **Type** | **Description** | **Status** |
|----------------------|-------------------|----------|-----------------|------------|
| `"cid"` | `controller_id` | INTEGER | Foreign key to controllers | ✅ **MAPPED** |
| `"callsign"` | `callsign` | VARCHAR(50) | Aircraft callsign | ✅ **MAPPED** |
| `"aircraft_type"` | `aircraft_type` | VARCHAR(20) | Aircraft type | ✅ **MAPPED** |
| `"position.lat"` | `position_lat` | DOUBLE PRECISION | Latitude | ✅ **MAPPED** |
| `"position.lng"` | `position_lng` | DOUBLE PRECISION | Longitude | ✅ **MAPPED** |
| `"altitude"` | `altitude` | INTEGER | Flight level | ✅ **MAPPED** |
| `"speed"` | `speed` | INTEGER | Airspeed | ✅ **MAPPED** |
| `"heading"` | `heading` | INTEGER | Aircraft heading | ✅ **MAPPED** |
| `"ground_speed"` | `ground_speed` | INTEGER | Ground speed | ✅ **MAPPED** |
| `"vertical_speed"` | `vertical_speed` | INTEGER | Vertical speed | ✅ **MAPPED** |
| `"squawk"` | `squawk` | VARCHAR(10) | Transponder code | ✅ **MAPPED** |
| `"departure"` | `departure` | VARCHAR(10) | Departure airport | ✅ **MAPPED** |
| `"arrival"` | `arrival` | VARCHAR(10) | Arrival airport | ✅ **MAPPED** |
| `"route"` | `route` | TEXT | Flight route | ✅ **MAPPED** |

## 3. TRANSCEIVER

| **VATSIM API Field** | **Database Field** | **Type** | **Description** | **Status** |
|----------------------|-------------------|----------|-----------------|------------|
| `"callsign"` | `callsign` | VARCHAR(50) | Entity callsign | ✅ **MAPPED** |
| `"transceiver_id"` | `transceiver_id` | INTEGER | Transceiver ID | ✅ **MAPPED** |
| `"frequency"` | `frequency` | INTEGER | Frequency in Hz | ✅ **MAPPED** |
| `"position_lat"` | `position_lat` | DOUBLE PRECISION | Latitude | ✅ **MAPPED** |
| `"position_lon"` | `position_lon` | DOUBLE PRECISION | Longitude | ✅ **MAPPED** |
| `"height_msl"` | `height_msl` | DOUBLE PRECISION | Height above sea level | ✅ **MAPPED** |
| `"height_agl"` | `height_agl` | DOUBLE PRECISION | Height above ground | ✅ **MAPPED** |
| `"entity_type"` | `entity_type` | VARCHAR(20) | Flight or ATC | ✅ **MAPPED** |
| `"entity_id"` | `entity_id` | INTEGER | Foreign key reference | ✅ **MAPPED** |

## Database Schema Updates

### Added Fields to Controllers Table:
```sql
-- VATSIM API fields
controller_id INTEGER,  -- From API "cid"
controller_name VARCHAR(100),  -- From API "name"
controller_rating INTEGER,  -- From API "rating"
```

### Added Index:
```sql
CREATE INDEX IF NOT EXISTS idx_controllers_controller_id ON controllers(controller_id);
```

## Migration Status

- ✅ **Model Updated**: Controller model includes new fields
- ✅ **Database Migration**: Fields added to existing database
- ✅ **Init Script Updated**: Greenfield deployments include new fields
- ✅ **Data Service Updated**: Correct field mapping implemented
- ✅ **Documentation Updated**: README reflects new capabilities

## Usage Examples

### Controller Data Processing:
```python
# API data mapping
controller_data = {
    'callsign': atc_position_data.get('callsign', ''),
    'facility': atc_position_data.get('facility', ''),
    'controller_id': atc_position_data.get('cid', None),  # API "cid" → DB "controller_id"
    'controller_name': atc_position_data.get('name', ''),  # API "name" → DB "controller_name"
    'controller_rating': atc_position_data.get('rating', 0),  # API "rating" → DB "controller_rating"
    'frequency': atc_position_data.get('frequency', ''),
    'status': 'online',
    'last_seen': datetime.utcnow()
}
```

### Flight Data Processing:
```python
# Flight data mapping
flight_data = {
    'callsign': flight_data.get('callsign', ''),
    'controller_id': flight_data.get('cid', None),  # API "cid" → DB "controller_id"
    'aircraft_type': flight_data.get('aircraft_type', ''),
    'position_lat': position_data.get('lat', 0.0),
    'position_lng': position_data.get('lng', 0.0),
    'altitude': flight_data.get('altitude', 0),
    'speed': flight_data.get('speed', 0),
    'departure': flight_data.get('departure', ''),
    'arrival': flight_data.get('arrival', ''),
    'route': flight_data.get('route', '')
}
```

## Notes

- All VATSIM API fields are now properly mapped to database fields
- Greenfield deployments automatically include the new fields
- Existing deployments have been migrated with the new fields
- The field mapping is consistent across all data types
- Performance indexes are in place for efficient queries 