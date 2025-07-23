#!/usr/bin/env python3
"""
Configuration management for ATC Position Recommendation Engine.

This module implements the no-hardcoding principle by loading all configuration
from environment variables with sensible defaults.
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
            url=os.getenv("DATABASE_URL", "sqlite:///atc_optimization.db"),
            pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true"
        )


@dataclass
class VATSIMConfig:
    """VATSIM API configuration with no hardcoding."""
    api_url: str
    timeout: int = 30
    retry_attempts: int = 3
    refresh_interval: int = 30
    user_agent: str = "ATC-Position-Engine/1.0"
    
    @classmethod
    def from_env(cls):
        """Load VATSIM configuration from environment variables."""
        return cls(
            api_url=os.getenv("VATSIM_API_URL", "https://data.vatsim.net/v3/vatsim-data.json"),
            timeout=int(os.getenv("VATSIM_API_TIMEOUT", "30")),
            retry_attempts=int(os.getenv("VATSIM_API_RETRY_ATTEMPTS", "3")),
            refresh_interval=int(os.getenv("VATSIM_DATA_REFRESH_INTERVAL", "30")),
            user_agent=os.getenv("VATSIM_USER_AGENT", "ATC-Position-Engine/1.0")
        )


@dataclass
class TrafficAnalysisConfig:
    """Traffic analysis configuration with no hardcoding."""
    density_threshold_high: float = 80.0
    density_threshold_medium: float = 50.0
    density_threshold_low: float = 20.0
    position_priority_weight_flights: float = 0.7
    position_priority_weight_sectors: float = 0.3
    traffic_prediction_confidence_base: float = 0.7
    flight_normalization_factor: float = 10.0
    sector_normalization_factor: float = 5.0
    workload_normalization_factor: float = 15.0
    impact_normalization_factor: float = 20.0
    
    @classmethod
    def from_env(cls):
        """Load traffic analysis configuration from environment variables."""
        return cls(
            density_threshold_high=float(os.getenv("TRAFFIC_DENSITY_THRESHOLD_HIGH", "80")),
            density_threshold_medium=float(os.getenv("TRAFFIC_DENSITY_THRESHOLD_MEDIUM", "50")),
            density_threshold_low=float(os.getenv("TRAFFIC_DENSITY_THRESHOLD_LOW", "20")),
            position_priority_weight_flights=float(os.getenv("POSITION_PRIORITY_WEIGHT_FLIGHTS", "0.7")),
            position_priority_weight_sectors=float(os.getenv("POSITION_PRIORITY_WEIGHT_SECTORS", "0.3")),
            traffic_prediction_confidence_base=float(os.getenv("TRAFFIC_PREDICTION_CONFIDENCE_BASE", "0.7")),
            flight_normalization_factor=float(os.getenv("FLIGHT_NORMALIZATION_FACTOR", "10.0")),
            sector_normalization_factor=float(os.getenv("SECTOR_NORMALIZATION_FACTOR", "5.0")),
            workload_normalization_factor=float(os.getenv("WORKLOAD_NORMALIZATION_FACTOR", "15.0")),
            impact_normalization_factor=float(os.getenv("IMPACT_NORMALIZATION_FACTOR", "20.0"))
        )


@dataclass
class MLConfig:
    """Machine Learning configuration with no hardcoding."""
    model_dir: str = "./models"
    min_training_data: int = 100
    min_historical_data: int = 24
    rf_n_estimators: int = 100
    rf_max_depth: int = 10
    anomaly_contamination: float = 0.1
    pattern_n_estimators: int = 50
    pattern_max_depth: int = 8
    prediction_horizon_hours: int = 4
    confidence_threshold: float = 0.7
    anomaly_threshold: float = 0.8
    
    @classmethod
    def from_env(cls):
        """Load ML configuration from environment variables."""
        return cls(
            model_dir=os.getenv("ML_MODEL_DIR", "./models"),
            min_training_data=int(os.getenv("ML_MIN_TRAINING_DATA", "100")),
            min_historical_data=int(os.getenv("ML_MIN_HISTORICAL_DATA", "24")),
            rf_n_estimators=int(os.getenv("ML_RF_N_ESTIMATORS", "100")),
            rf_max_depth=int(os.getenv("ML_RF_MAX_DEPTH", "10")),
            anomaly_contamination=float(os.getenv("ML_ANOMALY_CONTAMINATION", "0.1")),
            pattern_n_estimators=int(os.getenv("ML_PATTERN_N_ESTIMATORS", "50")),
            pattern_max_depth=int(os.getenv("ML_PATTERN_MAX_DEPTH", "8")),
            prediction_horizon_hours=int(os.getenv("ML_PREDICTION_HORIZON_HOURS", "4")),
            confidence_threshold=float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.7")),
            anomaly_threshold=float(os.getenv("ML_ANOMALY_THRESHOLD", "0.8"))
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
class AirportConfig:
    """Airport configuration with no hardcoding."""
    coordinates_file: Optional[str] = None
    api_url: Optional[str] = None
    cache_duration_hours: int = 24
    
    @classmethod
    def from_env(cls):
        """Load airport configuration from environment variables."""
        return cls(
            coordinates_file=os.getenv("AIRPORT_COORDINATES_FILE"),
            api_url=os.getenv("AIRPORT_API_URL"),
            cache_duration_hours=int(os.getenv("AIRPORT_CACHE_DURATION_HOURS", "24"))
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
class UnattendedDetectionConfig:
    """Unattended session detection configuration with no hardcoding."""
    ground_level_low_speed_enabled: bool = True
    ground_level_max_altitude_ft: int = 1000
    ground_level_max_speed_kts: int = 25
    ground_level_min_duration_minutes: int = 20
    ground_level_airport_distance_nm: int = 5
    
    long_flight_local_time_enabled: bool = True
    long_flight_min_duration_hours: int = 4
    long_flight_local_time_start_hour: int = 1
    long_flight_local_time_end_hour: int = 5
    
    @classmethod
    def from_env(cls):
        """Load unattended detection configuration from environment variables."""
        return cls(
            ground_level_low_speed_enabled=os.getenv("UNATTENDED_GROUND_LEVEL_ENABLED", "true").lower() == "true",
            ground_level_max_altitude_ft=int(os.getenv("UNATTENDED_GROUND_LEVEL_MAX_ALTITUDE_FT", "1000")),
            ground_level_max_speed_kts=int(os.getenv("UNATTENDED_GROUND_LEVEL_MAX_SPEED_KTS", "25")),
            ground_level_min_duration_minutes=int(os.getenv("UNATTENDED_GROUND_LEVEL_MIN_DURATION_MINUTES", "20")),
            ground_level_airport_distance_nm=int(os.getenv("UNATTENDED_GROUND_LEVEL_AIRPORT_DISTANCE_NM", "5")),
            
            long_flight_local_time_enabled=os.getenv("UNATTENDED_LONG_FLIGHT_ENABLED", "true").lower() == "true",
            long_flight_min_duration_hours=int(os.getenv("UNATTENDED_LONG_FLIGHT_MIN_DURATION_HOURS", "4")),
            long_flight_local_time_start_hour=int(os.getenv("UNATTENDED_LONG_FLIGHT_START_HOUR", "1")),
            long_flight_local_time_end_hour=int(os.getenv("UNATTENDED_LONG_FLIGHT_END_HOUR", "5"))
        )


@dataclass
class FeatureFlags:
    """Feature flags with no hardcoding."""
    traffic_analysis: bool = True
    heat_map: bool = True
    position_recommendations: bool = True
    traffic_prediction: bool = True
    alerts: bool = True
    real_time_updates: bool = True
    background_processing: bool = True
    unattended_detection: bool = True
    
    @classmethod
    def from_env(cls):
        """Load feature flags from environment variables."""
        return cls(
            traffic_analysis=os.getenv("FEATURE_TRAFFIC_ANALYSIS", "true").lower() == "true",
            heat_map=os.getenv("FEATURE_HEAT_MAP", "true").lower() == "true",
            position_recommendations=os.getenv("FEATURE_POSITION_RECOMMENDATIONS", "true").lower() == "true",
            traffic_prediction=os.getenv("FEATURE_TRAFFIC_PREDICTION", "true").lower() == "true",
            alerts=os.getenv("FEATURE_ALERTS", "true").lower() == "true",
            real_time_updates=os.getenv("FEATURE_REAL_TIME_UPDATES", "true").lower() == "true",
            background_processing=os.getenv("FEATURE_BACKGROUND_PROCESSING", "true").lower() == "true",
            unattended_detection=os.getenv("FEATURE_UNATTENDED_DETECTION", "true").lower() == "true"
        )


@dataclass
class AppConfig:
    """Main application configuration with no hardcoding."""
    database: DatabaseConfig
    vatsim: VATSIMConfig
    traffic_analysis: TrafficAnalysisConfig
    ml: MLConfig
    api: APIConfig
    logging: LoggingConfig
    features: FeatureFlags
    unattended_detection: UnattendedDetectionConfig
    airports: AirportConfig
    pilots: PilotConfig
    environment: str = "development"
    
    @classmethod
    def from_env(cls):
        """Load complete application configuration from environment variables."""
        return cls(
            database=DatabaseConfig.from_env(),
            vatsim=VATSIMConfig.from_env(),
            traffic_analysis=TrafficAnalysisConfig.from_env(),
            ml=MLConfig.from_env(),
            api=APIConfig.from_env(),
            logging=LoggingConfig.from_env(),
            features=FeatureFlags.from_env(),
            unattended_detection=UnattendedDetectionConfig.from_env(),
            airports=AirportConfig.from_env(),
            pilots=PilotConfig.from_env(),
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
    
    if config.vatsim.refresh_interval <= 0:
        raise ValueError("VATSIM refresh interval must be positive")
    
    # Validate traffic analysis configuration
    if not (0 <= config.traffic_analysis.position_priority_weight_flights <= 1):
        raise ValueError("Position priority weight for flights must be between 0 and 1")
    
    if not (0 <= config.traffic_analysis.position_priority_weight_sectors <= 1):
        raise ValueError("Position priority weight for sectors must be between 0 and 1")
    
    if not (0 <= config.traffic_analysis.traffic_prediction_confidence_base <= 1):
        raise ValueError("Traffic prediction confidence base must be between 0 and 1")
    
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
            "refresh_interval": config.vatsim.refresh_interval
        },
        "traffic_analysis": {
            "density_threshold_high": config.traffic_analysis.density_threshold_high,
            "density_threshold_medium": config.traffic_analysis.density_threshold_medium,
            "density_threshold_low": config.traffic_analysis.density_threshold_low,
            "position_priority_weight_flights": config.traffic_analysis.position_priority_weight_flights,
            "position_priority_weight_sectors": config.traffic_analysis.position_priority_weight_sectors
        },
        "features": {
            "traffic_analysis": config.features.traffic_analysis,
            "heat_map": config.features.heat_map,
            "position_recommendations": config.features.position_recommendations,
            "traffic_prediction": config.features.traffic_prediction,
            "alerts": config.features.alerts
        },
        "logging": {
            "level": config.logging.level,
            "format": config.logging.format,
            "file_path": config.logging.file_path is not None
        }
    } 