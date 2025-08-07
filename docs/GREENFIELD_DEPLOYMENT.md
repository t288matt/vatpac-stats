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

### **Application Setup:**
1. **Schema Validation**: App checks database on startup
2. **Auto-Fix**: Missing tables/fields created automatically
3. **Health Checks**: All services verified
4. **Background Services**: Data ingestion starts automatically
5. **VATSIM Integration**: Real-time data collection begins

## 📊 Database Schema Created

### **Tables Created (14 total):**
- `controllers` - ATC controller positions with VATSIM API fields
- `sectors` - Airspace sector definitions
- `flights` - Real-time flight data with complete VATSIM API mapping (FLIGHT STATUS REMOVED)
- `traffic_movements` - Airport arrival/departure tracking (FLIGHT STATUS REMOVED)
- `flight_summaries` - Historical flight data (FLIGHT STATUS REMOVED)
- `movement_summaries` - Hourly movement statistics
- `airport_config` - Airport configuration settings
- `airports` - Global airport database
- `movement_detection_config` - Detection algorithm settings
- `system_config` - Application configuration
- `events` - Special events and scheduling
- `transceivers` - Radio frequency and position data
- `vatsim_status` - VATSIM network status and general information
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
- ✅ **Removed from flight_summaries**: completed_at
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
- **Data retention**: Configurable via system_config
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

## 🗺️ Geographic Functionality (Future)

### **Planned Features:**
- **Polygon Detection**: Airspace boundary detection
- **Geographic Filtering**: Region-based flight filtering
- **Airspace Monitoring**: Real-time airspace utilization
- **Geographic Analytics**: Traffic pattern analysis
- **API Endpoints**: Geographic-based queries

### **Implementation Roadmap:**
- **Phase 1**: Core polygon detection (GEO_TODO.md)
- **Phase 2**: Database schema extensions
- **Phase 3**: Geographic services
- **Phase 4**: API integration
- **Phase 5**: Monitoring and analytics

---

**🎯 Result**: A fully functional VATSIM data collection system with simplified architecture, ready for production use and future geographic enhancements!

**📅 Last Updated**: 2025-08-07  
**🔄 Status**: Flight status removal complete, geographic roadmap ready  
**🚀 Ready for Deployment**: Yes 