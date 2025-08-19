# 🛩️ Flight Data Flow: Complete System Architecture

## 📊 **Flight Data Flow Diagram**

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    VATSIM NETWORK                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │
│  │   Flights API   │    │ Controllers API │    │ Transceivers    │    │   Sectors.xml   │   │
│  │   (Real-time)   │    │   (Real-time)   │    │   API (Real)    │    │   (Static)      │   │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    VATSIM SERVICE                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  get_current_data() - Fetches every 60 seconds                                            │ │
│  │                                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │ _parse_flights()│    │_parse_controllers│    │_parse_transceivers│                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ • 25+ fields    │    │ • 11 fields     │    │ • 8 fields      │                        │ │
│  │  │ • Position data │    │ • ATC info      │    │ • Frequency     │                        │ │
│  │  │ • Flight plan   │    │ • Rating        │    │ • Coordinates   │                        │ │
│  │  │ • Pilot data    │    │ • Facility      │    │ • Entity type   │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  │                                                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  │ _link_transceivers_to_entities()                                                        │ │
│  │  │ • Links transceivers to flights/controllers                                             │ │
│  │  │ • Sets entity_type ('flight' or 'atc')                                                 │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA SERVICE                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  process_vatsim_data() - Main orchestrator                                                │ │
│  │                                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │_process_flights()│    │_process_controllers│ │_process_transceivers│                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ 1. Geographic   │    │ 1. Callsign     │    │ 1. Geographic   │                        │ │
│  │  │    filtering    │    │    filtering    │    │    filtering    │                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ 2. Data         │    │ 2. Data         │    │ 2. Entity       │                        │ │
│  │  │    validation   │    │    validation   │    │    linking      │                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ 3. Sector       │    │ 3. No sector    │    │ 3. Position    │                        │ │
│  │  │    tracking     │    │    tracking     │    │    storage     │                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ 4. Bulk DB      │    │ 4. Bulk DB      │    │ 4. Bulk DB     │                        │ │
│  │  │    insertion    │    │    insertion    │    │    insertion   │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FILTERING LAYER                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  Geographic Boundary Filter (Australian Airspace)                                         │ │
│  │                                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │ filter_flights_ │    │filter_controllers│    │filter_transceivers│                        │ │
│  │  │ list()          │    │_list()          │    │_list()          │                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ • Polygon-based │    │ • Callsign      │    │ • Polygon-based │                        │ │
│  │  │ • <1ms overhead │    │   pattern       │    │ • <1ms overhead │                        │ │
│  │  │ • 100% accuracy │    │ • <0.1ms        │    │ • 100% accuracy │                        │ │
│  │  │ • Real-time     │    │ • 100% accuracy │    │ • Real-time     │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    SECTOR TRACKING                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  _track_sector_occupancy() - Only for flights                                             │ │
│  │                                                                                             │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │ Entry Criteria  │    │ Exit Criteria   │    │ Duration Calc   │                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ • Speed >60kts  │    │ • Speed <30kts  │    │ • Entry time    │                        │ │
│  │  │ • Within sector │    │ • 2 consecutive │    │ • Exit time     │                        │ │
│  │  │ • Valid coords  │    │   polls (60s)   │    │ • Total seconds │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  │                                                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  │ Australian Airspace Sectors (SYA, BLA, WOL, etc.)                                      │ │
│  │  │ • Real-time boundary detection                                                          │ │
│  │  │ • Automatic entry/exit tracking                                                         │ │
│  │  │ • Performance-based criteria                                                             │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATABASE LAYER                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  PostgreSQL Database (vatsim_data)                                                        │ │
│  │                                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │    flights      │    │ flight_sector_  │    │   transceivers  │                        │ │
│  │  │                 │    │ occupancy       │    │                 │                        │ │
│  │  │ • 25+ fields    │    │ • Sector entry  │    │ • Frequency     │                        │ │
│  │  │ • Position      │    │ • Sector exit   │    │ • Coordinates   │                        │ │
│  │  │ • Flight plan   │    │ • Duration      │    │ • Entity type   │                        │ │
│  │  │ • Pilot info    │    │ • Performance   │    │ • Timestamps    │                        │ │
│  │  │ • Timestamps    │    │ • Boundaries    │    │ • Heights       │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  │                                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │ flight_summaries│    │ flights_archive │    │ controllers    │                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ • Completed     │    │ • Old flight    │    │ • ATC positions │                        │ │
│  │  │   flights       │    │   data          │    │ • Ratings      │                        │ │
│  │  │ • Analytics     │    │ • Historical    │    │ • Facilities   │                        │ │
│  │  │ • Metrics       │    │   records       │    │ • Timestamps   │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    INTERACTION DETECTION                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  Flight-Controller Interaction Detection                                                  │ │
│  │                                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │FlightDetection  │    │ ATCDetection    │    │ ControllerType  │                        │ │
│  │  │Service          │    │ Service         │    │ Detector        │                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ • Controller→   │    │ • Flight→ATC    │    │ • Callsign      │                        │ │
│  │  │   Flight        │    │ • Interactions  │    │   analysis      │                        │ │
│  │  │ • Frequency     │    │ • Frequency     │    │ • Type detection│                        │ │
│  │  │   matching      │    │   matching      │    │ • Proximity     │                        │ │
│  │  │ • Proximity     │    │ • Proximity     │    │   ranges        │                        │ │
│  │  │   filtering     │    │   filtering     │    │ • Dynamic       │                        │ │
│  │  │ • Time windows  │    │ • Time windows  │    │   thresholds    │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    SUMMARY & ANALYTICS                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  Automatic Summary Generation                                                              │ │
│  │                                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │ Flight Summary  │    │ Controller      │    │ Sector Metrics  │                        │ │
│  │  │ Processing      │    │ Summary         │    │ & Analytics     │                        │ │
│  │  │                 │    │ Processing      │    │                 │                        │ │
│  │  │ • Every 60 min  │    │ • Every 30 min  │    │ • Real-time     │                        │ │
│  │  │ • Route analysis│    │ • Aircraft      │    │ • Performance   │                        │ │
│  │  │ • Sector data   │    │   counts        │    │ • Occupancy     │                        │ │
│  │  │ • ATC coverage  │    │ • Peak counts   │    │ • Duration      │                        │ │
│  │  │ • Performance   │    │ • Frequencies   │    │ • Efficiency    │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    API & MONITORING                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  FastAPI Endpoints & System Monitoring                                                     │ │
│  │                                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │   /api/flights  │    │ /api/controllers│    │ /api/status     │                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ • Real-time     │    │ • ATC positions │    │ • System health │                        │ │
│  │  │   data          │    │ • Ratings       │    │ • Performance   │                        │ │
│  │  │ • Position      │    │ • Facilities    │    │ • Data freshness│                        │ │
│  │  │ • Flight plan   │    │ • Frequencies   │    │ • Statistics    │                        │ │
│  │  │ • Analytics     │    │ • Status        │    │ • Monitoring    │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  │                                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │ │
│  │  │ /api/flights/   │    │ /api/controllers│    │ Background      │                        │ │
│  │  │ summaries       │    │ /summaries      │    │ Tasks           │                        │ │
│  │  │                 │    │                 │    │                 │                        │ │
│  │  │ • Completed     │    │ • Session       │    │ • Data ingestion│                        │ │
│  │  │   flights       │    │   summaries     │    │   (60s)         │                        │ │
│  │  │ • Route data    │    │ • Aircraft      │    │ • Cleanup       │                        │ │
│  │  │ • Performance   │    │   handled       │    │   (300s)        │                        │ │
│  │  │ • Analytics     │    │ • Metrics       │    │ • Monitoring    │                        │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 **Data Flow Summary**

