# VATSIM Data Collection System

A high-performance, API-driven platform for real-time VATSIM data collection, analysis, and monitoring. The system features centralized error handling, comprehensive observability, and is optimized for Grafana integration.

## 🚀 Features

- **API-First Design**: All functionality exposed through REST APIs
- **Centralized Error Handling**: Consistent error management across all services
- **Real-time VATSIM Data Collection**: Collects ATC position, flight, and sector data
- **Advanced Analytics**: Traffic analysis, movement detection, and workload optimization
- **Performance Optimized**: SSD wear reduction, memory caching, and bulk operations
- **Scalable Architecture**: Microservices-oriented with independent scaling
- **Comprehensive Monitoring**: Grafana dashboards and centralized error tracking
- **Production Ready**: Fault tolerance with circuit breakers and retry mechanisms

## 📋 Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows (with WSL2 for Windows)
- **Python**: 3.11 or higher
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: 10GB free space minimum
- **Network**: Internet connection for VATSIM API access

### Software Dependencies
- **Docker & Docker Compose** (for containerized deployment)
- **Python 3.11+** (for manual installation)
- **PostgreSQL 13+** (for production database)
- **Redis 6+** (for caching layer)

## 🛠️ Installation

### Option 1: Docker Compose (Recommended for Production)

#### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd vatsim-data

# Start all services
docker compose up -d

# Verify installation
curl http://localhost:8001/api/status
```

#### Detailed Docker Setup
```bash
# 1. Clone the repository
git clone <repository-url>
cd vatsim-data

# 2. Create environment file (optional)
cp env.example .env
# Edit .env with your configuration

# 3. Build and start services
docker compose up -d --build

# 4. Check service status
docker compose ps

# 5. View logs
docker compose logs -f app
```

#### Docker Services
- **VATSIM API**: http://localhost:8001
- **Grafana**: http://localhost:3050 (admin/admin)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Option 2: Manual Installation (Development)

#### Step 1: Install System Dependencies

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install Python and development tools
sudo apt install python3.11 python3.11-dev python3.11-venv python3-pip

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Install Redis
sudo apt install redis-server

# Install additional dependencies
sudo apt install build-essential libpq-dev
```

**macOS:**
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Install PostgreSQL
brew install postgresql

# Install Redis
brew install redis

# Start services
brew services start postgresql
brew services start redis
```

**Windows (with WSL2):**
```bash
# Install WSL2 and Ubuntu
# Then follow Ubuntu instructions above
```

#### Step 2: Set Up Python Environment
```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

#### Step 3: Install Python Dependencies
```bash
# Install requirements
pip install -r requirements.txt

# Verify installation
python -c "import fastapi, sqlalchemy, redis; print('Dependencies installed successfully')"
```

#### Step 4: Configure Database
```bash
# Create PostgreSQL database
sudo -u postgres createdb vatsim_data

# Create database user
sudo -u postgres createuser vatsim_user

# Set password for user
sudo -u postgres psql -c "ALTER USER vatsim_user PASSWORD 'vatsim_password';"

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vatsim_data TO vatsim_user;"
```

#### Step 5: Configure Environment Variables
```bash
# Create environment file
cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001

# Performance Settings
MEMORY_LIMIT_MB=2048
BATCH_SIZE_THRESHOLD=10000

# Error Handling
LOG_LEVEL=info
ERROR_MONITORING_ENABLED=true

# VATSIM API Settings
VATSIM_API_URL=https://data.vatsim.net/v3/
VATSIM_POLLING_INTERVAL=30
VATSIM_WRITE_INTERVAL=300
EOF
```

#### Step 6: Initialize Database
```bash
# Run database initialization
python -c "from app.database import init_db; init_db()"

# Verify database setup
python -c "from app.database import get_database_info; print(get_database_info())"
```

#### Step 7: Start the Application
```bash
# Start the application
python run.py

# Verify the API is running
curl http://localhost:8001/api/status
```

### Option 3: Development Setup

#### Prerequisites for Development
```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8 mypy

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

#### Development Environment Setup
```bash
# 1. Clone repository
git clone <repository-url>
cd vatsim-data

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up development database (SQLite for development)
export DATABASE_URL="sqlite:///./dev.db"

# 5. Initialize database
python -c "from app.database import init_db; init_db()"

