# VATSIM Data Collection System

## 📋 **System Overview**

The VATSIM Data Collection System is an air traffic data collection and analysis platform designed for VATSIM divisions to understand more about what happens in their airspace. While initially implemented for Australian airspace, the system is **fully configurable** through configuration files and can be deployed for any geographic region.

The system provides comprehensive flight tracking, controller tracking, and sector occupancy analysis through a streamlined, **API-first architecture**. Importantly, it matches ATC and flights through radio frequencies to allow deeper insights into effectiveness of ATC strategies, coverage and the service being provided to pilots. Used with a reporting tool such as Metabase, rich data can be extracted and used to drive insights and decisions.

### **Current Status: Production Ready ✅**
- **Operational Status**: ✅ **PRODUCTION READY** with active data collection
- **Geographic Filtering**: ✅ **ACTIVE** - Configurable airspace boundary filtering operational (currently configured for Australian airspace but can be configured for any airspace with JSON files)
- **Data Pipeline**: ✅ **OPERATIONAL** - Real-time VATSIM data ingestion every 60 seconds (configurable)
- **Sector Tracking**: ✅ **ACTIVE** - Configurable sector monitoring operational (currently configured for 17 Australian airspace sectors. Configurable to any airspace)
- **Flight Summaries**: ✅ **OPERATIONAL** - Automatic processing every 60 minutes (configurable)

### **Core Capabilities**
- **Real-time Data Collection**: Continuous VATSIM API v3 integration with 60-second polling (configurable)
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

### **Prerequisites**
Before installing, ensure your machine meets these requirements:

#### **System Requirements**
- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS 10.15+, or Windows 10/11 with WSL2
- **RAM**: Minimum 4GB, recommended 8GB+ for production
- **Storage**: Minimum 10GB free space, recommended 50GB+ for production data
- **CPU**: 2+ cores recommended for production workloads
- **Network**: Internet connection for VATSIM API access

#### **Software Dependencies**
- **Docker**: Version 20.10+ with Docker Compose V2
- **Git**: For cloning the repository
- **Make** (optional): For simplified commands on Linux/macOS

### **Installation Steps**

#### **Step 1: Install Docker and Docker Compose**

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install required packages
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group (requires logout/login)
sudo usermod -aG docker $USER

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
```

**macOS:**
```bash
# Install Docker Desktop
brew install --cask docker

# Or download from: https://www.docker.com/products/docker-desktop
```

**Windows:**
- Download Docker Desktop from: https://www.docker.com/products/docker-desktop
- Install and enable WSL2 if prompted
- Ensure virtualization is enabled in BIOS

**Verify Docker Installation:**
```bash
docker --version
docker compose version
```

#### **Step 2: Get the System Files**

**Option A: Clone Repository (Development)**
```bash
# Clone the repository
git clone <repository-url>
cd vatsim-data
```

**Option B: Minimal Deployment (Production)**
```bash
# Create deployment directory
mkdir vatsim-deployment
cd vatsim-deployment

# Download only essential files
curl -O https://raw.githubusercontent.com/yourusername/vatsim-data/main/docker-compose.yml

# Create required directories
mkdir -p database/vatsim logs config

# Download config files
curl -O https://raw.githubusercontent.com/yourusername/vatsim-data/main/config/init.sql
curl -O https://raw.githubusercontent.com/yourusername/vatsim-data/main/config/australian_airspace_polygon.json
curl -O https://raw.githubusercontent.com/yourusername/vatsim-data/main/config/australian_airspace_sectors.geojson

# Move config files to config directory
mv init.sql australian_airspace_polygon.json australian_airspace_sectors.geojson config/
```

**Option C: Single Script Deployment**
```bash
# Download and run deployment script
curl -s https://raw.githubusercontent.com/yourusername/vatsim-data/main/scripts/deploy-vatsim.sh | bash
```

**Expected Directory Structure:**

**For Development (Full Clone):**
```
vatsim-data/
├── app/                    # Application code
├── config/                 # Configuration files
├── database/              # Database storage
│   └── vatsim/           # PostgreSQL data files
├── logs/                  # Application logs
├── docker-compose.yml     # Core services
├── docker-compose.metabase.yml  # Business intelligence
├── Dockerfile             # Application container
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

