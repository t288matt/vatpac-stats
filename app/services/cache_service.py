#!/usr/bin/env python3
"""
In-Memory Cache Service for VATSIM Data Collection System

This module provides an in-memory caching service for performance optimization
by storing frequently accessed data in memory with TTL-based expiration.

INPUTS:
- Cache key-value pairs with TTL
- Cache invalidation requests
- Cache statistics queries

OUTPUTS:
- Fast data retrieval from memory
- Cache statistics and performance metrics
- Automatic TTL-based expiration
"""

import os
import time
from typing import Dict, Any, Optional, List
from collections import OrderedDict
from datetime import datetime, timezone

from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation

class BoundedCacheWithTTL:
    """Bounded cache with TTL support and LRU eviction."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: OrderedDict[str, tuple] = OrderedDict()
    
    def _evict_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [key for key, (_, expiry) in self.cache.items() if current_time > expiry]
        for key in expired_keys:
            self._remove_key(key)
    
    def _remove_key(self, key: str):
        """Remove a key from cache."""
        if key in self.cache:
            del self.cache[key]
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set a key-value pair with TTL."""
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            self._remove_key(oldest_key)
        
        expiry = time.time() + ttl_seconds
        self.cache[key] = (value, expiry)
        self.cache.move_to_end(key)
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value by key, return None if expired or not found."""
        if key not in self.cache:
            return None
        
        value, expiry = self.cache[key]
        if time.time() > expiry:
            self._remove_key(key)
            return None
        
        self.cache.move_to_end(key)
        return value
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if key in self.cache:
            self._remove_key(key)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        self._evict_expired()
        return len(self.cache)
    
    def keys(self):
        """Get all cache keys."""
        self._evict_expired()
        return list(self.cache.keys())

class CacheService:
    """In-memory caching service for performance optimization"""
    
    def __init__(self):
        self.service_name = "cache_service"
        self.logger = get_logger_for_module(f"services.{self.service_name}")
        self._initialized = False
        
        max_cache_size = int(os.getenv('CACHE_MAX_SIZE', 10000))
        self.memory_cache = BoundedCacheWithTTL(max_cache_size)
        self.cache_ttl = {
            'active_atc_positions': 30,      # 30 seconds
            'active_flights': 30,            # 30 seconds
            'network_status': 300,           # 5 minutes
            'network_stats': 60,             # 1 minute
            'airport_data': 600,             # 10 minutes
            'analytics_data': 3600,          # 1 hour
            'vatsim:ratings': 3600,          # 1 hour (static data)
            'airports:region': 600,          # 10 minutes (static data)
            'airport:coords': 3600,          # 1 hour (static data)
        }
        self.hit_count = 0
        self.miss_count = 0
        
    async def initialize(self) -> bool:
        """Initialize in-memory cache service"""
        try:
            self.hit_count = 0
            self.miss_count = 0
            
            cache_size = self.memory_cache.max_size
            self.logger.info(f"In-memory cache service initialized successfully with max size: {cache_size}")
            self.logger.info(f"Cache TTL configuration: {len(self.cache_ttl)} cache types configured")
            
            self._initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing cache service: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if service is properly initialized."""
        return self._initialized
    
    async def health_check(self) -> Dict[str, Any]:
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
    
    async def cleanup(self):
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
        
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            return key.startswith(prefix)
        elif pattern.startswith('*'):
            suffix = pattern[1:]
            return key.endswith(suffix)
        else:
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
        await _cache_service.initialize()
    return _cache_service 