# 6. Start development server
python run.py
```

## 📁 Project Structure

```
VATSIM data/
├── app/                          # Main application
│   ├── services/                 # Business logic services
│   │   ├── data_service.py       # Data ingestion and processing
│   │   ├── traffic_analysis_service.py # Traffic analysis
│   │   ├── ml_service.py         # Machine learning
│   │   ├── cache_service.py      # Caching layer
│   │   ├── query_optimizer.py    # Database optimization
│   │   └── resource_manager.py   # System resource management
│   ├── utils/                    # Utility functions
│   │   ├── error_handling.py     # Centralized error handling
│   │   ├── logging.py            # Logging utilities
│   │   └── exceptions.py         # Custom exceptions
│   ├── main.py                   # FastAPI application
│   ├── database.py               # Database configuration
│   ├── models.py                 # SQLAlchemy models
│   └── config.py                 # Configuration management
├── grafana/                      # Grafana dashboards & config
│   ├── dashboards/              # Dashboard JSON files
│   └── provisioning/            # Auto-provisioning config
├── docs/                         # Documentation
│   ├── migration/                # Database migration docs
│   ├── optimization/             # Performance optimization docs
│   └── analysis/                 # Data analysis docs
├── scripts/                      # Utility scripts
├── tools/                        # Database tools
├── data/                         # Data files
├── logs/                         # Application logs
└── requirements.txt              # Python dependencies
```

## 🛠️ Quick Start

### Option 1: Docker Compose (Recommended)
```bash
# Start all services
docker compose up -d

# Access services
# - VATSIM API: http://localhost:8001
# - Grafana: http://localhost:3050 (no auth required)
# - API Docs: http://localhost:8001/docs
# - API Status: http://localhost:8001/api/status
```

### Option 2: Manual Setup
```bash
# 1. Install Dependencies
pip install -r requirements.txt

# 2. Run the Application
python run.py

