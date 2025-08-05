# Native Setup Guide - Running VATSIM Data App Without Docker

## 🎯 **Difficulty Assessment: MODERATE** (6/10)

The app can be run natively, but requires setting up PostgreSQL, Redis, and Python dependencies manually.

## 📋 **What Needs to Be Done**

### 1. **Database Setup** (PostgreSQL)
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres createdb vatsim_data
sudo -u postgres createuser vatsim_user
sudo -u postgres psql -c "ALTER USER vatsim_user PASSWORD 'vatsim_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vatsim_data TO vatsim_user;"

# Apply database schema
psql -U vatsim_user -d vatsim_data -f tools/create_write_optimized_tables.sql
```

### 2. **Redis Setup**
```bash
# Install Redis
sudo apt install redis-server

# Configure Redis (optional)
sudo nano /etc/redis/redis.conf
# Set: maxmemory 512mb
# Set: maxmemory-policy allkeys-lru

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 3. **Python Environment**
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. **Environment Configuration**
Create `.env` file:
```bash
# Database Configuration
DATABASE_URL=postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
PRODUCTION_MODE=false

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
VATSIM_CLEANUP_INTERVAL=3600
```

### 5. **Database Initialization**
```bash
# Initialize database
python -c "from app.database import init_db; init_db()"
```

### 6. **Run the Application**
```bash
# Start the app
python run.py
```

## 🔧 **Key Changes Needed**

### 1. **Database Connection**
- **Docker**: `postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data`
- **Native**: `postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data`

### 2. **Redis Connection**
- **Docker**: `redis://redis:6379`
- **Native**: `redis://localhost:6379`

### 3. **File Paths**
- **Docker**: `/app/` paths
- **Native**: Relative paths or absolute paths

## ✅ **Advantages of Native Setup**

1. **Faster Development**: No container overhead
2. **Easier Debugging**: Direct access to logs and processes
3. **Better Performance**: No virtualization layer
4. **Simpler Testing**: Direct access to services
5. **Easier Integration**: Native system tools available

## ⚠️ **Challenges**

1. **Dependency Management**: Manual setup of PostgreSQL, Redis
2. **Environment Consistency**: Harder to ensure same environment across machines
3. **Service Management**: Manual start/stop of services
4. **Port Conflicts**: Need to ensure ports 5432, 6379, 8001 are available
5. **System Dependencies**: May need additional system packages

## 🚀 **Quick Start Script**

Create `run_native.sh`:
```bash
#!/bin/bash

echo "🚀 Starting VATSIM Data App (Native Mode)"

# Check if PostgreSQL is running
if ! pg_isready -U vatsim_user -d vatsim_data; then
    echo "❌ PostgreSQL not running. Starting..."
    sudo systemctl start postgresql
fi

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis not running. Starting..."
    sudo systemctl start redis-server
fi

# Activate virtual environment
source venv/bin/activate

# Set environment
export PRODUCTION_MODE=false
export DATABASE_URL=postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data
export REDIS_URL=redis://localhost:6379

# Start the application
python run.py
```

## 📊 **Comparison**

| Aspect | Docker | Native |
|--------|--------|--------|
| **Setup Time** | 5 minutes | 15-30 minutes |
| **Dependencies** | Automatic | Manual |
| **Performance** | Slightly slower | Faster |
| **Debugging** | Container logs | Direct access |
| **Portability** | Excellent | Good |
| **Development** | Container overhead | Direct access |

## 🎯 **Recommendation**

**For Development**: Use native setup for faster iteration and easier debugging
**For Production**: Use Docker for consistency and deployment simplicity

## 🔧 **Troubleshooting Native Setup**

### Common Issues:
1. **PostgreSQL connection refused**: Check if PostgreSQL is running
2. **Redis connection refused**: Check if Redis is running  
3. **Port already in use**: Stop conflicting services
4. **Permission denied**: Check file permissions and user access

### Debug Commands:
```bash
# Check PostgreSQL
sudo systemctl status postgresql
psql -U vatsim_user -d vatsim_data -c "SELECT version();"

# Check Redis
sudo systemctl status redis-server
redis-cli ping

# Check ports
netstat -tlnp | grep -E ':(5432|6379|8001)'

# Check Python environment
python -c "import psycopg2, redis, fastapi; print('All dependencies OK')"
```

## 📈 **Performance Benefits**

- **Startup Time**: 2-3 seconds vs 10-15 seconds (Docker)
- **Memory Usage**: ~100MB less overhead
- **CPU Usage**: ~5-10% less overhead
- **File I/O**: Direct access, no volume mounting overhead
- **Network**: Direct localhost connections, no container networking

The native setup is definitely feasible and would provide better performance for development and testing! 