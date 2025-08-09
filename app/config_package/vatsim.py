#!/usr/bin/env python3
"""
VATSIM Configuration for VATSIM Data Collection System

This module provides VATSIM-specific configuration management.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class VATSIMConfig:
    """VATSIM API configuration with validation."""
    
    api_url: str
    transceivers_api_url: str
    status_api_url: str
    timeout: int = 30
    retry_attempts: int = 3
    user_agent: str = "ATC-Position-Engine/1.0"
    polling_interval: int = 30
    write_interval: int = 30

    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    @classmethod
    def load_from_env(cls) -> 'VATSIMConfig':
        """Load VATSIM configuration from environment variables."""
        return cls(
            api_url=os.getenv("VATSIM_API_URL", "https://data.vatsim.net/v3/vatsim-data.json"),
            transceivers_api_url=os.getenv("VATSIM_TRANSCEIVERS_API_URL", "https://data.vatsim.net/v3/transceivers-data.json"),
            status_api_url=os.getenv("VATSIM_STATUS_API_URL", "https://data.vatsim.net/v3/status.json"),
            timeout=int(os.getenv("VATSIM_API_TIMEOUT", "30")),
            retry_attempts=int(os.getenv("VATSIM_API_RETRY_ATTEMPTS", "3")),
            user_agent=os.getenv("VATSIM_USER_AGENT", "ATC-Position-Engine/1.0"),
            polling_interval=int(os.getenv("VATSIM_POLLING_INTERVAL", "30")),
            write_interval=int(os.getenv("WRITE_TO_DISK_INTERVAL", "30")),

        )
    
    def validate(self) -> None:
        """Validate VATSIM configuration."""
        if not self.api_url:
            raise ValueError("VATSIM_API_URL is required")
        
        if not self.transceivers_api_url:
            raise ValueError("VATSIM_TRANSCEIVERS_API_URL is required")
        
        if not self.status_api_url:
            raise ValueError("VATSIM_STATUS_API_URL is required")
        
        if self.timeout < 1:
            raise ValueError("VATSIM_API_TIMEOUT must be at least 1")
        
        if self.retry_attempts < 0:
            raise ValueError("VATSIM_API_RETRY_ATTEMPTS must be non-negative")
        
        if self.polling_interval < 1:
            raise ValueError("VATSIM_POLLING_INTERVAL must be at least 1")
        
        if self.write_interval < 1:
            raise ValueError("WRITE_TO_DISK_INTERVAL must be at least 1")
        

    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "api_url": self.api_url,
            "transceivers_api_url": self.transceivers_api_url,
            "status_api_url": self.status_api_url,
            "timeout": self.timeout,
            "retry_attempts": self.retry_attempts,
            "user_agent": self.user_agent,
            "polling_interval": self.polling_interval,
            "write_interval": self.write_interval,

        } 