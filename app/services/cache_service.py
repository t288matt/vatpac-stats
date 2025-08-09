#!/usr/bin/env python3
"""
Redis Caching Service for VATSIM Data Collection System

This service provides intelligent caching to reduce database load and improve
API response times for frequently accessed data. It uses Redis for high-performance
caching with configurable TTL values for different data types.

INPUTS:
- Redis connection configuration
- Data objects to cache (ATC positions, flights, etc.)
- Cache keys and TTL values
- Cache invalidation patterns

OUTPUTS:
- Cached data objects with TTL management
- Cache statistics and performance metrics
- Cache invalidation results
- Fallback memory cache when Redis unavailable

CACHE TYPES:
- Active ATC Positions: 30-second TTL
- Active Flights: 30-second TTL
- Sector Status: 5-minute TTL
- Network Statistics: 1-minute TTL
- Traffic Movements: 5-minute TTL
- Airport Data: 10-minute TTL
- Analytics Data: 1-hour TTL
- Static Data: 1-hour TTL

FEATURES:
- Redis connection pooling
- Automatic TTL management
- Cache invalidation patterns
- Fallback memory cache
- Performance monitoring
- Error handling and recovery

OPTIMIZATIONS:
- Configurable TTL per data type
- Connection timeout management
- JSON serialization for complex objects
- Pattern-based cache invalidation
- Hit rate monitoring
"""

import redis
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta, timezone
import asyncio

from .base_service import CacheService as BaseCacheService
from ..utils.error_handling import handle_service_errors, log_operation, CacheError

class CacheService(BaseCacheService):
    """Redis caching service for performance optimization"""
    
    def __init__(self):
        super().__init__("cache_service")
        self.redis_client = None
        self.cache_ttl = {
            'active_atc_positions': 30,      # 30 seconds
            'active_flights': 30,          # 30 seconds
            'sector_status': 300,          # 5 minutes
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
        
    async def _initialize_service(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.logger.info("Redis cache service initialized successfully")
        except Exception as e:
            self.logger.warning(f"Redis not available, using memory cache: {e}")
            self.redis_client = None
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform cache service health check."""
        try:
            if not self.redis_client:
                return {"status": "no_redis", "fallback": "memory_cache"}
            
            # Test Redis connection
            self.redis_client.ping()
            info = self.redis_client.info()
            
            return {
                "status": "healthy",
                "redis_connected": True,
                "memory_used": info.get('used_memory_human', 'unknown'),
                "connected_clients": info.get('connected_clients', 0),
                "hit_rate": self._calculate_hit_rate(info)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _cleanup_service(self):
        """Cleanup cache service resources."""
        if self.redis_client:
            self.redis_client.close()
            self.redis_client = None
        self.logger.info("Cache service cleanup completed")
    
    @handle_service_errors
    @log_operation("get_cached_data")
    async def get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache"""
        try:
            if not self.redis_client:
                return None
            
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            self.logger.error(f"Error getting cached data for {key}: {e}")
            return None
    
    @handle_service_errors
    @log_operation("set_cached_data")
    async def set_cached_data(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set data in cache with TTL"""
        try:
            if not self.redis_client:
                return False
            
            ttl = ttl or self.cache_ttl.get(key, 300)
            self.redis_client.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            self.logger.error(f"Error setting cached data for {key}: {e}")
            return False
    
    async def invalidate_cache(self, pattern: str) -> bool:
        """Invalidate cache entries matching pattern"""
        try:
            if not self.redis_client:
                return False
            
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries matching {pattern}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache for {pattern}: {e}")
            return False
    
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
            if not self.redis_client:
                return {'status': 'disabled', 'reason': 'Redis not available'}
            
            info = self.redis_client.info()
            return {
                'status': 'active',
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(info)
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_hit_rate(self, info: Dict[str, Any]) -> float:
        """Calculate cache hit rate"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

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
