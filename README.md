# VATSIM Data Collection System

## 📋 **System Overview**

The VATSIM Data Collection System is a **production-ready, real-time air traffic control data collection and analysis platform** designed for VATSIM divisions to understand more about what happens in their airspace. While initially implemented for Australian airspace, the system is **fully configurable** through configuration files and can be deployed for any geographic region.

The system provides comprehensive flight tracking, controller tracking, and sector occupancy analysis through a streamlined, **API-first architecture**. Importantly, it matches ATC and flights through radio frequencies to allow deeper insights into effectiveness of ATC strategies, coverage and the service being provided to pilots. Used with a reporting tool such as Metabase, rich data can be extracted and used to drive insights and decisions.

### **Current Status: Production Ready ✅**
- **Operational Status**: ✅ **PRODUCTION READY** with active data collection
- **Geographic Filtering**: ✅ **ACTIVE** - Configurable airspace boundary filtering operational (currently configured for Australian airspace but can be configured for any airspace with JSON files)
- **Data Pipeline**: ✅ **OPERATIONAL** - Real-time VATSIM data ingestion every 60 seconds (configurable)
- **Sector Tracking**: ✅ **ACTIVE** - Configurable sector monitoring operational (currently configured for 17 Australian airspace sectors. Configurable to any airspace)
- **Flight Summaries**: ✅ **OPERATIONAL** - Automatic processing every 60 minutes (configurable)

### **Core Capabilities**
- **Real-time Data Collection**: Continuous VATSIM API v3 integration with 60-second polling
- **Geographic Boundary Filtering**: Shapely-based polygon filtering for any configurable airspace
- **Complete Flight Tracking**: Every position update preserved with unique constraints
- **Sector Occupancy Monitoring**: Real-time tracking of flights through any configurable airspace sectors
- **Automatic Data Management**: Flight summarization, archiving, and cleanup processes
- **Controller Proximity Detection**: Intelligent ATC interaction detection with controller-specific ranges

### **System Focus**
- **Geographic Scope**: Any airspace worldwide with configurable boundary filtering
- **Data Preservation**: Complete flight position history maintained for analytics
- **Performance Optimization**: Memory-optimized processing with <10ms geographic filtering
- **Production Reliability**: Comprehensive error handling, monitoring, and automatic recovery

### **System Configurability**
- **Generic Design**: The system is designed as a generic airspace monitoring platform, not limited to any specific region
- **Configuration-Driven**: All geographic boundaries, sectors, and operational parameters are defined in configuration files
- **Easy Deployment**: Can be deployed for any airspace by simply updating configuration files in the `config/` directory
- **Current Implementation**: Currently configured for Australian airspace as the first use case, but fully adaptable to any region

### **Business Objectives**
The system addresses critical needs in air traffic control operations:

1. **Real-time ATC Monitoring**: Continuous tracking of active controllers and their positions
2. **Flight Analysis**: Comprehensive analysis of aircraft movements and patterns
3. **Sector Management**: Real-time monitoring of airspace sector occupancy and transitions
4. **Data Analytics**: Historical analysis for operational planning and performance assessment
5. **Operational Intelligence**: Insights into ATC coverage, flight patterns, and sector utilization

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 4GB RAM available (8GB+ recommended for production)
- 10GB+ free disk space
- Internet connection for VATSIM API access
- GEOS library support (included in Docker image)

### Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd vatsim-data
   ```

2. **Start the system**
   ```bash
   docker-compose up -d
   ```

3. **Access the services**
   - **API Endpoints**: http://localhost:8001
   - **Database**: localhost:5432 (vatsim_user/vatsim_password)
   - **Metabase**: http://localhost:3030 (business intelligence)

## 📊 System Architecture

### **Core Components**

#### **Data Service** (`app/services/data_service.py`)
- **Memory-optimized data processing** to reduce SSD wear
- **Batch database operations** for efficiency
- **Geographic boundary filtering** for all entity types
- **Real-time data processing** with 60-second intervals
- **Flight summary processing** - automatic background processing every 60 minutes
- **Storage optimization** - ~90% reduction in daily storage growth

#### **Geographic Boundary Filter** (`app/filters/geographic_boundary_filter.py`)
- **Multi-entity support**: Flights, transceivers, and controllers
- **Australian airspace focus**: Uses `australian_airspace_polygon.json`
- **Performance optimized**: <1ms processing for 100+ entities
- **Configurable**: Enable/disable via environment variables
- **Conservative approach**: Missing position data allowed through

#### **Sector Tracking System**
- **Real-time Detection**: Automatically detects when flights enter/exit sectors
- **Altitude Monitoring**: Records entry and exit altitudes for vertical profile analysis
- **Duration Calculation**: Automatically calculates time spent in each sector
- **Sector Transitions**: Tracks movement between sectors with timestamps
- **Performance Optimized**: Uses Shapely polygons for fast point-in-polygon detection
- **17 Australian airspace sectors** fully tracked and monitored

#### **Flight Summary System**
- **Automatic processing** every 60 minutes
- **Complete flight history** with sector occupancy data
- **Data archiving** for long-term storage
- **API endpoints** for data access and analytics

#### **Controller Summary System**
- **Automatic processing** every 60 minutes
- **Session merging** - handles controller reconnections within 5-minute windows
- **Aircraft interaction detection** - uses controller-specific proximity ranges
- **Performance metrics** - tracks aircraft handled, peak counts, hourly breakdowns

### **Controller-Specific Proximity Ranges**
The system uses intelligent proximity ranges based on controller type:

- **Ground controllers**: 15nm (local airport operations)
- **Tower controllers**: 15nm (approach/departure operations)
- **Approach controllers**: 60nm (terminal area operations)
- **Center controllers**: 400nm (enroute operations)
- **FSS controllers**: 1000nm (flight service operations)

### **Automatic Cleanup System**
- **Purpose**: Automatically closes stale sector entries for flights that haven't been updated recently
- **Execution**: Runs automatically after each successful VATSIM data processing cycle (every 60 seconds)
- **Detection**: Identifies flights with open sector entries and no recent updates
- **Timeout**: Configurable via `CLEANUP_FLIGHT_TIMEOUT` environment variable (default: 300 seconds / 5 minutes)
- **Data Integrity**: Uses last known flight position and timestamp for accurate sector exit data
- **Transaction Safety**: Proper database commit/rollback handling ensures reliable persistence

## 🗄️ Database Schema

### **Core Tables**

| Table | Purpose | Description |
|-------|---------|-------------|
| **flights** | Live flight data | Real-time position and flight plan information |
| **transceivers** | Communication data | Radio frequency and communication information |
| **controllers** | ATC positions | Active controller positions and status |
| **flight_summaries** | Completed flights | Processed flight summaries with analytics |
| **flights_archive** | Historical data | Detailed flight position history |
| **flight_sector_occupancy** | Sector tracking | Real-time sector entry/exit data |
| **controller_summaries** | Controller sessions | Processed controller session data |
| **controllers_archive** | Controller history | Historical controller data |

### **Flight Table Structure**
The flight table stores comprehensive flight data with 32 optimized columns:

| Field Category | Fields | Source | Description |
|----------------|--------|--------|-------------|
| **Primary Key** | `id` | App | Auto-generated primary key |
| **Basic Info** | `callsign`, `aircraft_type`, `departure`, `arrival`, `route` | API | Flight identification and routing |
| **Position** | `latitude`, `longitude`, `altitude`, `heading`, `groundspeed` | API | Real-time position data |
| **Communication** | `transponder` | API | Transponder code |
| **Flight Plan** | `flight_rules`, `aircraft_faa`, `planned_altitude`, `deptime`, etc. | API | Detailed flight plan information |
| **Pilot Info** | `cid`, `name`, `server`, `pilot_rating` | API | Pilot and network information |
| **Status** | `status` | App | Flight status management |
| **Timestamps** | `last_updated_api`, `created_at`, `updated_at` | Mixed | Data timestamps |

### **Flight Plan Validation Filter**
The system includes automatic flight plan validation that ensures only flights with complete, analyzable flight plan data are stored:

| Field | Requirement | Description |
|-------|-------------|-------------|
| `departure` | Must be present and non-empty | Departure airport code (e.g., "YSSY", "KLAX") |
| `arrival` | Must be present and non-empty | Arrival airport code (e.g., "YMML", "KJFK") |
| `flight_rules` | Must be "I" (IFR) or "V" (VFR) | Flight rules classification |
| `aircraft_faa` | Must be present and non-empty | Aircraft type code (e.g., "B738", "A320") |

## ⚙️ Configuration

### **Environment Variables**

#### **Core Configuration:**
```yaml
# Database Configuration
DATABASE_URL: postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data
DATABASE_POOL_SIZE: 20
DATABASE_MAX_OVERFLOW: 40

# Geographic Boundary Filtering
ENABLE_BOUNDARY_FILTER: true
BOUNDARY_DATA_PATH: config/australian_airspace_polygon.json
BOUNDARY_FILTER_LOG_LEVEL: INFO
BOUNDARY_FILTER_PERFORMANCE_THRESHOLD: 10.0

