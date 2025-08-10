# 🚀 Greenfield Deployment Guide

## 📋 Prerequisites

### **System Requirements:**
- Docker and Docker Compose installed
- At least 2GB RAM available
- 10GB free disk space
- Internet connection for Docker images

### **Network Requirements:**
- Port 8001 available for API
- Port 5432 available for PostgreSQL (optional)
- Port 6379 available for Redis (optional)
- Port 3050 available for Grafana (optional)

### **System Dependencies:**
- GEOS library for geographic calculations (included in Docker)
- Shapely library for polygon operations (included in requirements.txt)
- PostGIS extensions (optional, for advanced geographic features)

## 🎯 One-Command Deployment

### **Step 1: Clone the Repository**
```bash
git clone https://github.com/t288matt/vatpac-stats.git
cd vatpac-stats
```

### **Step 2: Start the Application**
```bash
docker-compose up -d
```

### **Step 3: Verify Deployment**
```bash
# Check if all containers are running
docker-compose ps

# Test the API
curl http://localhost:8001/api/status

# Test geographic boundary filter (if enabled)
curl http://localhost:8001/api/filter/boundary/status

# Test flight filter
curl http://localhost:8001/api/filter/flight/status
```

## ✅ Expected Results

### **Container Status:**
```bash
docker-compose ps
# Should show:
# - vatsim_postgres: Up (healthy)
# - vatsim_redis: Up (healthy)  
# - vatsim_app: Up (healthy)
# - vatsim_grafana: Up (healthy)
```

### **API Response:**
```json
{
  "status": "operational",
  "timestamp": "2025-08-07T22:19:25.707673+00:00",
  "atc_positions_count": 160,
  "flights_count": 2537,
  "airports_count": 0,
  "movements_count": 125,
  "data_freshness": "real-time",
  "cache_status": "enabled",
  "diagnostic": {
    "total_flights_in_db": 2537,
    "total_controllers_in_db": 160,
    "data_ingestion_status": "data_present"
  }
}
```

## 🔧 What Happens Automatically

### **Database Setup:**
1. **PostgreSQL Container**: Starts with empty database
2. **Init Script**: `database/init.sql` runs automatically
3. **Tables Created**: All 14 required tables with proper fields
4. **Indexes Created**: Performance indexes for queries
5. **Triggers Created**: Automatic `updated_at` field updates
6. **Default Data**: System configuration inserted
7. **GEOS Support**: Geographic calculation libraries loaded

### **Application Setup:**
1. **Schema Validation**: App checks database on startup
2. **Auto-Fix**: Missing tables/fields created automatically
3. **Health Checks**: All services verified
4. **Background Services**: Data ingestion starts automatically
5. **VATSIM Integration**: Real-time data collection begins
6. **Filter Initialization**: Flight and geographic filters configured
7. **Cache Warming**: Redis cache populated with initial data

## 📊 Database Schema Created

### **Tables Created (6 total):**
- `controllers` - ATC controller positions with VATSIM API fields
- `flights` - Real-time flight data with complete VATSIM API mapping
- `traffic_movements` - Airport arrival/departure tracking
- `airports` - Global airport database
- `transceivers` - Radio frequency and position data
- `frequency_matches` - Frequency matching events between pilots and ATC

### **VATSIM API Integration:**
- ✅ **Complete 1:1 field mapping** with VATSIM API
- ✅ **Flight data fields**: cid, name, server, pilot_rating, military_rating, latitude, longitude, groundspeed, transponder, qnh_i_hg, qnh_mb, logon_time, last_updated_api
- ✅ **Flight plan fields**: flight_rules, aircraft_faa, aircraft_short, alternate, cruise_tas, planned_altitude, deptime, enroute_time, fuel_time, remarks, revision_id, assigned_transponder
- ✅ **Controller fields**: controller_id, controller_name, controller_rating, visual_range, text_atis
- ✅ **Network status**: api_version, reload, update_timestamp, connected_clients, unique_users

### **Flight Status System Removal (COMPLETED):**
- ✅ **Removed from flights table**: status, landed_at, completed_at, completion_method, completion_confidence, pilot_disconnected_at, disconnect_method
- ✅ **Removed from traffic_movements**: flight_completion_triggered, completion_timestamp, completion_confidence
- ✅ **Removed from frequency_matches**: is_active
- ✅ **Simplified architecture**: Focus on core flight tracking without status complexity

### **Features Included:**
- ✅ All required fields with correct data types
- ✅ Foreign key relationships
- ✅ Performance indexes (65+ total indexes)
- ✅ Automatic timestamp updates
- ✅ Default configuration data
- ✅ JSONB fields for flexible data storage
- ✅ Comprehensive VATSIM API field coverage
- ✅ Simplified flight tracking (no status complexity)
- ✅ Real-time data ingestion
- ✅ Geographic functionality roadmap (GEO_TODO.md)