**For Minimal Deployment:**
```
vatsim-deployment/
├── config/                 # Configuration files
│   ├── init.sql           # Database schema
│   ├── australian_airspace_polygon.json
│   └── australian_airspace_sectors.geojson
├── database/              # Database storage
│   └── vatsim/           # PostgreSQL data files
├── logs/                  # Application logs
└── docker-compose.yml     # Core services
```

#### **Step 3: Configure the System**

**Create Required Directories:**
```bash
# Create database storage directory (required for PostgreSQL)
mkdir -p database/vatsim

# Create logs directory (required for application logging)
mkdir -p logs

# Set proper permissions
chmod 755 database/vatsim logs
```

**Verify Configuration Files:**
```bash
# Check that required config files exist
ls -la config/
# Should show: init.sql, australian_airspace_polygon.json, australian_airspace_sectors.geojson
```

**Important**: The `config/` directory contains essential files that must be present for the system to work:
- **`init.sql`** - Database schema and initialization (required for PostgreSQL)
- **`australian_airspace_polygon.json`** - Geographic boundary filter (required for airspace filtering)
- **`australian_airspace_sectors.geojson`** - Sector definitions (required for sector tracking)

**If any of these files are missing, the system will fail to start or function properly.**

#### **Step 4: Start the System**

**Start Core Services:**
```bash
# Start PostgreSQL and VATSIM application
docker compose up -d

# Verify services are running
docker compose ps
```

**Expected Output:**
```
NAME                COMMAND                  SERVICE             STATUS              PORTS
vatsim_app         "python -m uvicorn …"    app                 running             0.0.0.0:8001->8001/tcp
vatsim_postgres    "docker-entrypoint.s…"   postgres            running             0.0.0.0:5432->5432/tcp
```

**Start Metabase (Optional):**
```bash
# Start business intelligence platform
docker compose -f docker-compose.metabase.yml up -d

# Verify Metabase is running
docker compose -f docker-compose.metabase.yml ps
```

#### **Step 5: Verify Installation**

**Check System Health:**
```bash
# Wait for services to fully start (2-3 minutes)
sleep 180

# Check API status
curl http://localhost:8001/api/status

# Check database status
curl http://localhost:8001/api/database/status

# Check filter status
curl http://localhost:8001/api/filter/boundary/status
```

**Expected API Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-16T10:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "vatsim_api": "operational",
    "geographic_filter": "active"
  }
}
```

**Check Database Connection:**
```bash
# Connect to database
docker compose exec postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"

# Expected output: Should show 8 tables
```

**Check Logs:**
```bash
# View application logs
docker compose logs app

# View database logs
docker compose logs postgres

# View Metabase logs (if running)
docker compose -f docker-compose.metabase.yml logs metabase
```

### **Post-Installation Configuration**

#### **Environment Variables (Optional)**
The system works with default settings, but you can customize:

**Create `.env` file (optional):**
```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

**Key Configuration Options:**
```bash
# Geographic filtering
ENABLE_BOUNDARY_FILTER=true
BOUNDARY_DATA_PATH=config/australian_airspace_polygon.json

# Data collection intervals
VATSIM_POLLING_INTERVAL=60
FLIGHT_SUMMARY_INTERVAL=60

# Database settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

#### **Access Points**
Once running, access the system at:

- **VATSIM API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Database**: localhost:5432 (vatsim_user/vatsim_password)
- **Metabase**: http://localhost:3030 (if enabled)

### **Troubleshooting Installation**

#### **Common Issues**

**1. Port Already in Use:**
```bash
# Check what's using the ports
sudo netstat -tulpn | grep :8001
sudo netstat -tulpn | grep :5432

# Stop conflicting services or change ports in docker-compose.yml
```

**2. Docker Permission Issues:**
```bash
# Fix Docker permissions
sudo chown $USER:$USER ~/.docker
sudo chmod 666 /var/run/docker.sock

# Or restart Docker service
sudo systemctl restart docker
```

**3. Insufficient Memory:**
```bash
# Check available memory
free -h

