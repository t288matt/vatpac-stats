# Configuration Reference for VATSIM Data Collection System

## Overview

This document provides a centralized reference for all configuration options used throughout the VATSIM data collection system. This eliminates duplication across service docstrings and provides a single source of truth for configuration.

## Environment Variables

### Database Configuration
- `DATABASE_URL`: PostgreSQL connection string
- `DATABASE_POOL_SIZE`: Connection pool size (default: 10)
- `DATABASE_MAX_OVERFLOW`: Max overflow connections (default: 20)
- `DATABASE_ECHO`: Enable SQL logging (default: false)

### VATSIM API Configuration
- `VATSIM_API_URL`: VATSIM data API endpoint
- `VATSIM_TRANSCEIVERS_API_URL`: VATSIM transceivers API endpoint
- `VATSIM_API_TIMEOUT`: API request timeout in seconds (default: 30)
- `VATSIM_API_RETRY_ATTEMPTS`: Number of retry attempts (default: 3)

- `VATSIM_USER_AGENT`: User agent string for API requests

### API Server Configuration
- `API_HOST`: Server host address (default: 0.0.0.0)
- `API_PORT`: Server port (default: 8001)
- `API_WORKERS`: Number of worker processes (default: 4)
- `API_DEBUG`: Enable debug mode (default: false)
- `API_RELOAD`: Enable auto-reload (default: false)
- `CORS_ORIGINS`: Allowed CORS origins (default: "*")

### Logging Configuration
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FORMAT`: Log format (default: json)
- `LOG_FILE_PATH`: Log file path (optional)
- `LOG_MAX_FILE_SIZE`: Max log file size in bytes (default: 10MB)
- `LOG_BACKUP_COUNT`: Number of log file backups (default: 5)

### Traffic Analysis Configuration
- `TRAFFIC_DENSITY_THRESHOLD_HIGH`: High density threshold (default: 80.0)
- `TRAFFIC_DENSITY_THRESHOLD_MEDIUM`: Medium density threshold (default: 50.0)
- `TRAFFIC_DENSITY_THRESHOLD_LOW`: Low density threshold (default: 20.0)
- `POSITION_PRIORITY_WEIGHT_FLIGHTS`: Flight weight for position priority (default: 0.7)
- `POSITION_PRIORITY_WEIGHT_SECTORS`: Sector weight for position priority (default: 0.3)
- `TRAFFIC_PREDICTION_CONFIDENCE_BASE`: Base confidence for predictions (default: 0.7)



### Feature Flags
- `FEATURE_TRAFFIC_ANALYSIS`: Enable traffic analysis (default: true)
- `FEATURE_HEAT_MAP`: Enable heat map generation (default: true)
- `FEATURE_POSITION_RECOMMENDATIONS`: Enable position recommendations (default: true)

- `FEATURE_ALERTS`: Enable alerts (default: true)
- `FEATURE_REAL_TIME_UPDATES`: Enable real-time updates (default: true)
- `FEATURE_BACKGROUND_PROCESSING`: Enable background processing (default: true)

### Airport Configuration
- `AIRPORT_COORDINATES_FILE`: Airport coordinates file path (optional)
- `AIRPORT_API_URL`: Airport API URL (optional)
- `AIRPORT_CACHE_DURATION_HOURS`: Airport cache duration (default: 24)

### Pilot Configuration
- `PILOT_NAMES_FILE`: Pilot names file path (optional)
- `PILOT_HOME_AIRPORTS_FILE`: Pilot home airports file path (optional)
- `PILOT_API_URL`: Pilot API URL (optional)

### Data Processing Intervals
- `VATSIM_POLLING_INTERVAL`: Data polling interval in seconds (default: 30)
- `VATSIM_WRITE_INTERVAL`: Data write interval in seconds (default: 300)


## Configuration Loading

All configuration is loaded through the `get_config()` function in `app/config.py`. This function:

1. Reads environment variables
2. Applies default values
3. Validates configuration
4. Returns structured configuration objects

## Service-Specific Configuration

### Data Service
- Uses polling, write, and cleanup intervals
- Implements memory caching with SSD optimization
- Configurable batch processing

### Cache Service
- Redis connection configuration
- TTL settings for different data types
- Fallback to memory cache when Redis unavailable



### Traffic Analysis Service
- Movement detection thresholds
- Distance calculation parameters
- Confidence scoring weights

## Environment-Specific Configuration

### Development
- Debug logging enabled
- Auto-reload enabled
- Local database connections

### Production
- Optimized logging levels
- Connection pooling
- Performance monitoring

### Testing
- Mock external services
- Reduced polling intervals
- Test-specific database

## Configuration Validation

The system validates configuration at startup and provides clear error messages for:

- Missing required environment variables
- Invalid configuration values
- Database connection issues
- API endpoint accessibility

## Configuration Updates

Configuration can be updated at runtime through:

1. Environment variable changes (requires restart)
2. Database configuration table updates
3. API endpoint configuration updates

## Monitoring Configuration

Configuration monitoring is available through:

- `/api/status` endpoint
- Health check endpoints
- Logging of configuration changes
- Performance metrics collection 