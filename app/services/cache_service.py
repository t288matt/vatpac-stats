#!/usr/bin/env python3
"""
In-Memory Caching Service for VATSIM Data Collection System

This service provides intelligent in-memory caching to reduce database load and improve
API response times for frequently accessed data. It uses a bounded LRU cache with
configurable TTL values for different data types.

INPUTS:
- Data objects to cache (ATC positions, flights, etc.)
- Cache keys and TTL values
- Cache invalidation patterns

OUTPUTS:
- Cached data objects with TTL management
- Cache statistics and performance metrics
- Cache invalidation results
- Memory-efficient LRU eviction

CACHE TYPES:
- Active ATC Positions: 30-second TTL
- Active Flights: 30-second TTL
- Network Statistics: 1-minute TTL
- Network Statistics: 1-minute TTL
- Traffic Movements: 5-minute TTL
- Airport Data: 10-minute TTL
- Analytics Data: 1-hour TTL
- Static Data: 1-hour TTL

FEATURES:
- Bounded LRU cache with automatic eviction
- Automatic TTL management
- Cache invalidation patterns
- Performance monitoring
- Error handling and recovery
- Memory leak prevention

OPTIMIZATIONS:
- Configurable TTL per data type
- Configurable cache size limits
- JSON serialization for complex objects
- Pattern-based cache invalidation
- Hit rate monitoring
"""

import json
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import asyncio

from .base_service import CacheService as BaseCacheService
from ..utils.error_handling import handle_service_errors, log_operation, CacheError

