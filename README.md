# VATSIM Data Collection System

A real-time VATSIM data collection and traffic analysis system that processes flight data, ATC positions, and network statistics with focus on Australian airspace.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 4GB RAM available
- Internet connection for VATSIM API access

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
   - **Grafana Dashboard**: http://localhost:3050 (admin/admin)
   - **API Endpoints**: http://localhost:8001
   - **Database**: localhost:5432 (vatsim_user/vatsim_password)

## 📊 System Architecture

### Services
- **App Service**: Main application (Python/FastAPI) - VATSIM data collection and API
- **PostgreSQL**: Primary database for flight data with optimized schema
- **Redis**: Caching layer for high-performance data access
- **Grafana**: Data visualization and monitoring dashboards

### Data Flow
1. **VATSIM API** → Data Service → Memory Cache → Database
2. **10-second polling** interval for real-time updates
3. **15-second disk write** interval for SSD optimization
4. **Automatic cleanup** of old data every hour

## 🗄️ Database Schema

### Flight Table (Current State)

The flight table stores comprehensive flight data with 39 optimized columns:

| Field Category | Fields | Source | Description |
|----------------|--------|--------|-------------|
| **Primary Key** | `id` | App | Auto-generated primary key |
| **Basic Info** | `callsign`, `aircraft_type`, `departure`, `arrival`, `route` | API | Flight identification and routing |
| **Position** | `position_lat`, `position_lng`, `altitude`, `heading`, `groundspeed` | API | Real-time position data |
| **Communication** | `transponder` | API | Transponder code |
| **Flight Plan** | `flight_rules`, `aircraft_faa`, `planned_altitude`, `deptime`, etc. | API | Detailed flight plan information |
| **Pilot Info** | `cid`, `name`, `server`, `pilot_rating` | API | Pilot and network information |
| **Status** | `status` | App | Flight status management |
| **Timestamps** | `last_updated_api`, `created_at`, `updated_at` | Mixed | Data timestamps |

### Flight Status System

Flight status is managed through a lifecycle system:

| Status | Description | Trigger |
|--------|-------------|---------|
| `'active'` | Currently flying | Updated in last API call |
| `'stale'` | Recently seen but not in latest update | Not updated in last 2.5× API polling interval |
| `'completed'` | Flight finished | Automatic cleanup (1 hour) |
| `'cancelled'` | Flight cancelled | Manual/API update |
| `'unknown'` | Status unclear | Fallback/error state |

**Status Lifecycle:**
```
VATSIM API → New Flight → 'active' → (2.5× polling interval) → 'stale' → (1 hour) → 'completed'
```

**Cleanup Process:** The system automatically runs every hour to mark flights older than 1 hour as 'completed'. This prevents database bloat while preserving flight data for analytics.

**⚠️ Flight Continuity Constraint:** If a flight logs off during cruise for more than 1 hour, it will be marked as 'completed' by the cleanup process. If the pilot logs back on, it will be treated as a **new flight** rather than continuing the previous flight. This ensures data integrity but means long breaks in flight will create separate flight records.

**🔄 Stale Flight Recovery:** Flights marked as 'stale' will automatically return to 'active' status if they receive an update within the 1-hour cleanup window.

## ⚙️ Configuration

### Environment Variables

```yaml
# VATSIM Data Collection
VATSIM_POLLING_INTERVAL: 10      # API polling (seconds)
WRITE_TO_DISK_INTERVAL: 15       # Database writes (seconds)
VATSIM_CLEANUP_INTERVAL: 3600    # Data cleanup (seconds)
STALE_FLIGHT_TIMEOUT_MULTIPLIER: 2.5  # Stale timeout multiplier

# Database
DATABASE_URL: postgresql://user:pass@host:5432/db
DATABASE_POOL_SIZE: 10
DATABASE_MAX_OVERFLOW: 20

# API Configuration
API_HOST: 0.0.0.0
API_PORT: 8001
API_WORKERS: 4

# Redis Configuration
REDIS_URL: redis://redis:6379
REDIS_MAX_CONNECTIONS: 20

# Logging
LOG_LEVEL: INFO
```

## 🔌 API Endpoints

### Flight Data
- `GET /api/flights` - Get all active flights
- `GET /api/flights/{callsign}` - Get specific flight
- `GET /api/flights/status/{status}` - Get flights by status

### Network Status
- `GET /api/status` - System health and statistics
- `GET /api/controllers` - Active ATC positions
- `GET /api/transceivers` - Radio frequency data

### Analytics
- `GET /api/analytics/traffic` - Traffic movement statistics
- `GET /api/analytics/flights` - Flight summary data

## 📈 Monitoring

### Grafana Dashboards
- **Real-time Flight Tracking**: Live flight positions and status
- **Network Statistics**: VATSIM network health and activity
- **Traffic Analysis**: Airport movement patterns
- **System Performance**: Application metrics and database performance

### Health Checks
- **API Connectivity**: VATSIM API status
- **Database Health**: Connection and query performance
- **Cache Status**: Memory usage and hit rates
- **Data Flow**: Processing pipeline status

## 🛠️ Development

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd vatsim-data

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

### Database Operations
```bash
# Check database schema
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "\d flights"

# View recent flights
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT callsign, status, last_updated_api FROM flights WHERE last_updated_api IS NOT NULL ORDER BY last_updated_api DESC LIMIT 5;"

# Check status distribution
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT status, COUNT(*) FROM flights GROUP BY status;"
```

## 🔍 Troubleshooting

### Common Issues

**No Data in Dashboard**
- Check if Australian flights are available in VATSIM network
- Verify flight filter is enabled: `FLIGHT_FILTER_ENABLED: "true"`
- Monitor application logs: `docker-compose logs app --tail 20`

**Database Connection Issues**
- Ensure PostgreSQL container is healthy: `docker ps`
- Check volume persistence: `docker volume ls | grep vatsim`
- Verify named volumes are properly mounted

**Performance Issues**
- Monitor memory usage: `docker stats`
- Check Redis cache status: `docker exec vatsim_redis redis-cli ping`
- Review application logs for errors

### Data Recovery
If data loss occurs:
1. Check named volume status: `docker volume inspect vatsimdata_postgres_data`
2. Verify volume backups exist
3. Restore from backup if necessary
4. Restart services: `docker-compose restart`

## 📋 Features

- **Real-time Data Collection**: Fetches VATSIM API data every 10 seconds
- **Australian Flight Filtering**: Focuses on flights to/from Australian airports
- **Database Storage**: PostgreSQL with optimized schema for flight data
- **Caching**: Redis for high-performance data access
- **Monitoring**: Grafana dashboards for data visualization
- **API Endpoints**: RESTful API for data access
- **Clean Schema**: Optimized database design with no duplicate fields
- **Status Management**: Comprehensive flight lifecycle tracking
- **Data Integrity**: Check constraints and validation
- **Performance Optimized**: Indexed queries and bulk operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📚 Documentation

- **Flight Status System**: See `docs/FLIGHT_STATUS_SYSTEM.md` for detailed status management
- **Schema Cleanup**: See `SCHEMA_CLEANUP_SUMMARY.md` for recent optimizations
- **API Documentation**: Available at http://localhost:8001/docs when running