# Flight Plan Validation Filter
FLIGHT_PLAN_VALIDATION_ENABLED: true

# VATSIM API Configuration
VATSIM_API_BASE_URL: https://data.vatsim.net/v3
VATSIM_API_TIMEOUT: 60
VATSIM_API_RETRY_ATTEMPTS: 20

# Application Configuration
LOG_LEVEL: INFO
ENVIRONMENT: production
```

#### **Flight Summary System Configuration:**
```yaml
# Flight Summary System
FLIGHT_COMPLETION_HOURS: 14        # Hours to wait before processing
FLIGHT_RETENTION_HOURS: 168       # Hours to keep archived data (7 days)
FLIGHT_SUMMARY_INTERVAL: 60       # Minutes between processing runs
FLIGHT_SUMMARY_ENABLED: true      # Enable/disable the system
```

#### **Sector Tracking Configuration:**
```yaml
# Sector Tracking System
SECTOR_TRACKING_ENABLED: true     # Enable real-time sector tracking
SECTOR_UPDATE_INTERVAL: 60        # Seconds between sector updates
SECTOR_DATA_PATH: config/australian_airspace_sectors.geojson
```

#### **Cleanup Process Configuration:**
```yaml
# Cleanup Process System
CLEANUP_FLIGHT_TIMEOUT: 300       # Seconds (5 minutes) before considering a flight stale for cleanup
```

#### **Controller Summary Configuration:**
```yaml
# Controller Summary System
CONTROLLER_SUMMARY_ENABLED: true
CONTROLLER_COMPLETION_MINUTES: 30     # 30 minutes - when summaries are made and records archived
CONTROLLER_RETENTION_HOURS: 168
CONTROLLER_SUMMARY_INTERVAL: 60
```

#### **Controller-Specific Proximity Configuration:**
```yaml
# Controller-specific proximity configuration (used by both detection services)
ENABLE_CONTROLLER_SPECIFIC_RANGES: true
CONTROLLER_PROXIMITY_DEFAULT_NM: 30
```

## 🔌 API Reference

### **Core Endpoints**

#### **System Status:**
- `GET /api/status` - System status and health checks
- `GET /api/database/status` - Database health and table status

#### **Flight Data:**
- `GET /api/flights` - Active flights with filtering and pagination
- `GET /api/flights/{callsign}` - Specific flight details
- `GET /api/flights/{callsign}/track` - Complete flight track
- `GET /api/flights/{callsign}/stats` - Flight statistics

#### **Flight Summaries:**
- `GET /api/flights/summaries` - Completed flight summaries with filtering
- `POST /api/flights/summaries/process` - Manual processing trigger
- `GET /api/flights/summaries/status` - Processing status and statistics
- `GET /api/flights/summaries/analytics` - Flight summary analytics

#### **Controller Data:**
- `GET /api/controllers` - Active ATC positions
- `GET /api/atc-positions` - Alternative ATC endpoint
- `GET /api/atc-positions/by-controller-id` - ATC positions grouped by controller ID

#### **Controller Summaries:**
- `GET /api/controller-summaries` - Controller session summaries
- `GET /api/controller-summaries/{callsign}/stats` - Controller statistics
- `GET /api/controller-summaries/performance/overview` - Performance overview
- `POST /api/controller-summaries/process` - Manual processing trigger

#### **Sector & Filter Data:**
- `GET /api/transceivers` - Radio frequency and position data
- `GET /api/filter/boundary/status` - Geographic boundary filter status
- `GET /api/filter/boundary/info` - Boundary polygon information
- `GET /api/cleanup/status` - Cleanup system status

## 🗺️ Geographic Configuration

### **Airspace Data Files**

#### **External Boundary** (`config/australian_airspace_polygon.json`)
- **Purpose**: Defines the external boundary of Australian Flight Information Region (FIR)
- **Content**: Single polygon with coordinates covering all of Australia and surrounding airspace
- **Usage**: Used by the geographic boundary filter to determine if flights/controllers are within Australian airspace
- **Format**: GeoJSON polygon with decimal degree coordinates

#### **Sector Boundaries** (`config/australian_airspace_sectors.geojson`)
- **Purpose**: Contains processed airspace sector boundaries in standard GeoJSON format
- **Content**: FeatureCollection with each main sector as a separate Feature containing combined subsector polygons
- **Usage**: Used for detailed sector analysis, ATC coverage mapping, and real-time sector tracking
- **Format**: Standard GeoJSON FeatureCollection with Polygon geometries

### **Filter Behavior**
- **Enabled by default** when `ENABLE_BOUNDARY_FILTER=true`
- **Applied before** flight plan validation filtering
- **Performance optimized** with minimal processing overhead
- **Conservative approach** - missing position data allowed through

## 🔧 Development

### **Local Development**
```bash
# Start development environment
docker-compose up -d

