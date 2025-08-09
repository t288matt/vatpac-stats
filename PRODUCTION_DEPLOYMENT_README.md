# 🚀 VATSIM Data Collection System - Production Deployment

## 📋 Simple Production Deployment Guide

This guide will help you deploy the VATSIM Data Collection System to production using the existing docker-compose.yml with production overrides.

### 🎯 What You'll Get

- **Production API** accessible via server IP
- **Real-time VATSIM data collection** every 10 seconds
- **Grafana monitoring dashboards** with traffic analytics
- **Automatic database backups** capability
- **Geographic filtering** for Australian airspace
- **Production-optimized performance** settings

## 🚀 One-Command Deployment

### Prerequisites

1. **Linux server** (Ubuntu 20.04+ or CentOS 8+) with:
   - 4+ GB RAM (8GB+ recommended)
   - 50+ GB SSD storage
   - Docker and Docker Compose installed
   - Ports 80 and 443 open in firewall

2. **Domain name** with DNS control
3. **Server IP address**

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

# Run the simple deployment script
chmod +x scripts/simple-deploy.sh
./scripts/simple-deploy.sh
```

The script will:
1. ✅ Check all prerequisites
2. ✅ Ask for your server IP
3. ✅ Generate secure passwords automatically
4. ✅ Create production environment overrides
5. ✅ Configure firewall rules
6. ✅ Deploy using existing docker-compose.yml
7. ✅ Verify deployment health

### Step 3: Access Your System

No DNS configuration needed! Access directly via your server IP:

```
# Your services will be available at:
API: http://YOUR_SERVER_IP:8001
Grafana: http://YOUR_SERVER_IP:3050
```

## 🔧 Manual Deployment (Alternative)

If you prefer manual control over the deployment:

### 1. Create Environment File

```bash
# Copy template and customize
cp production-env-example.txt .env.production

# Edit with your settings
nano .env.production
```

**Required Changes:**
- `POSTGRES_PASSWORD`: Secure database password
- `GRAFANA_ADMIN_PASSWORD`: Secure Grafana password

### 2. Deploy Services

```bash
# Start production deployment using existing docker-compose.yml
docker-compose --env-file .env.production up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Verify Deployment

```bash
# Test API
curl http://YOUR_SERVER_IP:8001/api/status

# Test Grafana
curl http://YOUR_SERVER_IP:3050
```

## 🌐 Access Your Deployment

After successful deployment, access your services:

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | `http://YOUR_SERVER_IP:8001` | No auth by default |
| **Grafana** | `http://YOUR_SERVER_IP:3050` | admin / [generated password] |

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
```

## 🔒 Security Features

### ✅ Automatic SSL/TLS
- **Let's Encrypt certificates** automatically generated
- **HTTPS redirect** for all traffic
- **Security headers** configured
- **Certificate auto-renewal**

### ✅ API Security
- **API key authentication** required
- **Rate limiting** (100 requests/minute)
- **CORS protection** configured
- **Request size limits**

### ✅ Database Security
- **Secure passwords** auto-generated
- **No external exposure** (internal network only)
- **Connection encryption**
- **Regular backups**

### ✅ Infrastructure Security
- **Reverse proxy** (Traefik) with SSL termination
- **Container isolation**
- **Non-root user** in containers
- **Firewall configuration**

## 📊 Monitoring & Dashboards

### Grafana Dashboards

1. **Flight Tracking Dashboard**
   - Real-time flight positions
   - Traffic density maps
   - Route analysis

2. **Network Statistics**
   - VATSIM network health
   - Connection statistics
   - Data freshness metrics

3. **System Performance**
   - API response times
   - Database performance
   - Memory and CPU usage

### Health Checks

```bash
# Container health
docker-compose -f docker-compose.prod.yml ps

# API health
curl https://api.yourdomain.com/api/status

# Database health
curl https://api.yourdomain.com/api/database/status

# System metrics
curl https://api.yourdomain.com/api/performance/metrics
```

## 💾 Backup Strategy

### Automatic Daily Backups

The system includes automated backup with:
- **Daily PostgreSQL dumps** at 2 AM UTC
- **30-day local retention**
- **Optional S3 upload** for off-site storage
- **Backup integrity verification**
- **Automated cleanup** of old backups

### Manual Backup Commands

```bash
# Create immediate backup
./scripts/backup-database.sh

