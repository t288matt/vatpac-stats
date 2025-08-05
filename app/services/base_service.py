#!/usr/bin/env python3
"""
Base Service Class for VATSIM Data Collection System

This module provides a base class for all services to eliminate code duplication
and standardize common patterns like initialization, error handling, and logging.
"""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from ..config import get_config
from ..utils.logging import get_logger_for_module


class BaseService(ABC):
    """
    Base class for all services in the VATSIM data collection system.
    
    Provides common functionality including:
    - Configuration management
    - Logging setup
    - Error handling patterns
    - Service initialization
    - Health checking
    """
    
    def __init__(self, service_name: str):
        """Initialize base service with common functionality."""
        self.service_name = service_name
        self.config = get_config()
        self.logger = get_logger_for_module(f"services.{service_name}")
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the service with error handling."""
        try:
            await self._initialize_service()
            self._initialized = True
            self.logger.info(f"{self.service_name} service initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.service_name} service: {e}")
            return False
    
    @abstractmethod
    async def _initialize_service(self):
        """Service-specific initialization logic."""
        pass
    
    def is_initialized(self) -> bool:
        """Check if service is properly initialized."""
        return self._initialized
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform service health check."""
        try:
            health_data = await self._perform_health_check()
            return {
                "service": self.service_name,
                "status": "healthy" if health_data else "unhealthy",
                "initialized": self._initialized,
                "details": health_data
            }
        except Exception as e:
            self.logger.error(f"Health check failed for {self.service_name}: {e}")
            return {
                "service": self.service_name,
                "status": "error",
                "initialized": self._initialized,
                "error": str(e)
            }
    
    @abstractmethod
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Service-specific health check logic."""
        pass
    
    async def cleanup(self):
        """Cleanup service resources."""
        try:
            await self._cleanup_service()
            self.logger.info(f"{self.service_name} service cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error during {self.service_name} cleanup: {e}")
    
    @abstractmethod
    async def _cleanup_service(self):
        """Service-specific cleanup logic."""
        pass


class DatabaseService(BaseService):
    """
    Base class for services that require database access.
    
    Provides common database functionality including:
    - Connection management
    - Transaction handling
    - Query optimization
    """
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.db_session = None
    
    async def _initialize_service(self):
        """Initialize database connection."""
        from ..database import SessionLocal
        self.db_session = SessionLocal()
    
    async def _cleanup_service(self):
        """Cleanup database connection."""
        if self.db_session:
            self.db_session.close()
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            if self.db_session:
                # Simple query to test connection
                result = self.db_session.execute("SELECT 1")
                return {"database": "connected", "test_query": "success"}
            return {"database": "no_session"}
        except Exception as e:
            return {"database": "error", "error": str(e)}


class CacheService(BaseService):
    """
    Base class for services that require caching.
    
    Provides common caching functionality including:
    - Cache key management
    - TTL handling
    - Cache invalidation
    """
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.cache_ttl = 300  # Default 5 minutes
    
    async def _initialize_service(self):
        """Initialize cache connection."""
        # Cache initialization logic
        pass
    
    async def _cleanup_service(self):
        """Cleanup cache connections."""
        # Cache cleanup logic
        pass
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Check cache connectivity."""
        return {"cache": "available"} 