class BoundedCacheWithTTL:
    """Bounded cache with LRU eviction and TTL support."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self.expiry_times = {}
        self.access_counter = 0
    
    def _evict_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [key for key, expiry in self.expiry_times.items() if expiry < current_time]
        for key in expired_keys:
            self._remove_key(key)
    
    def _remove_key(self, key: str):
        """Remove a key from all internal structures."""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
        self.expiry_times.pop(key, None)
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set a value in the cache with TTL and LRU eviction."""
        self._evict_expired()
        
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Evict least recently used
            oldest_key = min(self.access_times, key=self.access_times.get)
            self._remove_key(oldest_key)
        
        self.cache[key] = value
        self.access_times[key] = self.access_counter
        self.expiry_times[key] = time.time() + ttl_seconds
        self.access_counter += 1
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache and update access time."""
        self._evict_expired()
        
        if key in self.cache:
            # Check if expired
            if self.expiry_times[key] < time.time():
                self._remove_key(key)
                return None
            
            self.access_times[key] = self.access_counter
            self.access_counter += 1
            return self.cache[key]
        return None
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if key in self.cache:
            self._remove_key(key)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.access_times.clear()
        self.expiry_times.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        self._evict_expired()
        return len(self.cache)
    
    def keys(self):
        """Get all cache keys."""
        self._evict_expired()
        return list(self.cache.keys())


class CacheService(BaseCacheService):
    """In-memory caching service for performance optimization"""
    
    def __init__(self):
        super().__init__("cache_service")
        max_cache_size = int(os.getenv('CACHE_MAX_SIZE', 10000))
        self.memory_cache = BoundedCacheWithTTL(max_cache_size)
        self.cache_ttl = {
            'active_atc_positions': 30,      # 30 seconds
            'active_flights': 30,          # 30 seconds
            'network_status': 300,         # 5 minutes
            'network_stats': 60,           # 1 minute
            'traffic_movements': 300,      # 5 minutes
            'airport_data': 600,           # 10 minutes
            'analytics_data': 3600,        # 1 hour
            'atc_positions:active': 30,     # 30 seconds
            'atc_positions:by_controller_id': 30,  # 30 seconds
            'vatsim:ratings': 3600,        # 1 hour (static data)
            'airports:region': 600,        # 10 minutes (static data)
            'airport:coords': 3600,        # 1 hour (static data)
        }
        self.hit_count = 0
        self.miss_count = 0
        
    async def _initialize_service(self):
        """Initialize in-memory cache service"""
        try:
            # Initialize statistics
            self.hit_count = 0
            self.miss_count = 0
            
            # Log cache configuration
            cache_size = self.memory_cache.max_size
            self.logger.info(f"In-memory cache service initialized successfully with max size: {cache_size}")
            self.logger.info(f"Cache TTL configuration: {len(self.cache_ttl)} cache types configured")
            
        except Exception as e:
            self.logger.error(f"Error initializing cache service: {e}")
            raise
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform cache service health check."""
        try:
            cache_size = self.memory_cache.size()
            hit_rate = self._calculate_hit_rate()
            
            return {
                "status": "healthy",
                "cache_type": "in_memory",
                "cache_size": cache_size,
                "max_cache_size": self.memory_cache.max_size,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate_percent": hit_rate,
                "memory_efficient": True
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _cleanup_service(self):
        """Cleanup cache service resources."""
        try:
            self.memory_cache.clear()
            self.hit_count = 0
            self.miss_count = 0
            self.logger.info("In-memory cache service cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {e}")
    
    @handle_service_errors
    @log_operation("get_cached_data")
    async def get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache"""
        try:
            cached_data = self.memory_cache.get(key)
            if cached_data is not None:
                self.hit_count += 1
                return cached_data
            else:
                self.miss_count += 1
                return None
        except Exception as e:
            self.logger.error(f"Error getting cached data for {key}: {e}")
            self.miss_count += 1
            return None
    
    @handle_service_errors
    @log_operation("set_cached_data")
    async def set_cached_data(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set data in cache with TTL"""
        try:
            ttl = ttl or self.cache_ttl.get(key, 300)
            self.memory_cache.set(key, data, ttl)
            return True
        except Exception as e:
            self.logger.error(f"Error setting cached data for {key}: {e}")
            return False
    
    async def invalidate_cache(self, pattern: str) -> bool:
        """Invalidate cache entries matching pattern"""
        try:
            # Simple pattern matching for in-memory cache
            keys_to_delete = []
            for key in self.memory_cache.keys():
                if self._pattern_match(key, pattern):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                self.memory_cache.delete(key)
            
            if keys_to_delete:
                self.logger.info(f"Invalidated {len(keys_to_delete)} cache entries matching {pattern}")
            return True
        except Exception as e:
            self.logger.error(f"Error invalidating cache for {pattern}: {e}")
            return False
    
    def _pattern_match(self, key: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)"""
        if '*' not in pattern:
            return key == pattern
        
        # Convert Redis-style pattern to simple matching
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            return key.startswith(prefix)
        elif pattern.startswith('*'):
            suffix = pattern[1:]
            return key.endswith(suffix)
        else:
            # For more complex patterns, fall back to simple contains
            pattern_without_asterisk = pattern.replace('*', '')
            return pattern_without_asterisk in key
    
    async def get_atc_positions_cache(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached ATC positions data"""
        return await self.get_cached_data('atc_positions:active')
    
    async def set_atc_positions_cache(self, atc_positions: List[Dict[str, Any]]) -> bool:
        """Set cached ATC positions data"""
        return await self.set_cached_data('atc_positions:active', {'data': atc_positions, 'timestamp': datetime.now(timezone.utc).isoformat()})
    
    async def get_flights_cache(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached flights data"""
        return await self.get_cached_data('flights:active')
    
    async def set_flights_cache(self, flights: List[Dict[str, Any]]) -> bool:
        """Set cached flights data"""
        return await self.set_cached_data('flights:active', {'data': flights, 'timestamp': datetime.now(timezone.utc).isoformat()})
    
    async def get_network_stats_cache(self) -> Optional[Dict[str, Any]]:
        """Get cached network statistics"""
        return await self.get_cached_data('network:stats')
    
    async def set_network_stats_cache(self, stats: Dict[str, Any]) -> bool:
        """Set cached network statistics"""
        return await self.set_cached_data('network:stats', stats)
    
    async def get_traffic_movements_cache(self, airport_icao: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached traffic movements for airport"""
        return await self.get_cached_data(f'traffic:movements:{airport_icao}')
    
    async def set_traffic_movements_cache(self, airport_icao: str, movements: List[Dict[str, Any]]) -> bool:
        """Set cached traffic movements for airport"""
        return await self.set_cached_data(f'traffic:movements:{airport_icao}', movements)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            cache_size = self.memory_cache.size()
            hit_rate = self._calculate_hit_rate()
            
            return {
                'status': 'active',
                'cache_type': 'in_memory',
                'cache_size': cache_size,
                'max_cache_size': self.memory_cache.max_size,
                'cache_utilization_percent': (cache_size / self.memory_cache.max_size * 100) if self.memory_cache.max_size > 0 else 0,
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'total_requests': self.hit_count + self.miss_count,
                'hit_rate_percent': hit_rate,
                'memory_efficient': True,
                'ttl_enabled': True
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hit_count + self.miss_count
        return (self.hit_count / total * 100) if total > 0 else 0.0

# Global cache service instance
_cache_service = None

async def get_cache_service() -> CacheService:
    """Get or create cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        # Initialize the service
        await _cache_service.initialize()
    return _cache_service 
