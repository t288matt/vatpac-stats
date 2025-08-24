# 🔄 VATSIM API Field Mapping Reference

## 📋 Overview

This document provides a comprehensive mapping of fields from the VATSIM API v3 through the database to the final API responses.

**Data Flow**: VATSIM API v3 → Database Storage → API Response

## 🎯 VATSIM API v3 Source Fields

### **Controllers Data Structure**
```json
{
  "callsign": "YSSY_APP",
  "frequency": "124.700",
  "cid": 789012,
  "name": "Jane Controller",
  "rating": 5,
  "facility": 2,
  "visual_range": 50,
  "text_atis": "Sydney Approach, contact 124.700",
  "server": "AUSTRALIA",
  "last_updated": "2025-08-09T09:15:30Z",
  "logon_time": "2025-08-09T06:30:00Z"
}
```

### **Flights Data Structure**
```json
{
  "callsign": "QFA005",
  "cid": 123456,
  "name": "John Pilot",
  "server": "AUSTRALIA",
  "pilot_rating": 1,
  "military_rating": 0,
  "latitude": -33.9461,
  "longitude": 151.1772,
  "altitude": 37000,
  "groundspeed": 485,
  "heading": 90,
  "transponder": "2000",
  "logon_time": "2025-08-09T08:30:00Z",
  "last_updated": "2025-08-09T09:15:30Z",
  "flight_plan": {
    "flight_rules": "I",
    "aircraft_faa": "B789",
    "departure": "VTBS",
    "arrival": "YBBN",
    "alternate": "YSSY",
    "cruise_tas": "485",
    "altitude": "FL370",
    "deptime": "0830",
    "enroute_time": "1045",
    "fuel_time": "1145",
    "route": "VTBS DCT YBBN",
    "remarks": "PBN/A1B1C1D1L1O1S1"
  }
}
```

### **Transceivers Data Structure**
```json
{
  "callsign": "QFA005",
  "transceivers": [
    {
      "id": 12345,
      "frequency": 120500000,
      "latDeg": -33.9461,
      "lonDeg": 151.1772,
      "heightMslM": 11278.0,
      "heightAglM": 11278.0
    }
  ]
}
```

## 🗄️ Database Field Mapping

### **Controllers Table**

| VATSIM API Field | Database Column | Type | Constraints |
|------------------|-----------------|------|-------------|
| `callsign` | `callsign` | VARCHAR(50) | UNIQUE, NOT NULL |
| `frequency` | `frequency` | VARCHAR(20) | NULL |
| `cid` | `cid` | INTEGER | NULL |
| `name` | `name` | VARCHAR(100) | NULL |
| `rating` | `rating` | INTEGER | -1 to 12 |
| `facility` | `facility` | INTEGER | 0 to 6 |
| `visual_range` | `visual_range` | INTEGER | ≥ 0 |
| `text_atis` | `text_atis` | TEXT | NULL |
| `server` | `server` | VARCHAR(50) | NULL |
| `last_updated` | `last_updated` | TIMESTAMP | NULL |
| `logon_time` | `logon_time` | TIMESTAMP | NULL |

### **Flights Table**

| VATSIM API Field | Database Column | Type | Constraints |
|------------------|-----------------|------|-------------|
| `callsign` | `callsign` | VARCHAR(50) | NOT NULL |
| `cid` | `cid` | INTEGER | NULL |
| `name` | `name` | VARCHAR(100) | NULL |
| `server` | `server` | VARCHAR(50) | NULL |
| `pilot_rating` | `pilot_rating` | INTEGER | 0 to 63 |
| `military_rating` | `military_rating` | INTEGER | NULL |
| `latitude` | `latitude` | FLOAT | -90 to 90 |
| `longitude` | `longitude` | FLOAT | -180 to 180 |
| `altitude` | `altitude` | INTEGER | ≥ 0 |
| `groundspeed` | `groundspeed` | INTEGER | ≥ 0 |
| `heading` | `heading` | INTEGER | 0 to 360 |
| `transponder` | `transponder` | VARCHAR(10) | NULL |
| `logon_time` | `logon_time` | TIMESTAMP | NULL |
| `last_updated` | `last_updated_api` | TIMESTAMP | NULL |

**Flight Plan Fields (Nested Object):**
| VATSIM API Field | Database Column | Type | Constraints |
|------------------|-----------------|------|-------------|
| `flight_plan.aircraft_faa` | `aircraft_type` | VARCHAR(20) | NULL |
| `flight_plan.departure` | `departure` | VARCHAR(10) | NULL |
| `flight_plan.arrival` | `arrival` | VARCHAR(10) | NULL |
| `flight_plan.route` | `route` | TEXT | NULL |
| `flight_plan.flight_rules` | `flight_rules` | VARCHAR(10) | NULL |
| `flight_plan.alternate` | `alternate` | VARCHAR(10) | NULL |
| `flight_plan.cruise_tas` | `cruise_tas` | VARCHAR(10) | NULL |
| `flight_plan.altitude` | `planned_altitude` | VARCHAR(10) | NULL |
| `flight_plan.deptime` | `deptime` | VARCHAR(10) | NULL |
| `flight_plan.enroute_time` | `enroute_time` | VARCHAR(10) | NULL |
| `flight_plan.fuel_time` | `fuel_time` | VARCHAR(10) | NULL |
| `flight_plan.remarks` | `remarks` | TEXT | NULL |

### **Transceivers Table**