## 🎯 Access Points

### **API Endpoints:**
- **Main API**: http://localhost:8001
- **Status Check**: http://localhost:8001/api/status
- **Health Check**: http://localhost:8001/api/health/comprehensive
- **Flight Data**: http://localhost:8001/api/flights
- **ATC Data**: http://localhost:8001/api/controllers
- **Filter Status**: http://localhost:8001/api/filter/flight/status
- **Geographic Filter**: http://localhost:8001/api/filter/boundary/status
- **Network Status**: http://localhost:8001/api/network/status
- **Database Status**: http://localhost:8001/api/database/status

### **Monitoring:**
- **Grafana Dashboard**: http://localhost:3050
- **Default Credentials**: admin/admin
- **Dashboards**: ATC Communication Analytics, Sydney Flights, Test Dashboard

### **Database:**
- **PostgreSQL**: localhost:5432
- **Database**: vatsim_data
- **User**: vatsim_user
- **Password**: vatsim_password

## 🔍 Troubleshooting

### **If API Returns 500 Error:**
```bash
# Check app logs
docker-compose logs app

# Check database logs
docker-compose logs postgres

# Restart the application
docker-compose restart app
```

### **If Database Schema Issues:**
```bash
# The app will automatically fix schema issues
# Check logs for validation messages
docker-compose logs app | grep "schema"
```

### **If Containers Won't Start:**
```bash
# Check system resources
docker system df

# Clean up Docker
docker system prune -f

# Rebuild containers
docker-compose up -d --build
```

### **If Flight Data Not Appearing:**
```bash
# Check VATSIM API connectivity
docker-compose logs app | grep "VATSIM"

# Verify data ingestion
curl http://localhost:8001/api/status
```

## 📈 Performance Expectations

### **First Startup:**
- **Database Init**: 30-60 seconds
- **App Startup**: 10-20 seconds
- **VATSIM Data**: 1-2 minutes for first data
- **Total Time**: 2-3 minutes

### **Subsequent Starts:**
- **Database**: 5-10 seconds
- **App Startup**: 5-10 seconds
- **Data Ingestion**: Immediate
- **Total Time**: 10-20 seconds

### **Resource Usage:**
- **Memory**: ~500MB total
- **CPU**: Low usage
- **Disk**: ~1GB for database
- **Network**: Continuous VATSIM API polling

## 🚨 Important Notes

### **Data Persistence:**
- Database data stored in `./data/postgres/`
- Redis data stored in `./data/redis/`
- Grafana data stored in `./grafana/`

### **VATSIM Data:**
- **Real-time collection**: Every 10 seconds
- **Data retention**: Configurable via environment variables
- **API endpoints**: VATSIM public API
- **Coverage**: Global VATSIM network

### **Backup:**
```bash
# Backup database
docker-compose exec postgres pg_dump -U vatsim_user vatsim_data > backup.sql

# Restore database
docker-compose exec -T postgres psql -U vatsim_user vatsim_data < backup.sql
```

### **Updates:**
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up -d --build
```

## 🎉 Success Criteria

### **Deployment is Successful When:**
1. ✅ All containers show "Up (healthy)"
2. ✅ API returns 200 OK on status check
3. ✅ Database contains all required tables (14 tables)
4. ✅ Background data ingestion is running
5. ✅ Grafana dashboard is accessible
6. ✅ VATSIM data appears within 2-3 minutes
7. ✅ Flight count > 0 in API response

### **Expected Data After Deployment:**
- **Flights**: 1000-5000+ active flights
- **Controllers**: 50-200+ ATC positions
- **Real-time updates**: Every 10-15 seconds
- **Global coverage**: Multiple continents

### **If Any Step Fails:**
- Check the troubleshooting section above
- Review container logs for specific errors
- Ensure all prerequisites are met
- Verify system resources are sufficient
- Check internet connectivity for VATSIM API

## ⚙️ Environment Configuration

### **Core Environment Variables:**
```bash
# Database Configuration
DATABASE_URL=postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
REDIS_URL=redis://redis:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
API_WORKERS=4
CORS_ORIGINS=*

# VATSIM Data Collection
VATSIM_POLLING_INTERVAL=10

WRITE_TO_DISK_INTERVAL=15
VATSIM_API_TIMEOUT=30
VATSIM_API_RETRY_ATTEMPTS=3

# Flight Filtering
FLIGHT_FILTER_ENABLED=true
FLIGHT_FILTER_LOG_LEVEL=INFO

# Geographic Boundary Filtering (NEW)
ENABLE_BOUNDARY_FILTER=false
BOUNDARY_DATA_PATH=australian_airspace_polygon.json
BOUNDARY_FILTER_LOG_LEVEL=INFO
BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=10.0