# Test backup system
./scripts/backup-database.sh --test

# List available backups  
./scripts/backup-database.sh --list

# Restore from backup
./scripts/backup-database.sh --restore /path/to/backup.sql.gz
```

### S3 Backup Configuration

Add to your `.env.production`:

```bash
BACKUP_S3_BUCKET=your-vatsim-backup-bucket
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

## 🔧 Configuration Options

### Flight Filtering

```bash
# Australian airport filter (enabled by default)
FLIGHT_FILTER_ENABLED=true

# Geographic boundary filter (optional)
ENABLE_BOUNDARY_FILTER=true
BOUNDARY_DATA_PATH=australian_airspace_polygon.json
```

### Performance Tuning

```bash
# Memory allocation
MEMORY_LIMIT_MB=4096

# Database connections
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Data collection intervals
VATSIM_POLLING_INTERVAL=10
WRITE_TO_DISK_INTERVAL=15
```



## 🚨 Troubleshooting

### Common Issues

**1. SSL Certificate Issues**
```bash
# Check certificate status
docker logs vatsim_traefik | grep -i cert

# Force certificate renewal
docker-compose restart traefik
```

**2. API Not Responding**
```bash
# Check application logs
docker logs vatsim_app --tail 50

# Restart application
docker-compose restart app
```

**3. Database Connection Issues**
```bash
# Check database logs
docker logs vatsim_postgres --tail 20

# Test database connection
docker exec vatsim_postgres pg_isready -U vatsim_prod_user
```

**4. No VATSIM Data**
```bash
# Check data ingestion
docker logs vatsim_app | grep -i vatsim

# Verify network connectivity
docker exec vatsim_app curl -I https://data.vatsim.net/v3/vatsim-data.json
```

### Log Locations

```bash
# Application logs
/opt/vatsim/logs/

# Container logs
docker-compose -f docker-compose.prod.yml logs [service_name]

# System logs
/var/log/syslog
```

## 📈 Performance Monitoring

### Key Metrics to Monitor

1. **API Response Times** (<200ms average)
2. **Database Query Performance** (<50ms average)
3. **Memory Usage** (<80% of allocated)
4. **Disk Space** (>20% free)
5. **VATSIM Data Freshness** (<30 seconds)

### Monitoring Commands

```bash
# System resource usage
docker stats

# API performance
curl -w "@curl-format.txt" -s https://api.yourdomain.com/api/status

# Database performance
docker exec vatsim_postgres psql -U vatsim_prod_user -d vatsim_data -c "SELECT * FROM pg_stat_activity;"
```

## 🔄 Updates & Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Check backup integrity
2. **Monthly**: Review security logs
3. **Quarterly**: Update Docker images
4. **Annually**: Rotate SSL certificates (automatic)

### Update Procedure

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Verify update
curl https://api.yourdomain.com/api/status
```

## 📞 Support & Documentation

### Additional Resources

- **[API Documentation](docs/API_REFERENCE.md)**: Complete API reference
- **[Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md)**: System architecture
- **[Configuration Guide](docs/CONFIGURATION.md)**: Environment variables
- **[Geographic Filtering](docs/GEOGRAPHIC_BOUNDARY_FILTER_PLAN.md)**: Advanced filtering

### Getting Help

1. Check the troubleshooting section above
2. Review container logs for errors
3. Verify DNS and firewall configuration
4. Test network connectivity to VATSIM API

---

## ✅ Production Readiness Checklist

### Pre-Deployment
- [ ] Server meets minimum requirements
- [ ] Docker and Docker Compose installed
- [ ] Domain name configured with DNS
- [ ] Firewall ports 80/443 open
- [ ] SSL email configured for Let's Encrypt

### Post-Deployment
- [ ] All containers healthy and running
- [ ] API responding with HTTPS
- [ ] Grafana dashboards accessible
- [ ] VATSIM data ingestion working
- [ ] Backup script tested
- [ ] Monitoring alerts configured
- [ ] DNS propagation complete
- [ ] SSL certificates valid

**🎉 Congratulations! Your VATSIM Data Collection System is now running in production!**

---

*Last Updated: 2025-01-15*
*Version: Production Ready v2.0*
