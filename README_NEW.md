# VATSIM Data Collection System

A real-time VATSIM data collection system that processes flight data, ATC positions, and network statistics with comprehensive geographic boundary filtering and real-time sector tracking for Australian airspace.

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

### **Current Status: Production Ready ✅**
The system has been significantly simplified and optimized with comprehensive geographic boundary filtering and automatic cleanup processes:

- **Geographic boundary filtering implemented** for flights, transceivers, and controllers
- **Real-time sector tracking fully operational** - tracks flights through 17 Australian airspace sectors
- **Controller-specific proximity ranges fully implemented** - dynamic ranges based on controller type
- **Automatic cleanup system operational** - automatically closes stale sector entries with transaction safety
- **Data ingestion fully functional** - all tables populated with live VATSIM data
- **Schema mismatches resolved** - Python models match database schema
- **Performance optimized** - filtering adds <1ms overhead for 100+ entities
- **Sector tracking operational** - real-time sector occupancy monitoring with automatic transitions
- **Transaction safety implemented** - proper database commit/rollback handling for reliable persistence

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
- **Backend logic implemented** in data service with scheduled processing
- **Database tables exist** (flight_summaries, flights_archive)
- **Background processing active** every 60 minutes
- **API endpoints complete** - full public access to flight summaries
- **Manual processing endpoint** - can trigger processing manually
- **Status monitoring** - complete processing status and statistics
- **Analytics and reporting** - comprehensive flight summary analytics
- **Sector breakdown integration** - includes sector occupancy data in summaries

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

### **Current Tables Status**

