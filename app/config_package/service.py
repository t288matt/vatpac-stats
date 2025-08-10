#!/usr/bin/env python3
"""
Service Configuration for VATSIM Data Collection System

This module provides service-specific configuration management.
"""

import os
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ServiceConfig:
    """Service configuration with validation."""
    
    # API Configuration
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 4
    debug: bool = False
    reload: bool = False
    cors_origins: List[str] = None
    
    # Service Lifecycle
    startup_timeout: int = 60
    shutdown_timeout: int = 30
    health_check_interval: int = 30
    
    # Memory and Performance
    memory_limit_mb: int = 2048
    batch_size_threshold: int = 10000
    max_concurrent_requests: int = 100
    
    # Error Handling
    # Error monitoring simplified - using basic error handling
    retry_max_attempts: int = 3
    circuit_breaker_threshold: int = 5
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.cors_origins is None:
            self.cors_origins = ["*"]
        self.validate()
    
    @classmethod
    def load_from_env(cls) -> 'ServiceConfig':
        """Load service configuration from environment variables."""
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        cors_origins = cors_origins_str.split(",") if cors_origins_str != "*" else ["*"]
        
        return cls(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8001")),
            workers=int(os.getenv("API_WORKERS", "4")),
            debug=os.getenv("API_DEBUG", "false").lower() == "true",
            reload=os.getenv("API_RELOAD", "false").lower() == "true",
            cors_origins=cors_origins,
            startup_timeout=int(os.getenv("SERVICE_STARTUP_TIMEOUT", "60")),
            shutdown_timeout=int(os.getenv("SERVICE_SHUTDOWN_TIMEOUT", "30")),
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
            memory_limit_mb=int(os.getenv("MEMORY_LIMIT_MB", "2048")),
            batch_size_threshold=int(os.getenv("BATCH_SIZE_THRESHOLD", "10000")),
            max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "100")),
            # Error monitoring simplified - using basic error handling
            retry_max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
            circuit_breaker_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
        )
    
    def validate(self) -> None:
        """Validate service configuration."""
        if not self.host:
            raise ValueError("API_HOST is required")
        
        if self.port < 1 or self.port > 65535:
            raise ValueError("API_PORT must be between 1 and 65535")
        
        if self.workers < 1:
            raise ValueError("API_WORKERS must be at least 1")
        
        if self.startup_timeout < 1:
            raise ValueError("SERVICE_STARTUP_TIMEOUT must be at least 1")
        
        if self.shutdown_timeout < 1:
            raise ValueError("SERVICE_SHUTDOWN_TIMEOUT must be at least 1")
        
        if self.health_check_interval < 1:
            raise ValueError("HEALTH_CHECK_INTERVAL must be at least 1")
        
        if self.memory_limit_mb < 1:
            raise ValueError("MEMORY_LIMIT_MB must be at least 1")
        
        if self.batch_size_threshold < 1:
            raise ValueError("BATCH_SIZE_THRESHOLD must be at least 1")
        
        if self.max_concurrent_requests < 1:
            raise ValueError("MAX_CONCURRENT_REQUESTS must be at least 1")
        
        if self.retry_max_attempts < 0:
            raise ValueError("RETRY_MAX_ATTEMPTS must be non-negative")
        
        if self.circuit_breaker_threshold < 1:
            raise ValueError("CIRCUIT_BREAKER_THRESHOLD must be at least 1")
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "workers": self.workers,
            "debug": self.debug,
            "reload": self.reload,
            "cors_origins": self.cors_origins,
            "startup_timeout": self.startup_timeout,
            "shutdown_timeout": self.shutdown_timeout,
            "health_check_interval": self.health_check_interval,
            "memory_limit_mb": self.memory_limit_mb,
            "batch_size_threshold": self.batch_size_threshold,
            "max_concurrent_requests": self.max_concurrent_requests,
            "error_monitoring_enabled": False,  # Simplified
            "retry_max_attempts": self.retry_max_attempts,
            "circuit_breaker_threshold": self.circuit_breaker_threshold
        } 