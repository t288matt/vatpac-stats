#!/usr/bin/env python3
"""
Cache Service Interface for VATSIM Data Collection System

This interface defines the contract for caching operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime


class CacheServiceInterface(ABC):
    """Interface for caching operations."""
    
    @abstractmethod
    async def get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache."""
        pass
    
    @abstractmethod
    async def set_cached_data(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set data in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, pattern: str) -> bool:
        """Invalidate cache entries matching pattern."""
        pass
    
    @abstractmethod
    async def get_flights_cache(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached flights data."""
        pass
    
    @abstractmethod
    async def set_flights_cache(self, flights: List[Dict[str, Any]]) -> bool:
        """Set flights data in cache."""
        pass
    
    @abstractmethod
    async def get_network_stats_cache(self) -> Optional[Dict[str, Any]]:
        """Get cached network statistics."""
        pass
    
    @abstractmethod
    async def set_network_stats_cache(self, stats: Dict[str, Any]) -> bool:
        """Set network statistics in cache."""
        pass
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and performance metrics."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the cache service."""
        pass
    
    @abstractmethod
    async def clear_cache(self) -> bool:
        """Clear all cache entries."""
        pass 