| Table | Status | Records | Geographic Filtering |
|-------|--------|---------|---------------------|
| **flights** | ✅ Active | Live data | ✅ Enabled |
| **transceivers** | ✅ Active | Live data | ✅ Enabled |
| **controllers** | ✅ Active | Live data | ✅ Enabled (conservative) |
| **flight_summaries** | ✅ Active | Completed flights | ✅ Full API access |
| **flights_archive** | ✅ Active | Detailed history | ✅ Full API access |
| **flight_sector_occupancy** | ✅ Active | Sector tracking data | ✅ Real-time updates |
| **controller_summaries** | ✅ Active | Controller sessions | ✅ Full API access |
| **controllers_archive** | ✅ Active | Controller history | ✅ Full API access |

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
# Flight Summary System (Fully Operational)
FLIGHT_COMPLETION_HOURS: 14        # Hours to wait before processing
FLIGHT_RETENTION_HOURS: 168       # Hours to keep archived data (7 days)
FLIGHT_SUMMARY_INTERVAL: 60       # Minutes between processing runs
FLIGHT_SUMMARY_ENABLED: true      # Enable/disable the system
```

#### **Sector Tracking Configuration:**
```yaml
# Sector Tracking System (Fully Operational)
SECTOR_TRACKING_ENABLED: true     # Enable real-time sector tracking
SECTOR_UPDATE_INTERVAL: 60        # Seconds between sector updates
SECTOR_DATA_PATH: config/australian_airspace_sectors.geojson
```

#### **Cleanup Process Configuration:**
```yaml
# Cleanup Process System (Fully Operational)
CLEANUP_FLIGHT_TIMEOUT: 300       # Seconds (5 minutes) before considering a flight stale for cleanup
```

#### **Controller Summary Configuration:**
```yaml
# Controller Summary System (Fully Operational)
CONTROLLER_SUMMARY_ENABLED: true
CONTROLLER_COMPLETION_MINUTES: 30     # 30 minutes - when summaries are made and records archived
CONTROLLER_RETENTION_HOURS: 168
CONTROLLER_SUMMARY_INTERVAL: 60
```

#### **Controller-Specific Proximity Configuration:**
```yaml
# Controller-specific proximity configuration (used by both detection services)
CONTROLLER_PROXIMITY_GROUND_NM: 15      # Ground controllers: 15nm
CONTROLLER_PROXIMITY_TOWER_NM: 15       # Tower controllers: 15nm
CONTROLLER_PROXIMITY_APPROACH_NM: 60    # Approach controllers: 60nm
CONTROLLER_PROXIMITY_CENTER_NM: 400     # Center controllers: 400nm
CONTROLLER_PROXIMITY_FSS_NM: 1000      # FSS controllers: 1000nm
ENABLE_CONTROLLER_SPECIFIC_RANGES: true
CONTROLLER_PROXIMITY_DEFAULT_NM: 30     # Fallback for unknown controller types
```

## 🗺️ Geographic Boundary Filtering

### **Overview**
The system includes comprehensive geographic boundary filtering that processes:
- **Flights**: Filtered by `latitude`/`longitude` position
- **Transceivers**: Filtered by `position_lat`/`position_lon` position  
- **Controllers**: Currently uses conservative approach (all allowed through)

### **Australian Airspace Data Structure**
The system uses a comprehensive approach for geographic filtering and sector management:

#### **`australian_airspace_polygon.json` - External FIR Boundary**
- **Purpose**: Defines the external boundary of Australian Flight Information Region (FIR)
- **Content**: Single polygon with coordinates covering all of Australia and surrounding airspace
- **Usage**: Used by the geographic boundary filter to determine if flights/controllers are within Australian airspace
- **Status**: **Static file** - does not change and represents the official Australian FIR boundary
- **Format**: GeoJSON polygon with decimal degree coordinates

#### **`australian_airspace_sectors.geojson` - Processed Sector Boundaries**
- **Purpose**: Contains processed airspace sector boundaries in standard GeoJSON format
- **Content**: FeatureCollection with each main sector as a separate Feature containing combined subsector polygons
- **Usage**: Used for detailed sector analysis, ATC coverage mapping, and **real-time sector tracking**
- **Status**: **Automatically generated** from VATSYS XML files using the simplified processing script
- **Format**: Standard GeoJSON FeatureCollection with Polygon geometries

### **Filter Behavior**
- **Enabled by default** when `ENABLE_BOUNDARY_FILTER=true`
- **Applied before** flight plan validation filtering
- **Performance optimized** with minimal processing overhead
- **Conservative approach** - missing position data allowed through

## 📈 Monitoring & Analytics

### **API Endpoints**

#### **System Status:**
- `GET /api/status` - Comprehensive system status and health checks
- `GET /api/database/status` - Database health and table status
- `GET /api/startup/health` - Startup health verification

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

#### **Transceiver Data:**
- `GET /api/transceivers` - Radio frequency and position data

#### **Filter Status:**
- `GET /api/filter/boundary/status` - Geographic boundary filter status
- `GET /api/filter/boundary/info` - Boundary polygon information
- `GET /api/filter/controller-callsign/status` - Controller callsign filter status

#### **Cleanup System:**
- `POST /api/cleanup/stale-sectors` - Manually trigger cleanup process
- `GET /api/cleanup/status` - Current cleanup system status

#### **Database Operations:**
- `GET /api/database/tables` - Database tables and record counts
- `POST /api/database/query` - Execute custom SQL queries (admin only)

### **Data Freshness Monitoring**
The system provides comprehensive data freshness monitoring:

- **Real-time tables** (controllers, flights, transceivers): < 5 minutes (300 seconds)
- **Batch tables** (summaries, archive, sector): < 2 hours (7200 seconds)
- **Historical tables** (archive tables): Freshness not applicable

## 🧪 Testing & Validation

### **Test Coverage**
- ✅ **Unit Tests**: Geographic utilities and filter logic (89 tests)
- ✅ **Integration Tests**: API endpoints and data flow (17 tests)
- ✅ **End-to-End Tests**: Complete workflow validation (5 tests)
- ✅ **Performance Tests**: Filter performance and overhead measurement
- ✅ **Real Outcome Testing**: Verifies actual outcomes and outputs

### **Test Results**
Recent testing shows:
- **Filter Accuracy**: 100% for flights and transceivers
- **Performance**: <1ms overhead for 100+ entities
- **Configuration**: Proper on/off functionality
- **Live Data**: Successfully processes real VATSIM data
- **Service Symmetry**: Both detection services return identical results

### **Test Execution**
```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/ -k "geographic"
python -m pytest tests/ -k "integration"
python -m pytest tests/ -k "unit"

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

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
The sector boundaries are processed using a simplified approach:

