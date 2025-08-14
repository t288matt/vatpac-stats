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
    """Database configuration - simplified"""
    url: str
    pool_size: int = 20
    max_overflow: int = 40
    
    @classmethod
    def from_env(cls):
        """Load database configuration from environment variables."""
        url = os.getenv("DATABASE_URL", "postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data")
        return cls(
            url=url,
            pool_size=int(os.getenv("DATABASE_POOL_SIZE", "20")),
            max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "40"))
        )


@dataclass
class VATSIMConfig:
    """VATSIM API configuration - simplified"""
    api_url: str
    transceivers_api_url: str
    timeout: int = 30
    polling_interval: int = 60
    
    @classmethod
    def from_env(cls):
        """Load VATSIM configuration from environment variables."""
        return cls(
            api_url=os.getenv("VATSIM_API_URL", "https://data.vatsim.net/v3/vatsim-data.json"),
            transceivers_api_url=os.getenv("VATSIM_TRANSCEIVERS_API_URL", "https://data.vatsim.net/v3/transceivers-data.json"),
            timeout=int(os.getenv("VATSIM_API_TIMEOUT", "30")),
            polling_interval=int(os.getenv("VATSIM_POLLING_INTERVAL", "60"))
        )








@dataclass
class APIConfig:
    """API configuration - simplified"""
    host: str = "0.0.0.0"
    port: int = 8001
    cors_origins: list = None
    
    @classmethod
    def from_env(cls):
        """Load API configuration from environment variables."""
        cors_str = os.getenv("CORS_ORIGINS", "*")
        cors = cors_str.split(",") if cors_str != "*" else ["*"]
        
        return cls(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8001")),
            cors_origins=cors
        )


@dataclass
class LoggingConfig:
    """Logging configuration - simplified"""
    level: str = "INFO"
    format: str = "json"
    
    @classmethod
    def from_env(cls):
        """Load logging configuration from environment variables."""
        return cls(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "json")
        )








@dataclass
class FlightSummaryConfig:
    """Flight summary and archiving configuration"""
    completion_hours: int = 14
    retention_hours: int = 24
    summary_interval_minutes: int = 60  # Minutes between summary processing (default: 1 hour)
    enabled: bool = True
    
    @classmethod
    def from_env(cls):
        """Load flight summary configuration from environment variables."""
        return cls(
            completion_hours=int(os.getenv("FLIGHT_COMPLETION_HOURS", "14")),
            retention_hours=int(os.getenv("FLIGHT_RETENTION_HOURS", "24")),
            summary_interval_minutes=int(os.getenv("FLIGHT_SUMMARY_INTERVAL", "60")),  # Now in minutes
            enabled=os.getenv("FLIGHT_SUMMARY_ENABLED", "true").lower() == "true"
        )

@dataclass
class SectorTrackingConfig:
    """Sector tracking configuration"""
    enabled: bool = True
    update_interval: int = 60  # seconds
    sectors_file_path: str = "config/australian_airspace_sectors.geojson"
    
    @classmethod
    def from_env(cls):
        """Load sector tracking configuration from environment variables."""
        return cls(
            enabled=os.getenv("SECTOR_TRACKING_ENABLED", "true").lower() == "true",
            update_interval=int(os.getenv("SECTOR_UPDATE_INTERVAL", "60")),
            sectors_file_path=os.getenv("SECTOR_DATA_PATH", "config/australian_airspace_sectors.geojson")
        )

















@dataclass
class PilotConfig:
    """Pilot configuration - simplified"""
    names_file: str = None
    
    @classmethod
    def from_env(cls):
        """Load pilot configuration from environment variables."""
        return cls(
            names_file=os.getenv("PILOT_NAMES_FILE")
        )





@dataclass
class AppConfig:
    """Main application configuration with no hardcoding."""
    database: DatabaseConfig
    vatsim: VATSIMConfig

    api: APIConfig
    logging: LoggingConfig


    pilots: PilotConfig
    flight_summary: FlightSummaryConfig
    sector_tracking: SectorTrackingConfig
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
            flight_summary=FlightSummaryConfig.from_env(),
            sector_tracking=SectorTrackingConfig.from_env(),
            environment=os.getenv("ENVIRONMENT", "development")
        )


def validate_config(config: AppConfig) -> None:
    """
    Basic configuration validation - simplified for VATSIM data collection.
    
    Args:
        config: Application configuration to validate
        
    Raises:
        ValueError: If configuration values are invalid
    """
    # Essential validations only
    if config.vatsim.polling_interval <= 0:
        raise ValueError("VATSIM polling interval must be positive")
    
    if config.api.port < 1 or config.api.port > 65535:
        raise ValueError("API port must be between 1 and 65535")


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
    Get basic configuration summary - simplified for VATSIM data collection.
    
    Returns:
        dict: Basic configuration summary
    """
    config = get_config()
    
    return {
        "environment": config.environment,
        "api": {
            "host": config.api.host,
            "port": config.api.port
        },
        "vatsim": {
            "polling_interval": config.vatsim.polling_interval
        },
        "logging": {
            "level": config.logging.level
        }
    } 
