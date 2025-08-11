#!/usr/bin/env python3
"""
Configuration Management for VATSIM Data Collection System

This module implements the no-hardcoding principle by loading all configuration
from environment variables with sensible defaults. It provides centralized
configuration management for the entire application.

INPUTS:
- Environment variables for all configuration settings
- Database connection strings
- API endpoints and credentials
- Feature flags and system settings

OUTPUTS:
- Structured configuration objects (AppConfig, DatabaseConfig, etc.)
- Validated configuration settings
- Default values for missing environment variables
- Configuration summaries for monitoring

CONFIGURATION SECTIONS:
- Database: PostgreSQL connection settings
- VATSIM: API endpoints and authentication
# - Traffic Analysis: Thresholds and algorithms  # REMOVED: Traffic Analysis Service - Final Sweep

- API: FastAPI server configuration
- Logging: Log levels and output settings

- Airports: Airport data configuration
- Pilots: Pilot data configuration

ENVIRONMENT VARIABLES:
- DATABASE_URL: PostgreSQL connection string
- VATSIM_API_URL: VATSIM data API endpoint
- API_HOST/PORT: Server binding settings
- LOG_LEVEL: Logging verbosity

"""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration with no hardcoding."""
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False
    
    @classmethod
    def from_env(cls):
        """Load database configuration from environment variables."""
        return cls(
            url=os.getenv("DATABASE_URL", "postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data"),
            pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true"
        )


@dataclass
class VATSIMConfig:
    """VATSIM API configuration with no hardcoding."""
    api_url: str
    transceivers_api_url: str
    timeout: int = 30
    retry_attempts: int = 3
    polling_interval: int = 10
    user_agent: str = "ATC-Position-Engine/1.0"
    write_interval: int = 600  # 10 minutes - fallback if docker-compose doesn't set WRITE_TO_DISK_INTERVAL
    
    @classmethod
    def from_env(cls):
        """Load VATSIM configuration from environment variables."""
        return cls(
            api_url=os.getenv("VATSIM_API_URL", "https://data.vatsim.net/v3/vatsim-data.json"),
            transceivers_api_url=os.getenv("VATSIM_TRANSCEIVERS_API_URL", "https://data.vatsim.net/v3/transceivers-data.json"),
            timeout=int(os.getenv("VATSIM_API_TIMEOUT", "30")),
            retry_attempts=int(os.getenv("VATSIM_API_RETRY_ATTEMPTS", "3")),
            polling_interval=int(os.getenv("VATSIM_POLLING_INTERVAL", "10")),
            user_agent=os.getenv("VATSIM_USER_AGENT", "ATC-Position-Engine/1.0"),
            # WRITE_TO_DISK_INTERVAL: Fallback to 10 minutes (600 seconds) if docker-compose doesn't set it
            # Docker environment typically sets this to 15 seconds for optimized performance
            write_interval=int(os.getenv("WRITE_TO_DISK_INTERVAL", "600"))
        )








@dataclass
class APIConfig:
    """API configuration with no hardcoding."""
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 4
    debug: bool = False
    reload: bool = False
    cors_origins: Optional[list] = None
    
    @classmethod
    def from_env(cls):
        """Load API configuration from environment variables."""
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        cors_origins = cors_origins_str.split(",") if cors_origins_str != "*" else ["*"]
        
        return cls(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8001")),
            workers=int(os.getenv("API_WORKERS", "4")),
            debug=os.getenv("API_DEBUG", "false").lower() == "true",
            reload=os.getenv("API_RELOAD", "false").lower() == "true",
            cors_origins=cors_origins
        )


@dataclass
class LoggingConfig:
    """Logging configuration with no hardcoding."""
    level: str = "INFO"
    format: str = "json"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    @classmethod
    def from_env(cls):
        """Load logging configuration from environment variables."""
        return cls(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "json"),
            file_path=os.getenv("LOG_FILE_PATH"),
            max_file_size=int(os.getenv("LOG_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5"))
        )





@dataclass
class FlightFilterConfig:
    """Flight filter configuration with no hardcoding."""
    enabled: bool = False
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls):
        """Load flight filter configuration from environment variables."""
        return cls(
            enabled=os.getenv("FLIGHT_FILTER_ENABLED", "false").lower() == "true",
            log_level=os.getenv("FLIGHT_FILTER_LOG_LEVEL", "INFO")
        )

















@dataclass
class PilotConfig:
    """Pilot configuration with no hardcoding."""
    names_file: Optional[str] = None
    home_airports_file: Optional[str] = None
    api_url: Optional[str] = None
    
    @classmethod
    def from_env(cls):
        """Load pilot configuration from environment variables."""
        return cls(
            names_file=os.getenv("PILOT_NAMES_FILE"),
            home_airports_file=os.getenv("PILOT_HOME_AIRPORTS_FILE"),
            api_url=os.getenv("PILOT_API_URL")
        )





@dataclass
class AppConfig:
    """Main application configuration with no hardcoding."""
    database: DatabaseConfig
    vatsim: VATSIMConfig

    api: APIConfig
    logging: LoggingConfig


    pilots: PilotConfig
    flight_filter: FlightFilterConfig
    environment: str = "development"
    
    @classmethod
    def from_env(cls):
        """Load complete application configuration from environment variables."""
        return cls(
            database=DatabaseConfig.from_env(),
            vatsim=VATSIMConfig.from_env(),

            api=APIConfig.from_env(),
            logging=LoggingConfig.from_env(),

    
            pilots=PilotConfig.from_env(),
            flight_filter=FlightFilterConfig.from_env(),
            environment=os.getenv("ENVIRONMENT", "development")
        )


def validate_config(config: AppConfig) -> None:
    """
    Validate configuration values to ensure they are within acceptable ranges.
    
    Args:
        config: Application configuration to validate
        
    Raises:
        ValueError: If configuration values are invalid
    """
    # Validate VATSIM configuration
    if config.vatsim.timeout <= 0:
        raise ValueError("VATSIM timeout must be positive")
    
    if config.vatsim.retry_attempts < 0:
        raise ValueError("VATSIM retry attempts must be non-negative")
    
    if config.vatsim.polling_interval <= 0:
        raise ValueError("VATSIM polling interval must be positive")
    

    # Validate database configuration
    if config.database.pool_size <= 0:
        raise ValueError("Database pool size must be positive")
    
    if config.database.max_overflow < 0:
        raise ValueError("Database max overflow must be non-negative")
    
    # Validate API configuration
    if config.api.port < 1 or config.api.port > 65535:
        raise ValueError("API port must be between 1 and 65535")
    
    if config.api.workers <= 0:
        raise ValueError("API workers must be positive")
    
    # Validate logging configuration
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if config.logging.level not in valid_log_levels:
        raise ValueError(f"Log level must be one of: {valid_log_levels}")


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get the application configuration, loading it if not already loaded.
    
    Returns:
        AppConfig: Application configuration
        
    Raises:
        ValueError: If configuration validation fails
    """
    global _config
    
    if _config is None:
        _config = AppConfig.from_env()
        validate_config(_config)
    
    return _config


def reload_config() -> AppConfig:
    """
    Reload the application configuration from environment variables.
    
    Returns:
        AppConfig: Reloaded application configuration
        
    Raises:
        ValueError: If configuration validation fails
    """
    global _config
    
    _config = AppConfig.from_env()
    validate_config(_config)
    
    return _config


def get_config_summary() -> dict:
    """
    Get a summary of the current configuration for logging/debugging.
    
    Returns:
        dict: Configuration summary (excluding sensitive data)
    """
    config = get_config()
    
    return {
        "environment": config.environment,
        "api": {
            "host": config.api.host,
            "port": config.api.port,
            "debug": config.api.debug,
            "workers": config.api.workers
        },
        "database": {
            "url": config.database.url.split("://")[0] + "://***",  # Hide credentials
            "pool_size": config.database.pool_size,
            "max_overflow": config.database.max_overflow
        },
        "vatsim": {
            "api_url": config.vatsim.api_url,
            "timeout": config.vatsim.timeout,
            "retry_attempts": config.vatsim.retry_attempts,
            "polling_interval": config.vatsim.polling_interval
        },


        "logging": {
            "level": config.logging.level,
            "format": config.logging.format,
            "file_path": config.logging.file_path is not None
        }
    } 
