#!/usr/bin/env python3
"""
Database Configuration for VATSIM Data Collection System

This module provides database-specific configuration management.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database configuration with validation."""
    
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False
    pool_recycle: int = 180
    pool_timeout: int = 60
    connect_timeout: int = 30
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    @classmethod
    def load_from_env(cls) -> 'DatabaseConfig':
        """Load database configuration from environment variables."""
        return cls(
            url=os.getenv("DATABASE_URL", "postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data"),
            pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_recycle=int(os.getenv("DATABASE_POOL_RECYCLE", "180")),
            pool_timeout=int(os.getenv("DATABASE_POOL_TIMEOUT", "60")),
            connect_timeout=int(os.getenv("DATABASE_CONNECT_TIMEOUT", "30"))
        )
    
    def validate(self) -> None:
        """Validate database configuration."""
        if not self.url:
            raise ValueError("DATABASE_URL is required")
        
        if self.pool_size < 1:
            raise ValueError("DATABASE_POOL_SIZE must be at least 1")
        
        if self.max_overflow < 0:
            raise ValueError("DATABASE_MAX_OVERFLOW must be non-negative")
        
        if self.pool_recycle < 0:
            raise ValueError("DATABASE_POOL_RECYCLE must be non-negative")
        
        if self.pool_timeout < 1:
            raise ValueError("DATABASE_POOL_TIMEOUT must be at least 1")
        
        if self.connect_timeout < 1:
            raise ValueError("DATABASE_CONNECT_TIMEOUT must be at least 1")
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "url": self.url.replace(self.url.split('@')[0].split('://')[1], '***') if '@' in self.url else self.url,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "echo": self.echo,
            "pool_recycle": self.pool_recycle,
            "pool_timeout": self.pool_timeout,
            "connect_timeout": self.connect_timeout
        } 