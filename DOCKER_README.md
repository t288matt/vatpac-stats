# VATSIM Data Collection System - Docker Setup

This document provides instructions for deploying the VATSIM Data Collection System using Docker.

## Overview

The system consists of:
- **FastAPI Application**: Main data collection and API service
- **PostgreSQL Database**: Optimized for write-heavy workloads
- **Redis**: Caching layer for improved performance
- **pgAdmin**: Database management interface (development only)
- **Redis Commander**: Redis management interface (development only)

## Prerequisites

- Docker
- Docker Compose
- At least 4GB RAM available
- 10GB free disk space

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd vatsim-data-collection
```

### 2. Deploy the System
```bash
# Make the deployment script executable
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
```

### 3. Access the Services
- **Application**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Dashboard**: http://localhost:8001/frontend/index.html
- **pgAdmin**: http://localhost:5050 (admin@vatsim.local / admin)
- **Redis Commander**: http://localhost:8081

## Manual Deployment

### Production Environment
```bash
# Build and start services
docker-compose up -d --build

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Development Environment
```bash
# Build and start development services
docker-compose -f docker-compose.dev.yml up -d --build

# Check service status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs -f
```

## Service Configuration

### Application (FastAPI)
- **Port**: 8001
- **Environment**: Production/Development
- **Memory Limit**: 2GB (prod) / 1GB (dev)
- **Batch Size**: 10,000 (prod) / 5,000 (dev)

### PostgreSQL Database
- **Port**: 5432
- **Database**: vatsim_data (prod) / vatsim_data_dev (dev)
- **User**: vatsim_user
- **Password**: vatsim_password
- **Optimizations**: WAL compression, async commits, connection pooling

### Redis Cache
- **Port**: 6379
- **Memory**: 512MB (prod) / 256MB (dev)
- **Policy**: LRU eviction
- **Persistence**: AOF enabled

## Data Persistence

The following data is persisted:
- **PostgreSQL Data**: `postgres_data` volume
- **Redis Data**: `redis_data` volume
- **Application Data**: `app_data` volume
- **Logs**: `./logs` directory
- **Backups**: `./backups` directory

## Monitoring and Logs

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Health Checks
```bash
# Check application health
curl http://localhost:8001/api/status

# Check database health
docker-compose exec postgres pg_isready -U vatsim_user -d vatsim_data

# Check Redis health
docker-compose exec redis redis-cli ping
```

## Database Management

### pgAdmin (Development)
- **URL**: http://localhost:5050
- **Email**: admin@vatsim.local
- **Password**: admin

### Direct Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U vatsim_user -d vatsim_data

# Connect to Redis
docker-compose exec redis redis-cli
```

## Backup and Restore

### Backup Database
```bash
# PostgreSQL backup
docker-compose exec postgres pg_dump -U vatsim_user vatsim_data > backup.sql

# Redis backup
docker-compose exec redis redis-cli BGSAVE
```

### Restore Database
```bash
# PostgreSQL restore
docker-compose exec -T postgres psql -U vatsim_user -d vatsim_data < backup.sql
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check what's using the ports
   netstat -tulpn | grep :8001
   netstat -tulpn | grep :5432
   ```

2. **Service Won't Start**
   ```bash
   # Check service logs
   docker-compose logs app
   docker-compose logs postgres
   ```

3. **Database Connection Issues**
   ```bash
   # Check database status
   docker-compose exec postgres pg_isready -U vatsim_user -d vatsim_data
   ```

4. **Memory Issues**
   ```bash
   # Check container resource usage
   docker stats
   ```

### Reset Everything
```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Start fresh
./deploy.sh
```

## Performance Optimization

The system is configured for:
- **Write Optimization**: Batch writes every 5 minutes
- **Memory Caching**: 2GB application memory, 512MB Redis
- **Database Optimization**: WAL compression, async commits
- **Connection Pooling**: 20 database connections
- **SSD Protection**: Minimal write frequency

## Security Considerations

- Change default passwords in production
- Use environment variables for sensitive data
- Consider using Docker secrets for production
- Restrict network access to database ports
- Regularly update base images

## Development Workflow

1. **Start Development Environment**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Make Code Changes**
   - Edit files in the mounted volume
   - Changes are reflected immediately

3. **Test Changes**
   - Access application at http://localhost:8001
   - Check logs: `docker-compose -f docker-compose.dev.yml logs -f app`

4. **Stop Development Environment**
   ```bash
   docker-compose -f docker-compose.dev.yml down
   ```

## Production Deployment

For production deployment:
1. Change default passwords
2. Use environment variables for configuration
3. Set up proper logging
4. Configure backups
5. Set up monitoring
6. Use reverse proxy for SSL termination

## Support

For issues and questions:
1. Check the logs: `docker-compose logs -f`
2. Verify service health: `docker-compose ps`
3. Check resource usage: `docker stats`
4. Review this documentation
5. Check the main README.md for additional information 