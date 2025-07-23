# ATC Position Recommendation Engine

A real-time VATSIM data collection and analysis system for Australian airspace, optimized for high-performance data ingestion and analysis.

## 🚀 Features

- **Real-time VATSIM Data Collection**: Collects controller, flight, and sector data every 30 seconds
- **Advanced Analytics**: Traffic analysis, movement detection, and workload optimization
- **Performance Optimized**: SSD wear reduction, memory caching, and bulk operations
- **Scalable Architecture**: Support for both SQLite and PostgreSQL databases
- **Comprehensive Monitoring**: Real-time dashboards and performance metrics

## 📁 Project Structure

```
VATSIM data/
├── app/                          # Main application
│   ├── services/                 # Business logic services
│   ├── utils/                    # Utility functions
│   ├── main.py                   # FastAPI application
│   ├── database.py               # Database configuration
│   ├── models.py                 # SQLAlchemy models
│   └── config.py                 # Configuration management
├── frontend/                     # Web dashboard
├── docs/                         # Documentation
│   ├── migration/                # Database migration docs
│   ├── optimization/             # Performance optimization docs
│   └── analysis/                 # Data analysis docs
├── scripts/                      # Utility scripts
├── tools/                        # Database tools
├── backups/                      # Database backups
├── data/                         # Data files
├── logs/                         # Application logs
└── requirements.txt              # Python dependencies
```

## 🛠️ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python run.py
```

### 3. Access the Dashboard
- **Main Dashboard**: http://localhost:8001/frontend/index.html
- **API Documentation**: http://localhost:8001/docs
- **API Status**: http://localhost:8001/api/status

## 📊 System Architecture

### Data Flow
1. **VATSIM API** → **Data Ingestion Service** → **Database**
2. **Database** → **Analytics Services** → **Dashboard**
3. **Real-time Updates** every 30 seconds

### Performance Optimizations
- **Memory Caching**: 2GB limit with compression
- **Bulk Operations**: 10,000+ records per batch
- **SSD Protection**: WAL mode, minimal disk I/O
- **Database Optimization**: Connection pooling, indexing

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=sqlite:///./atc_optimization.db

# API Settings
API_HOST=0.0.0.0
API_PORT=8001

# Performance
MEMORY_LIMIT_MB=2048
BATCH_SIZE_THRESHOLD=10000
```

## 📈 Performance Characteristics

| Metric | Value |
|--------|-------|
| **Data Collection** | Every 30 seconds |
| **Active Flights** | 1,500+ concurrent |
| **Active Controllers** | 150+ concurrent |
| **Write Throughput** | 10,000+ records/sec |
| **Memory Usage** | 2GB with compression |
| **Disk I/O** | Minimal, batched |

## 🗄️ Database Support

### SQLite (Development)
- File-based storage
- WAL mode for concurrency
- Optimized for SSD wear reduction

### PostgreSQL (Production)
- Network-based storage
- Advanced partitioning
- Connection pooling
- WAL compression

## 📚 Documentation

### Migration Guides
- [PostgreSQL Migration](docs/migration/POSTGRESQL_MIGRATION_README.md)
- [Migration Summary](docs/migration/MIGRATION_SUMMARY.md)

### Optimization Guides
- [Write Optimization](docs/optimization/WRITE_OPTIMIZATION_GUIDE.md)
- [Performance Optimizations](docs/optimization/PERFORMANCE_OPTIMIZATIONS.md)
- [SSD Optimization](docs/optimization/POSTGRESQL_SSD_OPTIMIZATION.md)

### Analysis Tools
- [Data Integrity Report](docs/analysis/DATA_INTEGRITY_REPORT.md)
- [Database Analysis](docs/analysis/analyze_database.py)

## 🛠️ Scripts

### Migration Scripts
- `scripts/migrate_to_postgresql.py` - Full PostgreSQL migration
- `scripts/setup_postgresql.py` - PostgreSQL installation
- `scripts/migrate_windows.py` - Windows-specific migration

### Utility Scripts
- `scripts/test_migration_setup.py` - Migration testing
- `scripts/ssd_optimization.py` - SSD wear optimization
- `scripts/database_migration.py` - Database migration utilities

### Database Tools
- `tools/create_optimized_tables.sql` - Optimized table schemas
- `tools/postgresql.conf` - PostgreSQL configuration

## 🔍 Monitoring

### API Endpoints
- `GET /api/status` - System status
- `GET /api/network/status` - Network statistics
- `GET /api/controllers` - Active controllers
- `GET /api/flights` - Active flights
- `GET /api/traffic/summary/{region}` - Traffic summary
- `GET /api/traffic/movements/{airport}` - Airport movements

### Performance Metrics
- Real-time data collection status
- Memory usage and optimization
- Database connection pool status
- Write throughput and batch efficiency

## 🚀 Deployment

### Development
```bash
python run.py
```

### Production
```bash
# Use PostgreSQL for production
DATABASE_URL=postgresql://user:pass@localhost/vatsim_data
python run.py
```

## 📊 Data Integrity

The system includes comprehensive data integrity checks:
- Real-time data validation
- Automated backup creation
- Data freshness monitoring
- Consistency verification

## 🔧 Troubleshooting

### Common Issues
1. **Database Locked**: Stop the application and restart
2. **Memory Issues**: Check memory limits in config
3. **Performance**: Monitor write batch sizes

### Logs
- Application logs: `logs/`
- Database logs: Check database configuration
- Performance logs: Monitor API endpoints

## 📄 License

This project is designed for VATSIM data collection and analysis.

## 🤝 Contributing

1. Follow the existing code structure
2. Add comprehensive tests
3. Update documentation
4. Test performance impact

---

**Optimized for 99.99999% writes and very rare reads with maximum performance and minimal SSD wear.**