# 3. Access the API
# - API Documentation: http://localhost:8001/docs
# - API Status: http://localhost:8001/api/status
# - Grafana: Configure to connect to API endpoints
```

## 📊 System Architecture

### API-First Design
The system is built with an API-first approach, exposing all functionality through REST APIs:

#### Core API Endpoints
- **System Status**: `/api/status`, `/api/network/status`
- **ATC Data**: `/api/atc-positions`, `/api/vatsim/ratings`
- **Flight Data**: `/api/flights`, `/api/flights/memory`
- **Traffic Analysis**: `/api/traffic/*` endpoints
- **Performance**: `/api/performance/*` endpoints
- **Database**: `/api/database/*` endpoints
- **Airports**: `/api/airports/*` endpoints

### Data Flow
1. **VATSIM API** → **Data Service** → **Memory Cache** → **PostgreSQL Database**
2. **PostgreSQL Database** → **Analytics Services** → **Grafana Dashboards**
3. **Real-time Updates** with centralized error handling
4. **Caching**: Redis provides high-performance caching layer

### Services
- **VATSIM API**: Main application (port 8001)
- **PostgreSQL**: Database (port 5432)
- **Redis**: Caching (port 6379)
- **Grafana**: Visualization (port 3050)

### Centralized Error Handling
All services use centralized error handling with decorators:
```python
@handle_service_errors
@log_operation("operation_name")
async def service_method():
    # Service logic with automatic error handling
    pass
```

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data

# API Settings
API_HOST=0.0.0.0
API_PORT=8001

# Performance
MEMORY_LIMIT_MB=2048
BATCH_SIZE_THRESHOLD=10000

# Error Handling
LOG_LEVEL=info
ERROR_MONITORING_ENABLED=true
```

## 📈 Performance Characteristics

| Metric | Value |
|--------|-------|
| **Data Collection** | Real-time with centralized error handling |
| **Active ATC Positions** | 200+ concurrent |
| **Active Flights** | 30+ concurrent |
| **Write Throughput** | 10,000+ records/sec |
| **Memory Usage** | 2GB with compression |
| **Error Handling** | 60+ standardized error blocks |
| **API Endpoints** | 100% error-handled |

## 🗄️ Database Support

### PostgreSQL (Production)
- Network-based storage
- Advanced partitioning
- Connection pooling
- WAL compression
- Centralized error handling

### SQLite (Development)
- File-based storage
- WAL mode for concurrency
- Optimized for SSD wear reduction

## 📚 Documentation

### Architecture Documentation
- [Architecture Overview](ARCHITECTURE_OVERVIEW.md) - Complete system architecture
- [Architecture Changes Summary](ARCHITECTURE_CHANGES_SUMMARY.md) - Recent architectural changes

### Migration Guides
- [PostgreSQL Migration](docs/migration/POSTGRESQL_MIGRATION_README.md)
- [Migration Summary](docs/migration/MIGRATION_SUMMARY.md)

### Optimization Guides
- [Write Optimization](docs/optimization/WRITE_OPTIMIZATION_GUIDE.md)
- [Performance Optimizations](docs/optimization/PERFORMANCE_OPTIMIZATIONS.md)
- [SSD Optimization](docs/optimization/POSTGRESQL_SSD_OPTIMIZATION.md)

### Analysis Tools
- [Data Integrity Report](docs/analysis/DATA_INTEGRITY_REPORT.md)
- [Database Analysis](docs/analysis/analyze_database.py)

## 🛠️ Scripts

### Migration Scripts
- `scripts/migrate_to_postgresql.py` - Full PostgreSQL migration
- `scripts/setup_postgresql.py` - PostgreSQL installation
- `scripts/migrate_windows.py` - Windows-specific migration

### Utility Scripts
- `scripts/ssd_optimization.py` - SSD wear optimization
- `scripts/database_migration.py` - Database migration utilities

### Database Tools
- `tools/create_optimized_tables.sql` - Optimized table schemas
- `tools/postgresql.conf` - PostgreSQL configuration

## 🔍 Monitoring & Observability

### Grafana Dashboards
- **VATSIM Overview**: General VATSIM network statistics
- **Traffic Analysis**: Real-time traffic patterns and movements
- **Performance Metrics**: System performance and optimization
- **Error Monitoring**: Centralized error tracking and analytics

### API Endpoints
- `GET /api/status` - System status and health
- `GET /api/network/status` - Network statistics
- `GET /api/atc-positions` - Active ATC positions
- `GET /api/flights` - Active flights
- `GET /api/traffic/summary/{region}` - Traffic summary
- `GET /api/traffic/movements/{airport}` - Airport movements
- `GET /api/performance/metrics` - Performance metrics
- `GET /api/database/status` - Database status

### Error Monitoring
- **Centralized Error Tracking**: All errors logged with rich context
- **Error Analytics**: Error patterns and impact analysis
- **Performance Impact**: Error monitoring with performance metrics
- **Automated Alerting**: Error-based alerting system

## 🚀 Deployment

### Development
```bash
# Docker Compose (recommended)
docker-compose up -d

# Manual
python run.py
```

### Production
```bash
# Use PostgreSQL for production
DATABASE_URL=postgresql://user:pass@localhost/vatsim_data
docker-compose up -d
```

## 📊 Data Integrity

The system includes comprehensive data integrity checks:
- Real-time data validation
- Automated backup creation
- Data freshness monitoring
- Consistency verification
- Centralized error handling
- Grafana monitoring dashboards

## 🔧 Troubleshooting

### Common Issues
1. **API Errors**: Check centralized error logs
2. **Database Issues**: Monitor database status endpoint
3. **Performance**: Check performance metrics endpoint
4. **Grafana Access**: Verify API connectivity

### Logs
- Application logs: `logs/`
- Error logs: Centralized error monitoring
- Performance logs: Monitor API endpoints
- Grafana logs: `docker-compose logs grafana`

## 🎯 Architecture Benefits

### Operational Excellence
- **Centralized Error Handling**: Consistent error management across all services
- **Rich Error Context**: Comprehensive error logging for debugging
- **Automatic Error Recovery**: Circuit breakers and retry mechanisms
- **Comprehensive Monitoring**: Error tracking and performance analytics

### Developer Experience
- **API-First Design**: Clean REST APIs for all functionality
- **Simplified Error Management**: Decorator-based error handling
- **Consistent Patterns**: Standardized error handling across codebase
- **Better Debugging**: Rich error context and logging

### System Reliability
- **Fault Tolerance**: Circuit breakers and graceful degradation
- **Error Analytics**: Error tracking and reporting
- **Performance Optimization**: Memory and database optimization
- **Scalability**: Microservices-oriented architecture

## 📄 License

This project is designed for VATSIM data collection and analysis.

## 🤝 Contributing

1. Follow the API-first design principles
2. Use centralized error handling patterns
3. Update documentation
4. Monitor performance impact
5. Test Grafana integration

## 📚 Additional Resources

- **Grafana Setup**: See `grafana/README.md` for detailed Grafana configuration
- **API Documentation**: http://localhost:8001/docs
- **Architecture Documentation**: See `ARCHITECTURE_OVERVIEW.md`

---

**Optimized for high-performance data collection with centralized error handling and comprehensive observability.**
