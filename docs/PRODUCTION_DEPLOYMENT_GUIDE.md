# 🚀 Production Deployment Guide

## 🎯 Overview

This guide provides comprehensive instructions for deploying the VATSIM Data Collection System to a production environment with proper security, monitoring, and operational considerations.

## ⚠️ Prerequisites

### **System Requirements:**
- **CPU**: 4+ cores (8+ recommended)
- **Memory**: 8GB RAM minimum (16GB+ recommended)
- **Storage**: 50GB+ SSD storage
- **Network**: High-bandwidth internet connection
- **OS**: Linux (Ubuntu 20.04+ or CentOS 8+)

### **Software Requirements:**
- Docker Engine 20.10+
- Docker Compose 2.0+
- SSL certificates (Let's Encrypt recommended)
- Domain name with DNS configuration
- Firewall configuration capability

## 🔒 Security Configuration

### **1. SSL/TLS Setup**

#### **Option A: Let's Encrypt (Recommended)**
```bash
# Install Certbot
sudo apt update
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d api.yourdomain.com -d grafana.yourdomain.com

# Certificates will be at:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

#### **Option B: Self-Signed (Development Only)**
```bash
# Generate self-signed certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /opt/vatsim/certs/key.pem \
  -out /opt/vatsim/certs/cert.pem \
  -subj "/C=AU/ST=State/L=City/O=Organization/CN=yourdomain.com"
```

### **2. Environment Security**

Create a production environment file:

```bash
# Create secure environment file
sudo mkdir -p /opt/vatsim/config
sudo touch /opt/vatsim/config/production.env
sudo chmod 600 /opt/vatsim/config/production.env
```

**Production Environment Variables:**
```bash
# /opt/vatsim/config/production.env

# === SECURITY CONFIGURATION ===
PRODUCTION_MODE=true
API_KEY_REQUIRED=true
API_RATE_LIMIT_ENABLED=true
SSL_ENABLED=true
SSL_CERT_PATH=/certs/fullchain.pem
SSL_KEY_PATH=/certs/privkey.pem

# === AUTHENTICATION ===
JWT_SECRET_KEY=your_super_secure_jwt_secret_key_here_64_chars_minimum
API_MASTER_KEY=your_api_master_key_here
GRAFANA_ADMIN_PASSWORD=your_secure_grafana_password_here

# === DATABASE SECURITY ===
POSTGRES_PASSWORD=your_secure_database_password_here
POSTGRES_USER=vatsim_prod_user
DATABASE_URL=postgresql://vatsim_prod_user:your_secure_database_password_here@postgres:5432/vatsim_data

# === CORS & API SECURITY ===
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
API_RATE_LIMIT_PER_MINUTE=100
API_MAX_CONCURRENT_REQUESTS=50

# === MONITORING & LOGGING ===
ERROR_MONITORING_ENABLED=true
PERFORMANCE_MONITORING_ENABLED=true
LOG_LEVEL=INFO
SENTRY_DSN=your_sentry_dsn_here

# === BACKUP CONFIGURATION ===
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=your-backup-bucket
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# === CORE APPLICATION SETTINGS ===
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
REDIS_URL=redis://redis:6379
MEMORY_LIMIT_MB=4096
BATCH_SIZE_THRESHOLD=15000

# === VATSIM DATA COLLECTION ===
VATSIM_POLLING_INTERVAL=10

WRITE_TO_DISK_INTERVAL=15
VATSIM_API_TIMEOUT=30
VATSIM_API_RETRY_ATTEMPTS=3

# === FLIGHT FILTERING ===
FLIGHT_FILTER_ENABLED=true
FLIGHT_FILTER_LOG_LEVEL=INFO
ENABLE_BOUNDARY_FILTER=false
BOUNDARY_DATA_PATH=australian_airspace_polygon.json
BOUNDARY_FILTER_LOG_LEVEL=INFO
BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=10.0


```

## 🐳 Production Docker Configuration

### **Create Production Docker Compose:**

```yaml
# /opt/vatsim/docker-compose.prod.yml
version: '3.8'

services:
  # Reverse Proxy with SSL Termination
  traefik:
    image: traefik:v2.10
    container_name: vatsim_traefik
    command:
      - "--api.dashboard=true"
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--log.level=INFO"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /opt/vatsim/letsencrypt:/letsencrypt
    restart: unless-stopped
    networks:
      - vatsim_network

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: vatsim_postgres
    env_file:
      - /opt/vatsim/config/production.env
    environment:
      POSTGRES_DB: vatsim_data
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - /opt/vatsim/config/postgresql.conf:/etc/postgresql/postgresql.conf
      - /opt/vatsim/database/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $POSTGRES_USER -d vatsim_data"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - vatsim_network

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: vatsim_redis
    command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru --save 60 1000
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - vatsim_network

  # Main Application
  app:
    build:
      context: /opt/vatsim/app
      dockerfile: Dockerfile
    container_name: vatsim_app
    env_file:
      - /opt/vatsim/config/production.env
    volumes:
      - /opt/vatsim/logs:/app/logs:rw
      - /opt/vatsim/data/australian_airspace_polygon.json:/app/australian_airspace_polygon.json:ro
      - /opt/vatsim/certs:/certs:ro
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    networks:
      - vatsim_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.vatsim-api.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.vatsim-api.entrypoints=websecure"
      - "traefik.http.routers.vatsim-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.vatsim-api.loadbalancer.server.port=8001"

  # Grafana Monitoring
  grafana:
    image: grafana/grafana:10.2.0
    container_name: vatsim_grafana
    env_file:
      - /opt/vatsim/config/production.env
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_USERS_ALLOW_SIGN_UP: false
      GF_INSTALL_PLUGINS: grafana-clock-panel,grafana-simple-json-datasource
      GF_SERVER_ROOT_URL: https://grafana.yourdomain.com
      GF_SERVER_SERVE_FROM_SUB_PATH: true
    volumes:
      - /opt/vatsim/grafana/provisioning:/etc/grafana/provisioning:ro
      - /opt/vatsim/grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    depends_on:
      app:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - vatsim_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.vatsim-grafana.rule=Host(`grafana.yourdomain.com`)"
      - "traefik.http.routers.vatsim-grafana.entrypoints=websecure"
      - "traefik.http.routers.vatsim-grafana.tls.certresolver=letsencrypt"
      - "traefik.http.services.vatsim-grafana.loadbalancer.server.port=3000"

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  grafana_data:
    driver: local

networks:
  vatsim_network:
    driver: bridge
```

## 🔥 Firewall Configuration

### **UFW Configuration (Ubuntu):**
```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow specific IPs for database access (if needed)
sudo ufw allow from YOUR_ADMIN_IP to any port 5432

# Check status
sudo ufw status verbose
```

## 📊 Monitoring & Alerting

### **1. Health Check Script:**
```bash
#!/bin/bash
# /opt/vatsim/scripts/health_check.sh

API_URL="https://api.yourdomain.com"
API_KEY="your_api_key_here"

# Check API health
response=$(curl -s -H "Authorization: Bearer $API_KEY" "$API_URL/api/status")
if [[ $? -ne 0 ]]; then
    echo "CRITICAL: API is down"
    # Send alert (email, Slack, etc.)
    exit 1
fi

# Check data freshness
last_update=$(echo $response | jq -r '.timestamp')
current_time=$(date -u +%s)
last_update_time=$(date -d "$last_update" +%s)
diff=$((current_time - last_update_time))

if [[ $diff -gt 300 ]]; then  # 5 minutes
    echo "WARNING: Data is stale (${diff}s old)"
    # Send warning alert
    exit 1
fi

echo "OK: System healthy"
exit 0
```

### **2. Log Rotation:**
```bash
# /etc/logrotate.d/vatsim
/opt/vatsim/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    postrotate
        docker kill -s USR1 vatsim_app
    endscript
}
```

## 💾 Backup Strategy

### **1. Database Backup Script:**
```bash
#!/bin/bash
# /opt/vatsim/scripts/backup_database.sh

