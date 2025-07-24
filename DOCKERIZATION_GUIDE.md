# Dockerization Guide

## 🐳 Converting Remote Installation to Docker

This guide helps you convert your working remote installation into a Docker containerized setup.

## 📋 Prerequisites

### **Before Dockerization**
1. ✅ **Remote installation working** - Application runs successfully on remote machine
2. ✅ **Data collection verified** - VATSIM data is being collected
3. ✅ **Performance tested** - System handles expected load
4. ✅ **Dependencies documented** - All requirements identified

### **Docker Requirements**
- **Docker** installed on remote machine
- **Docker Compose** installed
- **Git** for version control
- **Disk space** for container images

## 🚀 Dockerization Steps

### **Step 1: Prepare Docker Environment**

#### **Install Docker on Remote Machine**

**macOS:**
```bash
# Install Docker Desktop
brew install --cask docker

# Start Docker Desktop
open /Applications/Docker.app
```

**Linux (Ubuntu/Debian):**
```bash
# Update package list
sudo apt update

# Install Docker
sudo apt install docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Log out and back in for group changes to take effect
```

**Verify Docker Installation:**
```bash
docker --version
docker-compose --version
```

### **Step 2: Create Dockerfile**

The Dockerfile is already created, but let's verify it's optimized:

```dockerfile
# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs backups

# Set permissions
RUN chmod 755 data logs backups

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/api/status || exit 1

# Start the application
CMD ["python", "run.py"]
```

### **Step 3: Update Docker Compose**

The `docker-compose.yml` is already optimized, but verify it matches your remote setup:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: vatsim_postgres
    environment:
      POSTGRES_DB: vatsim_data
      POSTGRES_USER: vatsim_user
      POSTGRES_PASSWORD: vatsim_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./tools/postgresql.conf:/etc/postgresql/postgresql.conf
      - ./tools/create_optimized_tables.sql:/docker-entrypoint-initdb.d/01-init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vatsim_user -d vatsim_data"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - vatsim_network

  # Redis for caching
  redis:
    image: redis:7-alpine
    container_name: vatsim_redis
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
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
    build: .
    container_name: vatsim_app
    environment:
      - DATABASE_URL=postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data
      - REDIS_URL=redis://redis:6379
      - API_HOST=0.0.0.0
      - API_PORT=8001
      - MEMORY_LIMIT_MB=2048
      - BATCH_SIZE_THRESHOLD=10000
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
    ports:
      - "8001:8001"
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
      start_period: 40s
    restart: unless-stopped
    networks:
      - vatsim_network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  vatsim_network:
    driver: bridge
```

### **Step 4: Migrate Data**

#### **Option A: Start Fresh (Recommended)**
```bash
# Stop the remote application
sudo systemctl stop vatsim-data.service  # Linux
# or
launchctl unload ~/Library/LaunchAgents/com.vatsim.data.plist  # macOS

# Start Docker containers
docker-compose up -d --build
```

#### **Option B: Migrate Existing Data**
```bash
# Backup existing data
cp atc_optimization.db backups/atc_optimization_backup.db

# Start Docker containers
docker-compose up -d --build

# Migrate data to PostgreSQL (if needed)
docker exec -it vatsim_app python scripts/migrate_to_postgresql.py
```

### **Step 5: Verify Docker Setup**

#### **Check Container Status**
```bash
# View running containers
docker-compose ps

# Check container logs
docker-compose logs app
docker-compose logs postgres
docker-compose logs redis
```

#### **Test Application**
```bash
# Test API endpoint
curl http://localhost:8001/api/status

# Test database connection
docker exec -it vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM controllers;"

# Test Redis connection
docker exec -it vatsim_redis redis-cli ping
```

#### **Access Services**
- **Dashboard**: http://localhost:8001/frontend/index.html
- **API Docs**: http://localhost:8001/docs
- **API Status**: http://localhost:8001/api/status

## 🔧 Docker Optimization

### **Performance Optimizations**

#### **Multi-stage Build**
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
EXPOSE 8001
CMD ["python", "run.py"]
```

#### **Resource Limits**
```yaml
# Add to docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### **Security Hardening**

#### **Non-root User**
```dockerfile
# Add to Dockerfile
RUN useradd -m -u 1000 vatsim
USER vatsim
```

#### **Read-only Root Filesystem**
```yaml
# Add to docker-compose.yml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
```

## 📊 Monitoring Docker Containers

### **Container Monitoring**
```bash
# Monitor resource usage
docker stats

# Monitor logs
docker-compose logs -f app

# Check container health
docker-compose ps
```

### **Performance Monitoring**
```bash
# Monitor disk usage
docker system df

# Clean up unused resources
docker system prune -a

# Monitor network
docker network ls
docker network inspect vatsim_vatsim_network
```

## 🔄 Migration Checklist

### **Pre-Dockerization**
- [ ] Remote installation working
- [ ] Data collection verified
- [ ] Performance baseline established
- [ ] Dependencies documented
- [ ] Configuration files backed up

### **Dockerization**
- [ ] Docker installed on remote machine
- [ ] Dockerfile optimized
- [ ] Docker Compose configured
- [ ] Data migration plan ready
- [ ] Health checks implemented

### **Post-Dockerization**
- [ ] Containers running successfully
- [ ] Data collection working
- [ ] Performance meets requirements
- [ ] Monitoring in place
- [ ] Backup strategy implemented

## 🛠️ Troubleshooting

### **Common Docker Issues**

#### **Container Won't Start**
```bash
# Check logs
docker-compose logs app

# Check resource usage
docker stats

# Restart containers
docker-compose restart
```

#### **Database Connection Issues**
```bash
# Check PostgreSQL container
docker exec -it vatsim_postgres pg_isready -U vatsim_user -d vatsim_data

# Check network connectivity
docker exec -it vatsim_app ping postgres
```

#### **Performance Issues**
```bash
# Monitor resource usage
docker stats

# Check container limits
docker inspect vatsim_app | grep -A 10 "HostConfig"

# Optimize container resources
docker-compose down
docker-compose up -d --scale app=1
```

## 🎯 Next Steps After Dockerization

1. **Set up monitoring**: Implement container monitoring
2. **Configure backups**: Set up automated database backups
3. **Security hardening**: Implement security best practices
4. **Scaling**: Prepare for horizontal scaling
5. **CI/CD**: Set up automated deployment pipeline

## 📞 Support

If you encounter issues during dockerization:

1. **Check container logs**: `docker-compose logs`
2. **Verify network**: `docker network inspect`
3. **Test connectivity**: `docker exec -it vatsim_app curl localhost:8001/api/status`
4. **Review configuration**: Check environment variables and volumes

---

**Dockerization completed successfully! 🐳**

Your VATSIM data collection system is now running in Docker containers with improved scalability, isolation, and deployment flexibility. 