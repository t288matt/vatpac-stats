# 🚀 VATSIM Data Collection System - Production Deployment

## 📋 Production Deployment Guide

This guide will help you deploy the VATSIM Data Collection System to production using Docker Compose.

### 🎯 What You'll Get

- **Production API** accessible via server IP
- **Real-time VATSIM data collection** every 60 seconds
- **Grafana monitoring dashboards** with comprehensive metrics
- **PostgreSQL database** with optimized configuration
- **Geographic filtering** for Australian airspace
- **Flight summary system** with sector tracking
- **Production-optimized performance** settings

### **Current System Features**
- ✅ **Geographic Boundary Filter**: Australian airspace polygon filtering
- ✅ **Flight Summary System**: Automatic flight completion tracking
- ✅ **Sector Tracking**: Real-time sector occupancy monitoring
- ✅ **Performance Optimized**: Database connection pooling and caching
- ✅ **Monitoring Ready**: Grafana dashboards with health metrics

## 🚀 Deployment

### Prerequisites

1. **Linux server** (Ubuntu 20.04+ or CentOS 8+) with:
   - 4+ GB RAM (8GB+ recommended)
   - 50+ GB SSD storage
   - Docker and Docker Compose installed
   - Ports 8001 and 3050 open in firewall

2. **Server IP address**

### Step 1: Prepare Your Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose (if not already installed)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in to apply docker group changes
```

### Step 2: Clone and Deploy

```bash
# Clone the repository
git clone https://github.com/yourusername/vatsim-data.git
cd vatsim-data

# Deploy the system
docker-compose up -d --build
```

The system will:
1. ✅ Start PostgreSQL database with optimized configuration
2. ✅ Build and start the main application
3. ✅ Start Grafana monitoring
4. ✅ Configure all services with production settings

### Step 3: Access Your System

Access directly via your server IP:

```
# Your services will be available at:
API: http://YOUR_SERVER_IP:8001
Grafana: http://YOUR_SERVER_IP:3050
```

## 🔧 Configuration

### Environment Variables

The system uses the following key configuration in `docker-compose.yml`:

```yaml
# VATSIM Data Collection
VATSIM_POLLING_INTERVAL: 60        # Data fetch interval (seconds)
WRITE_TO_DISK_INTERVAL: 30         # Data persistence interval (seconds)

# Database Performance
DATABASE_POOL_SIZE: 20              # Connection pool size
DATABASE_MAX_OVERFLOW: 40          # Max overflow connections

# Flight Filtering
ENABLE_BOUNDARY_FILTER: "true"     # Australian airspace filtering
BOUNDARY_DATA_PATH: "australian_airspace_polygon.json"

# Flight Summary System
FLIGHT_SUMMARY_ENABLED: "true"     # Enable flight summaries
FLIGHT_COMPLETION_HOURS: 14        # Hours to mark flight complete
SECTOR_TRACKING_ENABLED: "true"    # Real-time sector tracking
```

### Customizing Configuration

To modify settings, edit the `docker-compose.yml` file and restart:

```bash
# Edit configuration
nano docker-compose.yml

# Restart with new configuration
docker-compose down
docker-compose up -d --build
```

## 🌐 Access Your Deployment

After successful deployment, access your services:

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | `http://YOUR_SERVER_IP:8001` | No auth by default |
| **Grafana** | `http://YOUR_SERVER_IP:3050` | admin / admin |

### 🔑 Important URLs

```bash
# API Health Check
http://YOUR_SERVER_IP:8001/api/status

# API Documentation  
http://YOUR_SERVER_IP:8001/docs

# Flight Data
http://YOUR_SERVER_IP:8001/api/flights

# Controllers
http://YOUR_SERVER_IP:8001/api/controllers

# Filter Status
http://YOUR_SERVER_IP:8001/api/filter/flight/status

# Flight Summaries
http://YOUR_SERVER_IP:8001/api/flights/summaries
```

## 🔒 Security Features

### ✅ API Security
- **CORS protection** configured
- **Request size limits** enforced
- **Rate limiting** via application logic

### ✅ Database Security
- **Internal network only** (no external exposure)
- **Connection encryption** enabled
- **Optimized configuration** for production

### ✅ Container Security
- **Non-root user** in containers
- **Resource limits** configured
- **Container isolation**

## 📊 Monitoring & Dashboards

### Grafana Dashboards

1. **Flight Performance Metrics**
   - Real-time flight tracking
   - Performance analytics
   - Route analysis

2. **ATC Service Coverage**
   - Controller statistics
   - Sector coverage metrics
   - Service availability

3. **Comprehensive Health Monitoring**
   - System performance
   - Database metrics
   - API response times

