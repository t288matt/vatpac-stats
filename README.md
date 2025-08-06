# VATSIM Data Collection & Visualization System

A comprehensive system for collecting, processing, and visualizing VATSIM flight data with real-time monitoring capabilities.

## ⚠️ **IMPORTANT: Database Architecture is Stable**

**The database schema and models are well-designed and should NOT be modified during refactoring.** The current database architecture provides:

- ✅ **Complete VATSIM API field mapping** (1:1 mapping with API fields)
- ✅ **Optimized flight tracking** (every position update preserved)
- ✅ **Proper indexing** for fast queries
- ✅ **Unique constraints** to prevent duplicate data
- ✅ **Efficient data types** for storage optimization
- ✅ **Clear table relationships** and foreign keys

**Database files to preserve unchanged:**
- `app/models.py` - All database models
- `app/database.py` - Database connection management
- `database/init.sql` - Database initialization
- All database migration files

**Focus refactoring efforts on:**
- Service layer architecture
- Error handling patterns
- Configuration management
- Monitoring and observability
- Testing frameworks

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 4GB RAM available
- Internet connection for VATSIM API access

### Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd VATSIM-data
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
- **PostgreSQL Database**: Persistent data storage with named volumes
- **Redis Cache**: In-memory caching for performance
- **Python Application**: VATSIM data collection and API
- **Grafana**: Real-time visualization and monitoring

### Data Persistence
The system now uses **named Docker volumes** for reliable data persistence:
- `vatsimdata_postgres_data`: Database storage
- `vatsimdata_redis_data`: Cache storage

This prevents data loss from bind mount corruption and ensures data survives container restarts.

## 🔧 Configuration

### Environment Variables
Key configuration options in `docker-compose.yml`:

```yaml
# Data Collection
VATSIM_POLLING_INTERVAL: 30      # Seconds between VATSIM API calls
WRITE_TO_DISK_INTERVAL: 30       # Seconds between database writes
VATSIM_CLEANUP_INTERVAL: 3600    # Seconds between data cleanup

# Geographic Filtering
FLIGHT_FILTER_ENABLED: "true"     # Only collect Australian flights
FLIGHT_FILTER_LOG_LEVEL: "DEBUG"  # Filter logging level
```

### Data Retention
- **Active Flights**: Stored in real-time, marked as 'completed' after 1 hour
- **Flight Summaries**: Preserved for analytics after completion
- **ATC Positions**: Marked offline after 30 minutes of inactivity
- **Traffic Movements**: Retained for 7 days

## 📈 Monitoring & Visualization

### Grafana Dashboards
- **Sydney Flights Dashboard**: Real-time Australian flight tracking
- **Test Dashboard**: System monitoring and testing

### Key Metrics
- Active flights count
- ATC controller positions
- Flight completion rates
- System performance indicators

## 🛠️ Maintenance

### Backup Named Volumes
```bash
# Backup PostgreSQL data
docker run --rm -v vatsimdata_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore PostgreSQL data
docker run --rm -v vatsimdata_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

### System Health Checks
```bash
# Check service status
docker-compose ps

# View application logs
docker logs vatsim_app

# Check database connectivity
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM flights;"
```

## 🔍 Troubleshooting

### Common Issues

**No Data in Dashboard**
- Check if Australian flights are available in VATSIM network
- Verify flight filter is enabled: `FLIGHT_FILTER_ENABLED: "true"`
- Monitor application logs: `docker logs vatsim_app --tail 20`

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

## 📋 API Endpoints

### Health Check
```
GET /api/status
```

### Flight Data
```
GET /api/flights
GET /api/flights/{callsign}
```

### ATC Controllers
```
GET /api/controllers
GET /api/controllers/{callsign}
```

## 🔒 Security

- Database access restricted to container network
- Grafana authentication enabled (admin/admin)
- API endpoints available on localhost only
- Named volumes provide data isolation

## 📝 Recent Updates

### v2.1.0 - Named Volumes Implementation
- **Improved Data Persistence**: Replaced bind mounts with named Docker volumes
- **Enhanced Reliability**: Data survives container restarts and system reboots
- **Better Performance**: Optimized storage for Docker environments
- **Easier Backup**: Simplified volume backup and restore procedures
- **📖 Detailed Documentation**: See `docs/NAMED_VOLUMES_IMPLEMENTATION.md` for complete implementation details

### Previous Versions
- v2.0.0: Australian flight filtering
- v1.0.0: Initial VATSIM data collection

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Verify system requirements
4. Create an issue with detailed information