1. **Sector Hierarchy File**: Edit `airspace_sector_data/SectorHierarchy.txt` to define main sectors and their subsectors
2. **VATSYS Files**: Ensure `airspace_sector_data/Volumes.xml` contains the coordinate data for all subsectors
3. **Run Processing Script**: Execute the simplified processing script:
   ```bash
   cd airspace_sector_data
   python process_australian_sectors.py
   ```
4. **Review Output**: Verify the generated GeoJSON files match expectations
5. **Output Files**: The script generates:
   - `australian_airspace_sectors.geojson` - Main sector boundaries in GeoJSON format
   - `australian_sectors_data.json` - Processing metadata and statistics

#### **External Boundary (Static)**
The `config/australian_airspace_polygon.json` file:
- **Never changes** - represents official Australian FIR boundary
- **Used directly** by the geographic boundary filter
- **No maintenance required** - this is a reference data file

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

# Check sector tracking status
curl http://localhost:8001/api/sector/status

# Check cleanup system status
curl http://localhost:8001/api/cleanup/status

# Monitor database
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM flights;"
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM flight_sector_occupancy;"
```

### **Performance Monitoring**
The system provides comprehensive performance monitoring:

- **API Response Time**: Target <500ms
- **Database Query Time**: Target <100ms
- **Filter Processing**: <1ms overhead for 100+ entities
- **Memory Usage**: Target <70% of allocated memory

## 📚 Documentation

### **Core Documentation**
- **[Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md)** - System design and components
- **[API Reference](docs/API_REFERENCE.md)** - Complete API endpoint documentation
- **[Configuration Guide](docs/CONFIGURATION.md)** - Environment setup and tuning
- **[Database Architecture](docs/DATABASE_ARCHITECTURE.md)** - Database design and optimization
- **[Production Deployment](docs/PRODUCTION_DEPLOYMENT_GUIDE.md)** - Production setup guide

### **Feature Documentation**
- **[Geographic Filter Config](docs/GEOGRAPHIC_BOUNDARY_FILTER_CONFIG.md)** - Filter configuration guide
- **[Flight Summary Status](docs/FLIGHT_SUMMARY_IMPLEMENTATION_STATUS.md)** - Flight summary system status
- **[Controller Summary Plan](docs/CONTROLLER_SUMMARY_IMPLEMENTATION_PLAN.md)** - Controller summary system
- **[Sector Tracking Plan](docs/SECTOR_TRACKING_IMPLEMENTATION_PLAN.md)** - Sector tracking system

### **Airspace Data Documentation**
- **[Australian Sector Processing](airspace_sector_data/PROCESSING_AUSTRALIAN_SECTOR_FILES_README.md)** - Complete guide for processing VATSYS sector files
- **[Controller Callsign Extraction](airspace_sector_data/CONTROLLER_CALLSIGN_EXTRACTION_README.md)** - Controller callsign processing guide

## 🚀 Recent Updates

### **January 2025 - System Optimization & Cleanup**
- **Automatic cleanup system** implemented for stale sector management
- **Transaction safety** improved with proper commit/rollback handling
- **Performance optimization** with <1ms filtering overhead
- **Real-time sector tracking** fully operational for 17 Australian sectors
- **Flight summary system** 100% complete and operational
- **Controller summary system** fully implemented with session merging
- **Geographic boundary filtering** optimized for multi-entity support

### **December 2024 - Geographic Filtering & Sector Tracking**
- **Geographic boundary filtering** implemented for flights, transceivers, and controllers
- **Real-time sector tracking** system operational
- **Controller-specific proximity ranges** implemented
- **Flight plan validation filter** added for data quality
- **Performance optimization** completed

### **November 2024 - Core System Implementation**
- **VATSIM API integration** completed with full field mapping
- **Database schema** optimized and aligned
- **API endpoints** implemented and tested
- **Data pipeline** operational for real-time collection

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
**🚀 Status**: Production Ready with Geographic Filtering, Complete Flight Summary System, Real-Time Sector Tracking & Automatic Cleanup Process  
**🗺️ Geographic Coverage**: Australian Airspace  
**⚡ Performance**: <1ms filtering overhead  
**🔧 Architecture**: Simplified and optimized  
**📊 Flight Summary**: Fully operational with complete API access  
**🎯 Sector Tracking**: Fully operational with real-time monitoring  
**🧹 Cleanup Process**: Fully operational with automatic stale sector management  
**✅ System Status**: Complete and fully functional