### **1. Data Ingestion (Every 60 seconds)**
- **VATSIM API** → **VATSIM Service** → **Data Service**
- Flights, controllers, and transceivers fetched simultaneously
- Real-time position and status data

### **2. Processing Pipeline**
- **Geographic Filtering**: Australian airspace boundary validation
- **Data Validation**: Field validation and preparation
- **Sector Tracking**: Real-time sector occupancy (flights only)
- **Bulk Storage**: High-performance database insertion

### **3. Real-time Updates**
- **Flight Position**: Latitude, longitude, altitude, speed, heading
- **Sector Occupancy**: Automatic entry/exit detection
- **Performance Monitoring**: Speed-based criteria for sector tracking

### **4. Analytics & Summaries**
- **Flight Summaries**: Generated every 60 minutes
- **Controller Summaries**: Generated every 30 minutes
- **Sector Metrics**: Real-time occupancy and performance data

### **5. API Access**
- **Real-time Data**: Current flight positions and status
- **Historical Data**: Completed flights and summaries
- **Analytics**: Performance metrics and sector data

## 📊 **Key Performance Metrics**

| **Metric** | **Value** | **Description** |
|------------|-----------|-----------------|
| **Ingestion Frequency** | Every 60 seconds | VATSIM data refresh rate |
| **Geographic Filtering** | <1ms per flight | Australian airspace validation |
| **Sector Tracking** | ~1ms per flight | Real-time sector occupancy |
| **Database Insert** | ~0.3ms per flight | Bulk insertion performance |
| **Total Processing** | ~2.0ms per flight | Complete pipeline overhead |
| **Data Freshness** | <5 minutes | Real-time data age threshold |

## 🎯 **Data Flow Characteristics**

- **Real-time**: Continuous 60-second updates
- **Geographic**: Australian airspace focused
- **Intelligent**: Automatic sector tracking and performance monitoring
- **Scalable**: Bulk operations and optimized database queries
- **Analytical**: Comprehensive summary generation and metrics
- **API-First**: RESTful endpoints for data access and monitoring

This data flow architecture provides a robust, real-time system for tracking flights within Australian airspace with comprehensive analytics and monitoring capabilities.