| VATSIM API Field | Database Column | Type | Constraints |
|------------------|-----------------|------|-------------|
| `callsign` | `callsign` | VARCHAR(50) | NOT NULL |
| `transceivers[].id` | `transceiver_id` | INTEGER | NOT NULL |
| `transceivers[].frequency` | `frequency` | BIGINT | > 0 |
| `transceivers[].latDeg` | `position_lat` | FLOAT | -90 to 90 |
| `transceivers[].lonDeg` | `position_lon` | FLOAT | -180 to 180 |
| `transceivers[].heightMslM` | `height_msl` | FLOAT | NULL |
| `transceivers[].heightAglM` | `height_agl` | FLOAT | NULL |

## 🔄 API Response Field Mapping

### **GET /api/controllers Response**

| Database Column | API Response Field | Type | Notes |
|-----------------|-------------------|------|-------|
| `callsign` | `callsign` | string | Controller callsign |
| `frequency` | `frequency` | string | Radio frequency |
| `cid` | `cid` | integer | Controller ID |
| `name` | `name` | string | Controller name |
| `rating` | `controller_rating` | integer | Controller rating |
| `facility` | `facility` | string | Facility type (converted from integer) |
| `visual_range` | `visual_range` | integer | Visual range in NM |
| `text_atis` | `text_atis` | string | ATIS information |
| `server` | `server` | string | Network server |
| `logon_time` | `logon_time` | string | ISO timestamp |
| `last_updated` | `last_updated` | string | ISO timestamp |

### **GET /api/flights Response**

| Database Column | API Response Field | Type | Notes |
|-----------------|-------------------|------|-------|
| `callsign` | `callsign` | string | Flight callsign |
| `cid` | `cid` | integer | VATSIM user ID |
| `name` | `name` | string | Pilot name |
| `server` | `server` | string | Network server |
| `pilot_rating` | `pilot_rating` | integer | Pilot rating |
| `latitude` | `latitude` | number | Position latitude |
| `longitude` | `longitude` | number | Position longitude |
| `altitude` | `altitude` | integer | Current altitude |
| `groundspeed` | `groundspeed` | integer | Ground speed |
| `heading` | `heading` | integer | Current heading |
| `transponder` | `transponder` | string | Transponder code |
| `departure` | `departure` | string | Departure airport |
| `arrival` | `arrival` | string | Arrival airport |
| `aircraft_type` | `aircraft_type` | string | Aircraft type |
| `flight_rules` | `flight_rules` | string | IFR/VFR |
| `planned_altitude` | `planned_altitude` | string | Planned cruise altitude |
| `last_updated` | `last_updated` | string | ISO timestamp |

### **GET /api/transceivers Response**

| Database Column | API Response Field | Type | Notes |
|-----------------|-------------------|------|-------|
| `id` | `id` | integer | Transceiver ID |
| `callsign` | `callsign` | string | Entity callsign |
| `frequency` | `frequency` | number | Frequency in Hz |
| `position_lat` | `position_lat` | number | Position latitude |
| `position_lon` | `position_lng` | number | Position longitude |
| `height_msl` | `altitude` | number | Height MSL in meters |
| `timestamp` | `last_updated` | string | ISO timestamp |

### **Flight Summary Fields (flight_summaries table)**

| Database Column | API Response Field | Type | Notes |
|-----------------|-------------------|------|-------|
| `id` | `id` | integer | Unique identifier |
| `callsign` | `callsign` | string | Flight callsign |
| `aircraft_type` | `aircraft_type` | string | Aircraft type |
| `departure` | `departure` | string | Departure airport |
| `arrival` | `arrival` | string | Arrival airport |
| `deptime` | `deptime` | string | Departure time |
| `route` | `route` | text | Flight plan route |
| `flight_rules` | `flight_rules` | string | IFR/VFR |
| `planned_altitude` | `planned_altitude` | string | Planned cruise altitude |
| `controller_callsigns` | `controller_callsigns` | jsonb | JSON array of ATC callsigns |
| `controller_time_percentage` | `controller_time_percentage` | number | Percentage of total time on ATC |
| `airborne_controller_time_percentage` | `airborne_controller_time_percentage` | number | Percentage of airborne time on ATC (>1500ft) |
| `time_online_minutes` | `time_online_minutes` | integer | Total time online in minutes |
| `primary_enroute_sector` | `primary_enroute_sector` | string | Primary sector flown through |

## 🔧 Field Transformations & Processing

### **Data Type Conversions**

| VATSIM API Type | Database Type | API Response Type | Notes |
|-----------------|---------------|-------------------|-------|
| `string` | `VARCHAR/TEXT` | `string` | Direct mapping |
| `number` | `INTEGER/FLOAT` | `number` | Direct mapping |
| `ISO timestamp` | `TIMESTAMP` | `string` | Converted to ISO format |
| `null` | `NULL` | `null` | Preserved |

### **Special Processing**

1. **Flight Plan Nesting**: VATSIM API nests flight plan data, but database flattens it
2. **Timestamp Conversion**: ISO timestamps converted to PostgreSQL timestamps, then back to ISO for API responses
3. **Facility Mapping**: Integer facility codes converted to readable strings in API responses
4. **Coordinate Validation**: Latitude/longitude validated against geographic constraints
5. **Rating Validation**: Controller and pilot ratings validated against VATSIM ranges

## 🚫 Removed Fields

The following fields were removed from the Flight model to match the current database schema:

- `aircraft_short` - Short aircraft code from flight plan
- `revision_id` - Flight plan revision ID  
- `assigned_transponder` - Assigned transponder code
- `qnh_i_hg` - QNH pressure in inches Hg
- `qnh_mb` - QNH pressure in millibars

These fields are no longer stored or processed by the system.

---

**📅 Last Updated**: 2025-01-27  
**🔄 Data Flow**: VATSIM API v3 → Database → API Response  
**📚 Total Fields Mapped**: 43+  
**🚀 Production Ready**: Yes  
**🗺️ Geographic Filtering**: Enabled for flights, transceivers, and controllers