# If less than 4GB, increase swap or reduce Docker memory limits
```

**4. Database Connection Failures:**
```bash
# Check if PostgreSQL is running
docker compose exec postgres pg_isready -U vatsim_user -d vatsim_data

# Check database logs
docker compose logs postgres
```

**5. Geographic Filter Not Working:**
```bash
# Verify config files exist
ls -la config/australian_airspace_polygon.json
ls -la config/australian_airspace_sectors.geojson

# Check filter status
curl http://localhost:8001/api/filter/boundary/status
```

**6. Missing Configuration Files:**
```bash
# Check if config directory exists and has required files
ls -la config/

# Required files:
# - init.sql (database schema)
# - australian_airspace_polygon.json (geographic boundary)
# - australian_airspace_sectors.geojson (sector definitions)

# If files are missing, the system cannot start properly
```

#### **Reset Installation (if needed)**
```bash
# Stop all services
docker compose down
docker compose -f docker-compose.metabase.yml down

# Remove all data (WARNING: This deletes all collected data)
sudo rm -rf database/vatsim logs data cache

# Recreate directories
mkdir -p database/vatsim logs data cache
chmod 755 database/vatsim logs data cache

# Restart services
docker compose up -d
```

### **Next Steps**

After successful installation:

1. **Monitor Data Collection**: Check that VATSIM data is being collected
2. **Configure Geographic Boundaries**: Update airspace files for your region
3. **Set Up Monitoring**: Configure log rotation and health monitoring
4. **Production Deployment**: Review production deployment guide for scaling
5. **Customization**: Modify sector definitions and filtering rules

### **Configuration Files Explained**

The `config/` directory contains essential files that the system requires to function:

#### **`init.sql`** - Database Schema
- **Purpose**: Creates all database tables, indexes, and constraints
- **Why Essential**: Without this, PostgreSQL starts with an empty database
- **What Happens If Missing**: System starts but has no tables, all API calls fail

#### **`australian_airspace_polygon.json`** - Geographic Boundary
- **Purpose**: Defines the Australian airspace boundary for filtering
- **Why Essential**: Geographic filtering won't work without this file
- **What Happens If Missing**: All flights/controllers pass through unfiltered

#### **`australian_airspace_sectors.geojson`** - Sector Definitions
- **Purpose**: Defines individual airspace sectors for tracking
- **Why Essential**: Sector occupancy tracking won't work without this file
- **What Happens If Missing**: No sector data is recorded

**⚠️ Critical**: These files must be present before starting the system. If any are missing, the system will fail to function properly.

### **Support**

If you encounter issues:
1. Check the logs: `docker compose logs app`
2. Verify system requirements are met
3. Check the troubleshooting section above
4. Review existing GitHub issues
5. Create a new issue with detailed error information

### **Usage Patterns**

#### **VATSIM Only (Recommended for development)**
```bash
docker-compose up -d
```
- Starts PostgreSQL database and VATSIM API
- Ports: 8001 (API), 5432 (Database)
- No Metabase overhead

#### **Metabase Only (For existing VATSIM data analysis)**
```bash
docker-compose -f docker-compose.metabase.yml up -d
```
- Starts Metabase and its PostgreSQL database
- Ports: 3030 (Metabase), internal database
- Requires existing VATSIM database connection

#### **Full Stack (Production)**
```bash
# Start core services first
docker-compose up -d

# Start Metabase after core services are healthy
docker-compose -f docker-compose.metabase.yml up -d
```

#### **Service Management**
```bash
# Stop only Metabase
docker-compose -f docker-compose.metabase.yml down

# Stop only VATSIM services
docker-compose down