# Monitor logs
docker-compose logs -f app

# Access database
docker-compose exec postgres psql -U vatsim_user -d vatsim_data

# Run tests
docker-compose exec app python -m pytest tests/
```

### **Code Structure**
```
app/
├── filters/           # Geographic boundary filtering
│   ├── geographic_boundary_filter.py
│   ├── callsign_pattern_filter.py
│   └── controller_callsign_filter.py
├── services/          # Data processing and API services
│   ├── data_service.py
│   ├── vatsim_service.py
│   ├── atc_detection_service.py
│   └── flight_detection_service.py
├── models.py          # Database models (SQLAlchemy)
├── main.py            # FastAPI application
├── config.py          # Configuration management
├── database.py        # Database connection management
└── utils/             # Utility functions and helpers
    ├── geographic_utils.py
    ├── sector_loader.py
    ├── logging.py
    └── error_handling.py
```

### **Airspace Data Maintenance**

#### **Updating Sector Definitions**
1. **Sector Hierarchy File**: Edit `airspace_sector_data/SectorHierarchy.txt` to define main sectors and their subsectors
2. **VATSYS Files**: Ensure `airspace_sector_data/Volumes.xml` contains the coordinate data for all subsectors
3. **Run Processing Script**: Execute the processing script:
   ```bash
   cd airspace_sector_data
   python process_australian_sectors.py
   ```
4. **Output Files**: The script generates:
   - `australian_airspace_sectors.geojson` - Main sector boundaries in GeoJSON format
   - `australian_sectors_data.json` - Processing metadata and statistics

## 🚨 Troubleshooting

### **Common Issues**

1. **Filter not working**: Check `ENABLE_BOUNDARY_FILTER` environment variable
2. **No data in tables**: Verify VATSIM API connectivity and database connection
3. **Performance issues**: Monitor filter performance thresholds and system resources
4. **Sector tracking not working**: Check `SECTOR_TRACKING_ENABLED` and sector file paths
5. **Flight summaries not processing**: Check `FLIGHT_SUMMARY_ENABLED` and processing intervals

### **Health Checks**
```bash
# Check system health
curl http://localhost:8001/api/status

# Check filter status
curl http://localhost:8001/api/filter/boundary/status

# Check database
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM flights;"
```

## 📚 Documentation

### **Core Documentation**
- **[Architecture Overview](docs/VATSIM_ARCHITECTURE_COMPLETE.md)** - System design and components
- **[API Reference](docs/API_REFERENCE.md)** - Complete API endpoint documentation
- **[Configuration Guide](docs/CONFIGURATION.md)** - Environment setup and tuning
- **[Production Deployment](docs/PRODUCTION_DEPLOYMENT_GUIDE.md)** - Production setup guide

### **Feature Documentation**
- **[Geographic Filter Config](docs/GEOGRAPHIC_BOUNDARY_FILTER_CONFIG.md)** - Filter configuration guide
- **[Flight Summary Status](docs/FLIGHT_SUMMARY_IMPLEMENTATION_STATUS.md)** - Flight summary system status
- **[Controller Summary Plan](docs/CONTROLLER_SUMMARY_IMPLEMENTATION_PLAN.md)** - Controller summary system
- **[Sector Tracking Plan](docs/SECTOR_TRACKING_IMPLEMENTATION_PLAN.md)** - Sector tracking system

### **Airspace Data Documentation**
- **[Australian Sector Processing](airspace_sector_data/PROCESSING_AUSTRALIAN_SECTOR_FILES_README.md)** - Complete guide for processing VATSYS sector files
- **[Controller Callsign Extraction](airspace_sector_data/CONTROLLER_CALLSIGN_EXTRACTION_README.md)** - Controller callsign processing guide

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For issues, questions, or contributions:
- Check the documentation first
- Review existing issues and pull requests
- Create a new issue with detailed information

---

**📅 Last Updated**: 2025-01-16  
**🚀 Status**: Production Ready  
**🗺️ Geographic Coverage**: Australian Airspace (Configurable for any region)  
**⚡ Performance**: <1ms filtering overhead  
**🔧 Architecture**: API-first with real-time data processing