### Health Checks

```bash
# Container health
docker-compose ps

# API health
curl http://YOUR_SERVER_IP:8001/api/status

# Database health
docker exec vatsim_postgres pg_isready -U vatsim_user

# System metrics
docker stats
```

## 💾 Backup Strategy

### Manual Backup Commands

```bash
# Create immediate backup
docker exec vatsim_postgres pg_dump -U vatsim_user vatsim_data > backup_$(date +%Y%m%d_%H%M%S).sql

# List available backups  
ls -la *.sql

# Restore from backup
docker exec -i vatsim_postgres psql -U vatsim_user vatsim_data < backup_file.sql
```

### Automated Backup Setup

Create a cron job for daily backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/vatsim-data && docker exec vatsim_postgres pg_dump -U vatsim_user vatsim_data > backups/backup_$(date +\%Y\%m\%d).sql
```

## 🔧 Configuration Options

### Flight Filtering

```yaml
# Geographic boundary filter (enabled by default)
ENABLE_BOUNDARY_FILTER: "true"
BOUNDARY_DATA_PATH: "australian_airspace_polygon.json"

# Flight summary system
FLIGHT_SUMMARY_ENABLED: "true"
SECTOR_TRACKING_ENABLED: "true"
```

### Performance Tuning

```yaml
# Memory allocation
MEMORY_LIMIT_MB: 2048

# Database connections
DATABASE_POOL_SIZE: 20
DATABASE_MAX_OVERFLOW: 40

# Data collection intervals
VATSIM_POLLING_INTERVAL: 60
WRITE_TO_DISK_INTERVAL: 30
```

## 🚨 Troubleshooting

### Common Issues

**1. API Not Responding**
```bash
# Check application logs
docker logs vatsim_app --tail 50

# Restart application
docker-compose restart app
```

**2. Database Connection Issues**
```bash
# Check database logs
docker logs vatsim_postgres --tail 20

# Test database connection
docker exec vatsim_postgres pg_isready -U vatsim_user
```

**3. No VATSIM Data**
```bash
# Check data ingestion
docker logs vatsim_app | grep -i vatsim

# Verify network connectivity
docker exec vatsim_app curl -I https://data.vatsim.net/v3/vatsim-data.json
```

**4. Grafana Not Accessible**
```bash
# Check Grafana logs
docker logs vatsim_grafana --tail 20

# Restart Grafana
docker-compose restart grafana
```

### Log Locations

```bash
# Application logs
docker logs vatsim_app

# Database logs
docker logs vatsim_postgres

# Grafana logs
docker logs vatsim_grafana

# System logs
/var/log/syslog
```

## 📈 Performance Monitoring

### Key Metrics to Monitor

1. **API Response Times** (<200ms average)
2. **Database Query Performance** (<50ms average)
3. **Memory Usage** (<80% of allocated)
4. **Disk Space** (>20% free)
5. **VATSIM Data Freshness** (<60 seconds)

### Monitoring Commands

```bash
# System resource usage
docker stats

# API performance
curl -w "@curl-format.txt" -s http://YOUR_SERVER_IP:8001/api/status

# Database performance
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT * FROM pg_stat_activity;"
```

## 🔄 Updates & Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Check backup integrity
2. **Monthly**: Review application logs
3. **Quarterly**: Update Docker images
4. **As needed**: Monitor system performance

### Update Procedure

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Verify update
curl http://YOUR_SERVER_IP:8001/api/status
```

## 📞 Support & Documentation

### Additional Resources

- **[API Documentation](docs/API_REFERENCE.md)**: Complete API reference
- **[Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md)**: System architecture
- **[Configuration Guide](docs/CONFIGURATION.md)**: Environment variables
- **[Geographic Filtering](docs/GEOGRAPHIC_BOUNDARY_FILTER_CONFIG.md)**: Advanced filtering

### Getting Help

1. Check the troubleshooting section above
2. Review container logs for errors
3. Verify firewall configuration
4. Test network connectivity to VATSIM API

---

## ✅ Production Readiness Checklist

### Pre-Deployment
- [ ] Server meets minimum requirements
- [ ] Docker and Docker Compose installed
- [ ] Firewall ports 8001/3050 open
- [ ] Sufficient disk space available

### Post-Deployment
- [ ] All containers healthy and running
- [ ] API responding on port 8001
- [ ] Grafana dashboards accessible on port 3050
- [ ] VATSIM data ingestion working
- [ ] Database connection successful
- [ ] Geographic filtering active
- [ ] Flight summary system operational

**🎉 Congratulations! Your VATSIM Data Collection System is now running in production!**

---

*Last Updated: 2025-01-15*
*Version: Production Ready v3.0*
