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
git clone <repository-url>
cd vatsim-data
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
  "timestamp": "2025-08-06T06:35:09.481393",
  "atc_positions_count": 0,
  "flights_count": 0,
  "airports_count": 0,
  "movements_count": 0,
  "data_freshness": "real-time",
  "cache_status": "enabled"
}
```

## 🔧 What Happens Automatically

### **Database Setup:**
1. **PostgreSQL Container**: Starts with empty database
2. **Init Script**: `database/init.sql` runs automatically
3. **Tables Created**: All 12 required tables with proper fields
4. **Indexes Created**: Performance indexes for queries
5. **Triggers Created**: Automatic `updated_at` field updates
6. **Default Data**: System configuration inserted

### **Application Setup:**
1. **Schema Validation**: App checks database on startup
2. **Auto-Fix**: Missing tables/fields created automatically
3. **Health Checks**: All services verified
4. **Background Services**: Data ingestion starts automatically

## 📊 Database Schema Created

### **Tables Created (13 total):**
- `controllers` - ATC controller positions with VATSIM API fields
- `sectors` - Airspace sector definitions
- `flights` - Real-time flight data with complete VATSIM API mapping
- `traffic_movements` - Airport arrival/departure tracking
- `flight_summaries` - Historical flight data
- `movement_summaries` - Hourly movement statistics
- `airport_config` - Airport configuration settings
- `airports` - Global airport database
- `movement_detection_config` - Detection algorithm settings
- `system_config` - Application configuration
- `events` - Special events and scheduling
- `transceivers` - Radio frequency and position data
- `vatsim_status` - VATSIM network status and general information

### **VATSIM API Integration:**
- ✅ **Complete 1:1 field mapping** with VATSIM API
- ✅ **Flight data fields**: cid, name, server, pilot_rating, military_rating, latitude, longitude, groundspeed, transponder, qnh_i_hg, qnh_mb, logon_time, last_updated_api
- ✅ **Flight plan fields**: flight_rules, aircraft_faa, aircraft_short, alternate, cruise_tas, planned_altitude, deptime, enroute_time, fuel_time, remarks, revision_id, assigned_transponder
- ✅ **Controller fields**: controller_id, controller_name, controller_rating, visual_range, text_atis
- ✅ **Network status**: api_version, reload, update_timestamp, connected_clients, unique_users

### **Features Included:**
- ✅ All required fields with correct data types
- ✅ Foreign key relationships
- ✅ Performance indexes (59 total indexes)
- ✅ Automatic timestamp updates
- ✅ Default configuration data
- ✅ JSONB fields for flexible data storage
- ✅ Comprehensive VATSIM API field coverage

## 🎯 Access Points

### **API Endpoints:**
- **Main API**: http://localhost:8001
- **Status Check**: http://localhost:8001/api/status
- **Health Check**: http://localhost:8001/api/health/comprehensive

### **Monitoring:**
- **Grafana Dashboard**: http://localhost:3050
- **Default Credentials**: admin/admin

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

## 📈 Performance Expectations

### **First Startup:**
- **Database Init**: 30-60 seconds
- **App Startup**: 10-20 seconds
- **Total Time**: 1-2 minutes

### **Subsequent Starts:**
- **Database**: 5-10 seconds
- **App Startup**: 5-10 seconds
- **Total Time**: 10-20 seconds

### **Resource Usage:**
- **Memory**: ~500MB total
- **CPU**: Low usage
- **Disk**: ~1GB for database

## 🚨 Important Notes

### **Data Persistence:**
- Database data stored in `./data/postgres/`
- Redis data stored in `./data/redis/`
- Grafana data stored in `./grafana/`

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
3. ✅ Database contains all required tables
4. ✅ Background data ingestion is running
5. ✅ Grafana dashboard is accessible

### **If Any Step Fails:**
- Check the troubleshooting section above
- Review container logs for specific errors
- Ensure all prerequisites are met
- Verify system resources are sufficient

---

**🎯 Result**: A fully functional VATSIM data collection system ready for production use! 