BACKUP_DIR="/opt/vatsim/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="vatsim_backup_$DATE.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker exec vatsim_postgres pg_dump -U vatsim_prod_user vatsim_data | gzip > "$BACKUP_DIR/$BACKUP_FILE"

# Upload to S3 (if configured)
if [[ -n "$AWS_ACCESS_KEY_ID" ]]; then
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://your-backup-bucket/database/"
fi

# Clean old local backups (keep 7 days)
find $BACKUP_DIR -name "vatsim_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

### **2. Automated Backup Cron:**
```bash
# Add to crontab
0 2 * * * /opt/vatsim/scripts/backup_database.sh >> /opt/vatsim/logs/backup.log 2>&1
```

## 🚀 Deployment Steps

### **1. Initial Setup:**
```bash
# Create directory structure
sudo mkdir -p /opt/vatsim/{app,config,logs,backups,scripts,certs}

# Clone repository
cd /opt/vatsim
sudo git clone https://github.com/yourusername/vatsim-data.git app

# Set permissions
sudo chown -R $USER:docker /opt/vatsim
sudo chmod -R 755 /opt/vatsim
sudo chmod 600 /opt/vatsim/config/production.env
```

### **2. Deploy Application:**
```bash
cd /opt/vatsim/app

# Build and start services
docker-compose -f docker-compose.prod.yml up -d --build

# Verify deployment
docker-compose -f docker-compose.prod.yml ps
```