# Performance Settings
MEMORY_LIMIT_MB=2048
BATCH_SIZE_THRESHOLD=10000
LOG_LEVEL=INFO
PRODUCTION_MODE=true


```

### **Production Environment Variables:**
```bash
# Security (Production Only)
API_KEY_REQUIRED=true
API_RATE_LIMIT_ENABLED=true
SSL_ENABLED=true
SSL_CERT_PATH=/certs/cert.pem
SSL_KEY_PATH=/certs/key.pem

# Monitoring (Production Only)
# Error monitoring simplified
PERFORMANCE_MONITORING_ENABLED=true
GRAFANA_ADMIN_PASSWORD=your_secure_password_here
POSTGRES_PASSWORD=your_secure_db_password_here

# Backup Configuration (Production Only)
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=your-backup-bucket
```

## 🗺️ Geographic Functionality (IMPLEMENTED)

### **Current Features:**
- ✅ **Polygon Detection**: Australian airspace boundary detection
- ✅ **Geographic Filtering**: Shapely-based point-in-polygon filtering
- ✅ **Dual Filter System**: Airport + Geographic filtering
- ✅ **Performance Monitoring**: <10ms filtering performance
- ✅ **GeoJSON Support**: Standard GeoJSON polygon format

### **Geographic Filter Configuration:**
```bash
# Enable geographic boundary filtering
ENABLE_BOUNDARY_FILTER=true
BOUNDARY_DATA_PATH=australian_airspace_polygon.json
BOUNDARY_FILTER_LOG_LEVEL=INFO
BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=10.0
```

### **Filter Combinations:**
1. **Both OFF**: All flights pass through (no filtering)
2. **Airport ON, Geographic OFF**: Only flights to/from Australian airports  
3. **Airport OFF, Geographic ON**: Only flights physically in Australian airspace
4. **Both ON**: Flights to/from Australian airports AND physically in Australian airspace

## 🔒 Production Security Considerations

### **SSL/TLS Configuration:**
```bash
# 1. Generate SSL certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /certs/key.pem -out /certs/cert.pem

# 2. Update docker-compose.yml
# Add volume mount: - /path/to/certs:/certs:ro

# 3. Configure reverse proxy (recommended)
# Use Traefik or Nginx for SSL termination
```

### **API Security:**
```bash
# Environment variables for production
API_KEY_REQUIRED=true
API_RATE_LIMIT_PER_MINUTE=60
API_CORS_ORIGINS=https://yourdomain.com
JWT_SECRET_KEY=your_jwt_secret_key_here
```

### **Database Security:**
```bash
# Change default passwords
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_USER=vatsim_prod_user

# Enable SSL for database connections
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

## 🚀 Production Deployment Checklist

### **Pre-Deployment:**
- [ ] Change all default passwords
- [ ] Configure SSL certificates
- [ ] Set up reverse proxy (Traefik/Nginx)
- [ ] Configure firewall rules
- [ ] Set up monitoring alerts
- [ ] Configure backup strategy
- [ ] Test disaster recovery procedures

### **Post-Deployment:**
- [ ] Verify all services are healthy
- [ ] Test API endpoints with authentication
- [ ] Confirm data ingestion is working
- [ ] Set up log aggregation
- [ ] Configure performance monitoring
- [ ] Test backup and restore procedures

## 📊 Production Monitoring

### **Health Checks:**
```bash
# API Health
curl -H "Authorization: Bearer $API_KEY" https://api.yourdomain.com/api/status

# Database Health  
docker exec postgres pg_isready -U vatsim_user

# Redis Health
docker exec redis redis-cli ping

# Application Logs
docker logs vatsim_app --tail 100
```

### **Performance Monitoring:**
- **CPU Usage**: Monitor container CPU usage
- **Memory Usage**: Track memory consumption patterns
- **Database Performance**: Monitor query response times
- **API Response Times**: Track endpoint performance
- **Data Ingestion Rate**: Monitor VATSIM data processing

## 💾 Backup & Recovery

### **Database Backup:**
```bash
# Daily automated backup
docker exec postgres pg_dump -U vatsim_user vatsim_data | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip -c backup_20250809.sql.gz | docker exec -i postgres psql -U vatsim_user vatsim_data
```

### **Configuration Backup:**
```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  grafana/ \
  australian_airspace_polygon.json
```

---

**🎯 Result**: A fully functional, production-ready VATSIM data collection system with comprehensive security, monitoring, and geographic filtering capabilities!

**📅 Last Updated**: 2025-08-09  
**🔄 Status**: Production-ready with geographic boundary filtering, comprehensive security, and monitoring  
**🚀 Ready for Production Deployment**: Yes (with security checklist completed) 