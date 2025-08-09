# VATSIM API Database Mapping Tables

## 1. FLIGHT

| VATSIM API Field | Current Code Field | Database Field | Status | Proposed Mapping |
|------------------|-------------------|----------------|---------|------------------|
| "cid" | pilot_id | pilot_id | ❌ Missing | Direct mapping (foreign key) |
| "name" | pilot_name | pilot_name | ✅ Captured | Stored in VATSIMFlight.pilot_name |
| "callsign" | callsign | callsign | ✅ OK | Direct mapping |
| "server" | server | server | ❌ Missing | Direct mapping |
| "pilot_rating" | pilot_rating | pilot_rating | ❌ Missing | Direct mapping |
| "military_rating" | military_rating | military_rating | ❌ Missing | Direct mapping |
| "latitude" | position_lat | position_lat | ✅ OK | Stored as position.lat |
| "longitude" | position_lng | position_lng | ✅ OK | Stored as position.lng |
| "altitude" | altitude | altitude | ✅ OK | Direct mapping |
| "groundspeed" | ground_speed | ground_speed | ✅ OK | Stored as speed |
| "transponder" | squawk | squawk | ❌ Missing | Direct mapping |
| "heading" | heading | heading | ❌ Missing | Direct mapping |
| "qnh_i_hg" | qnh_inhg | qnh_inhg | ❌ Missing | Direct mapping |
| "qnh_mb" | qnh_mb | qnh_mb | ❌ Missing | Direct mapping |
| "logon_time" | logon_time | logon_time | ❌ Missing | Direct mapping |
| "last_updated" | last_updated | last_updated | ✅ OK | Direct mapping |

### Flight Plan Fields (Nested Object)
| VATSIM API Field | Current Code Field | Database Field | Status | Proposed Mapping |
|------------------|-------------------|----------------|---------|------------------|
| "flight_plan.flight_rules" | flight_rules | flight_rules | ❌ Missing | Direct mapping |
| "flight_plan.aircraft" | aircraft_type | aircraft_type | ✅ OK | Stored as aircraft_short |
| "flight_plan.aircraft_faa" | aircraft_faa | aircraft_faa | ❌ Missing | Direct mapping |
| "flight_plan.aircraft_short" | aircraft_short | aircraft_short | ✅ OK | Direct mapping |
| "flight_plan.departure" | departure | departure | ✅ OK | Direct mapping |
| "flight_plan.arrival" | arrival | arrival | ✅ OK | Direct mapping |
| "flight_plan.alternate" | alternate | alternate | ❌ Missing | Direct mapping |
| "flight_plan.cruise_tas" | cruise_tas | cruise_tas | ❌ Missing | Direct mapping |
| "flight_plan.altitude" | planned_altitude | planned_altitude | ❌ Missing | Direct mapping |
| "flight_plan.deptime" | deptime | deptime | ❌ Missing | Direct mapping |
| "flight_plan.enroute_time" | enroute_time | enroute_time | ❌ Missing | Direct mapping |
| "flight_plan.fuel_time" | fuel_time | fuel_time | ❌ Missing | Direct mapping |
| "flight_plan.remarks" | remarks | remarks | ❌ Missing | Direct mapping |
| "flight_plan.route" | route | route | ✅ OK | Direct mapping |
| "flight_plan.revision_id" | revision_id | revision_id | ❌ Missing | Direct mapping |
| "flight_plan.assigned_transponder" | assigned_transponder | assigned_transponder | ❌ Missing | Direct mapping |

## 2. CONTROLLER

| VATSIM API Field | Current Code Field | Database Field | Status | Proposed Mapping |
|------------------|-------------------|----------------|---------|------------------|
| "cid" | controller_id | controller_id | ✅ OK | Direct mapping (foreign key) |
| "name" | controller_name | controller_name | ✅ OK | Direct mapping |
| "callsign" | callsign | callsign | ✅ OK | Direct mapping |
| "facility" | facility | facility | ✅ OK | Direct mapping |
| "frequency" | frequency | frequency | ✅ OK | Direct mapping |
| "rating" | controller_rating | controller_rating | ✅ OK | Direct mapping |
| "visual_range" | visual_range | visual_range | ❌ Missing | Direct mapping |
| "text_atis" | text_atis | text_atis | ❌ Missing | Direct mapping |
| "last_updated" | last_updated | last_updated | ✅ OK | Direct mapping |

## 3. TRANSCEIVER

| VATSIM API Field | Current Code Field | Database Field | Status | Proposed Mapping |
|------------------|-------------------|----------------|---------|------------------|
| "callsign" | callsign | callsign | ✅ OK | Direct mapping |
| "transceiver_id" | transceiver_id | transceiver_id | ✅ OK | Direct mapping |
| "frequency" | frequency | frequency | ✅ OK | Direct mapping |
| "latitude" | position_lat | position_lat | ✅ OK | Direct mapping |
| "longitude" | position_lon | position_lon | ✅ OK | Direct mapping |
| "height_msl" | height_msl | height_msl | ✅ OK | Direct mapping |
| "height_agl" | height_agl | height_agl | ✅ OK | Direct mapping |
| "entity_type" | entity_type | entity_type | ✅ OK | Direct mapping |
| "entity_id" | entity_id | entity_id | ✅ OK | Direct mapping |
| "timestamp" | timestamp | timestamp | ✅ OK | Direct mapping |

## 4. GENERAL/STATUS

| VATSIM API Field | Current Code Field | Database Field | Status | Proposed Mapping |
|------------------|-------------------|----------------|---------|------------------|
| "version" | api_version | api_version | ❌ Missing | Direct mapping |
| "reload" | reload | reload | ❌ Missing | Direct mapping |
| "update" | update_timestamp | update_timestamp | ❌ Missing | Direct mapping |
| "update_timestamp" | update_timestamp | update_timestamp | ❌ Missing | Direct mapping |
| "connected_clients" | connected_clients | connected_clients | ❌ Missing | Direct mapping |
| "unique_users" | unique_users | unique_users | ❌ Missing | Direct mapping |

## 5. SECTORS

**Note**: Sectors data is not available in the current VATSIM API v3, and the sectors table has been removed from the database during cleanup.

| VATSIM API Field | Current Code Field | Database Field | Status | Proposed Mapping |
|------------------|-------------------|----------------|---------|------------------|
| "sectors" | N/A | N/A | ❌ Not Available | API v3 limitation + table removed |

## Summary

### ✅ Currently Working Fields:
- **Flight**: callsign, pilot_name, aircraft_type, departure, arrival, route, altitude, speed, position_lat/lng
- **Controller**: controller_id, controller_name, callsign, facility, frequency, controller_rating
- **Transceiver**: All fields are captured

### ❌ Missing High-Priority Fields:
- **Flight**: pilot_id, server, pilot_rating, military_rating, transponder, heading, qnh_inhg, qnh_mb, logon_time
- **Flight Plan**: flight_rules, aircraft_faa, alternate, cruise_tas, planned_altitude, deptime, enroute_time, fuel_time, remarks, revision_id, assigned_transponder
- **Controller**: visual_range, text_atis
- **General/Status**: All fields are missing 