# Stop everything
docker-compose down && docker-compose -f docker-compose.metabase.yml down
```

3. **Access the services**
   - **API Endpoints**: http://localhost:8001
   - **Database**: localhost:5432 (vatsim_user/vatsim_password)
   - **Metabase**: http://localhost:3030 (business intelligence) - *requires separate compose file*

## 📊 System Architecture

### **Infrastructure Design**
The system uses a **modular Docker Compose architecture** that separates concerns:

- **Core Application Stack** (`docker-compose.yml`)
  - PostgreSQL database for VATSIM data
  - FastAPI application for data processing and API endpoints
  - Optimized for real-time data collection and processing

- **Business Intelligence Stack** (`docker-compose.metabase.yml`)
  - Metabase application for data visualization and analytics
  - Separate PostgreSQL instance for Metabase metadata
  - Independent scaling and maintenance

This separation ensures:
- **Service isolation** - Core app performance unaffected by Metabase operations
- **Independent scaling** - Can scale Metabase without impacting data collection
- **Maintenance flexibility** - Update BI tools without service interruption
- **Resource optimization** - Run only needed services for specific use cases

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
- **Dual ATC coverage metrics**:
  - `controller_time_percentage`: Total ATC coverage (ground + airborne)
  - `airborne_controller_time_percentage`: Airborne ATC coverage (>1500ft)

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
| **transceivers** | Communication data | Radio frequency and communication information (excludes 122.8 MHz range) |
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

### **Transceivers Table & Data Quality**
The transceivers table stores radio frequency and position data with built-in data quality constraints:

| Field | Type | Description |
|-------|------|-------------|
| `frequency` | BIGINT | Frequency in Hz (excludes 122.8 MHz range) |
| `position_lat/lon` | DOUBLE | Position coordinates |
| `entity_type` | VARCHAR | 'flight' or 'atc' |
| `entity_id` | INTEGER | Reference to flights or controllers table |

**Data Quality Constraint:**
- **122.8 MHz Exclusion**: CHECK constraint prevents insertion of frequencies in the 122800000-122800999 Hz range
- **Reason**: 122.8 MHz is commonly misused in VATSIM and doesn't represent valid operational frequencies

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

maintenance/           # Database maintenance and health monitoring
├── maintain_database_health.sh    # Main maintenance script
├── prevent_index_corruption.sql   # PostgreSQL maintenance operations
└── README.md                      # Maintenance documentation
```

### **Database Maintenance**

#### **Automated Health Monitoring**
The system includes comprehensive database maintenance scripts to prevent index corruption and maintain optimal performance:

**Location**: `maintenance/` directory

**Key Scripts**:
- **`maintain_database_health.sh`** - Main maintenance script with health checks, index optimization, and log cleanup
- **`prevent_index_corruption.sql`** - PostgreSQL maintenance operations (ANALYZE, VACUUM, bloat detection)

**Usage**:
```bash
# Run all maintenance tasks
./maintenance/maintain_database_health.sh

# Check database health only
./maintenance/maintain_database_health.sh check

# Optimize indexes only
./maintenance/maintain_database_health.sh optimize

# Show help
./maintenance/maintain_database_health.sh help
```

**Scheduled Maintenance**:
- **Recommended**: Weekly maintenance every Wednesday at 16:00 UTC
- **Post-deployment**: Run after major schema changes
- **Monitoring**: Continuous health checks for production systems

**Features**:
- ✅ Real-time bloat detection using PostgreSQL statistics
- ✅ Safe REINDEX operations with timeout protection
- ✅ Container health validation and error handling
- ✅ Comprehensive logging and reporting
- ✅ Unused index identification and cleanup recommendations

**For complete maintenance documentation**: See [maintenance/README.md](maintenance/README.md)

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

### **Docker Compose Issues**

6. **"Orphan containers" warning**: This is normal when using multiple compose files
   - **Cause**: Docker sees containers from other compose files as "orphans"
   - **Solution**: Ignore the warning - it doesn't affect functionality
   - **Prevention**: Use `--remove-orphans` flag only if you want to stop all services

7. **Metabase can't connect to VATSIM database**: Check network configuration
   - **Cause**: Metabase needs access to the main PostgreSQL instance
   - **Solution**: Ensure both compose files are running on the same Docker network
   - **Verification**: Check `docker network ls` for shared networks

8. **Port conflicts**: Verify port assignments
   - **VATSIM API**: Port 8001
   - **VATSIM Database**: Port 5432
   - **Metabase**: Port 3030
   - **Metabase Database**: Internal only (no host port mapping)

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