### **3. Verify Deployment:**
```bash
# Check all services are healthy
docker-compose -f docker-compose.prod.yml ps

# Test API endpoints
curl -H "Authorization: Bearer $API_KEY" https://api.yourdomain.com/api/status
curl https://grafana.yourdomain.com

# Check logs
docker logs vatsim_app --tail 50
docker logs vatsim_postgres --tail 20
```

## 📋 Production Checklist

### **Pre-Deployment:**
- [ ] SSL certificates configured and tested
- [ ] All passwords changed from defaults
- [ ] Firewall rules configured
- [ ] DNS records configured
- [ ] Backup strategy implemented
- [ ] Monitoring alerts configured
- [ ] Log rotation configured

### **Post-Deployment:**
- [ ] All services healthy and running
- [ ] API endpoints responding with authentication
- [ ] VATSIM data ingestion working
- [ ] Grafana dashboards accessible
- [ ] Backup script tested
- [ ] Health check script working
- [ ] SSL certificates valid and auto-renewing

## 🔍 Troubleshooting

### **Common Issues:**

1. **SSL Certificate Issues:**
   ```bash
   # Check certificate status
   sudo certbot certificates
   
   # Renew certificates
   sudo certbot renew --dry-run
   ```

2. **Database Connection Issues:**
   ```bash
   # Check database logs
   docker logs vatsim_postgres
   
   # Test database connection
   docker exec vatsim_postgres psql -U vatsim_prod_user -d vatsim_data -c "SELECT 1;"
   ```

3. **API Authentication Issues:**
   ```bash
   # Check API logs
   docker logs vatsim_app | grep -i auth
   
   # Verify API key
   curl -H "Authorization: Bearer $API_KEY" https://api.yourdomain.com/api/status
   ```

## 📞 Support & Maintenance

### **Regular Maintenance Tasks:**
- Monitor disk space usage
- Check backup integrity weekly
- Update SSL certificates (automated with Let's Encrypt)
- Monitor application logs for errors
- Review security logs monthly
- Update Docker images quarterly

### **Performance Monitoring:**
- API response times
- Database query performance
- Memory and CPU usage
- Network bandwidth utilization
- Error rates and types

---

**🎯 Result**: A secure, scalable, production-ready VATSIM data collection system with comprehensive monitoring, backup, and security measures.

**📅 Last Updated**: 2025-08-09  
**🔄 Status**: Production deployment guide complete  
**🚀 Ready for Production**: Yes (follow all checklist items)
