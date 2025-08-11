#!/usr/bin/env python3
"""
Service Configuration for VATSIM Data Collection System

This module provides service-specific configuration management.
"""

import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class ServiceConfig:
    """Service configuration with no hardcoding."""
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30
    batch_size: int = 1000
    
    @classmethod
    def from_env(cls):
        """Load service configuration from environment variables."""
        return cls(
            max_retries=int(os.getenv("SERVICE_MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("SERVICE_RETRY_DELAY", "5")),
            timeout=int(os.getenv("SERVICE_TIMEOUT", "30")),
            batch_size=int(os.getenv("SERVICE_BATCH_SIZE", "1000"))
        )
    
    def validate(self) -> None:
        """Validate service configuration."""
        if self.max_retries < 0:
            raise ValueError("SERVICE_MAX_RETRIES must be non-negative")
        
        if self.retry_delay < 0:
            raise ValueError("SERVICE_RETRY_DELAY must be non-negative")
        
        if self.timeout < 1:
            raise ValueError("SERVICE_TIMEOUT must be at least 1")
        
        if self.batch_size < 1:
            raise ValueError("SERVICE_BATCH_SIZE must be at least 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout,
            "batch_size": self.batch_size
        } 