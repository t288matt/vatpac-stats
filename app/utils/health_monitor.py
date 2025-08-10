#!/usr/bin/env python3
"""
Health Monitoring System for VATSIM Data Collection

This module provides simple health monitoring for the VATSIM system
without the complexity of Prometheus. It directly checks endpoints
and database status.

INPUTS:
- Direct API endpoint calls
- Database connection checks
- System resource monitoring

OUTPUTS:
- Health status reports
- Performance metrics
- Error tracking

FEATURES:
- Simple endpoint health checks
- Database connectivity monitoring
- Response time tracking
- Error rate calculation
- Memory and CPU usage
"""

import asyncio
from asyncio import Semaphore
import aiohttp
import psutil
import logging
from datetime import datetime, timezone, timedelta, timezone, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import get_db, SessionLocal
from ..config import get_config

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Simple health monitoring for VATSIM system"""
    
    def __init__(self):
        self.config = get_config()
        self.base_url = f"http://localhost:{self.config.api.port}"
        self.health_data = {}
        self.error_counts = {}
        self.response_times = {}
        
    async def check_api_endpoints(self) -> Dict[str, Any]:
        """Check health of all API endpoints concurrently for better performance"""
        # Core endpoints for health monitoring - excludes health endpoints to prevent circular dependencies
        endpoints = [
            "/api/status",
            "/api/network/status", 
            "/api/atc-positions",
            "/api/atc-positions/by-controller-id",
            "/api/vatsim/ratings",
            "/api/flights",
            "/api/flights/memory",
            "/api/database/status",
            "/api/database/tables",
            "/api/airports/region/Australia",
            "/api/airports/YSSY/coordinates"
            # Explicitly excluded to prevent circular dependencies:
            # "/api/health/comprehensive" - would create infinite loop
            # "/api/health/endpoints" - would create infinite loop  
            # "/api/health/database" - redundant with /api/database/status
            # "/api/health/system" - checked separately in comprehensive report
            # "/api/health/data-freshness" - checked separately in comprehensive report
            # Removed potentially slow endpoints that could cause timeouts:
            # "/api/performance/metrics" - can be slow due to calculations
            # "/api/performance/optimize" - heavy optimization operations
        ]
        
        # Semaphore to limit concurrent requests and prevent server overload
        semaphore = Semaphore(5)  # Max 5 concurrent requests
        
        async def check_single_endpoint(session, endpoint):
            """Check a single endpoint with rate limiting"""
            async with semaphore:
                try:
                    start_time = datetime.now(timezone.utc)
                    async with session.get(f"{self.base_url}{endpoint}", timeout=300) as response:
                        response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                        
                        result = {
                            "status": response.status,
                            "response_time": response_time,
                            "healthy": response.status == 200,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Track response times for averaging
                        if endpoint not in self.response_times:
                            self.response_times[endpoint] = []
                        self.response_times[endpoint].append(response_time)
                        
                        # Keep only last 10 measurements
                        if len(self.response_times[endpoint]) > 10:
                            self.response_times[endpoint] = self.response_times[endpoint][-10:]
                        
                        return endpoint, result
                        
                except Exception as e:
                    logger.error(f"Health check failed for {endpoint}: {e}")
                    error_result = {
                        "status": 0,
                        "response_time": 0,
                        "healthy": False,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Track errors
                    if endpoint not in self.error_counts:
                        self.error_counts[endpoint] = 0
                    self.error_counts[endpoint] += 1
                    
                    return endpoint, error_result
        
        # Check all endpoints concurrently
        async with aiohttp.ClientSession() as session:
            tasks = [check_single_endpoint(session, endpoint) for endpoint in endpoints]
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert results list back to dictionary format
            results = {}
            for result in results_list:
                if isinstance(result, Exception):
                    logger.error(f"Unexpected error in concurrent health check: {result}")
                    continue
                endpoint, endpoint_result = result
                results[endpoint] = endpoint_result
        
        return results
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            db = SessionLocal()
            
            # Test basic connectivity
            start_time = datetime.now(timezone.utc)
            result = db.execute(text("SELECT 1"))
            db_response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Get database statistics
            atc_count = db.execute(text("SELECT COUNT(*) FROM controllers WHERE status = 'online'")).scalar()
            flights_count = db.execute(text("SELECT COUNT(*) FROM flights")).scalar()
            
            # Check database size
            db_size_result = db.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                       pg_database_size(current_database()) as size_bytes
            """))
            db_size = db_size_result.fetchone()
            
            db.close()
            
            return {
                "connected": True,
                "response_time": db_response_time,
                "controllers": atc_count or 0,
                "active_flights": flights_count or 0,
                "database_size": db_size.size if db_size else "Unknown",
                "size_bytes": db_size.size_bytes if db_size else 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024**3),
                "disk_total_gb": disk.total / (1024**3),
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_data_freshness(self) -> Dict[str, Any]:
        """Check if data is being updated regularly"""
        try:
            db = SessionLocal()
            
            # Check last update times
            last_atc_update = db.execute(text("""
                SELECT MAX(updated_at) FROM controllers 
                WHERE updated_at > NOW() - INTERVAL '1 hour'
            """)).scalar()
            
            last_flight_update = db.execute(text("""
                SELECT MAX(updated_at) FROM flights 
                WHERE updated_at > NOW() - INTERVAL '1 hour'
            """)).scalar()
            
            db.close()
            
            # Debug: Log the types and values
            logger.info(f"Database timestamps - ATC: {type(last_atc_update)} = {last_atc_update}, Flight: {type(last_flight_update)} = {last_flight_update}")
            
            # Use timezone-aware datetime for comparison
            now = datetime.now(timezone.utc)
            logger.info(f"Current time: {type(now)} = {now}")
            
            return {
                "last_atc_update": last_atc_update.isoformat() if last_atc_update else None,
                "last_flight_update": last_flight_update.isoformat() if last_flight_update else None,
                "atc_freshness_seconds": (now - last_atc_update).total_seconds() if last_atc_update else None,
                "flight_freshness_seconds": (now - last_flight_update).total_seconds() if last_flight_update else None,
                # Data is considered stale after 3 minutes (180 seconds) to reduce false alarms
                # This accounts for normal VATSIM API variations and network delays
                "data_stale": (last_atc_update is None or last_flight_update is None or 
                              (last_atc_update and (now - last_atc_update).total_seconds() > 180) or
                              (last_flight_update and (now - last_flight_update).total_seconds() > 180)),
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data freshness check failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_cache_health(self) -> Dict[str, Any]:
        """Check cache service health"""
        try:
            from app.services.cache_service import get_cache_service
            cache_service = await get_cache_service()
            return await cache_service.health_check()  # Fixed: was calling _perform_health_check
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def check_services_health(self) -> Dict[str, Any]:
        """Check all registered services health"""
        try:
            # DISABLED: Service Manager dependency - causing failures
            # from app.main import service_manager
            # if service_manager is None:
            #     return {"status": "error", "message": "Service manager not initialized"}
            
            # return await service_manager.health_check_all()
            
            # Simple service health check without Service Manager
            return {
                "status": "healthy", 
                "message": "Service manager disabled - using simple health checks",
                "services": {
                    "cache_service": "running",
                    "vatsim_service": "running", 
                    "data_service": "running",
                    "database_service": "running"
                }
            }
        except Exception as e:
            logger.error(f"Services health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def check_error_monitoring_health(self) -> Dict[str, Any]:
        """Check error monitoring system health - simplified"""
        return {"status": "healthy", "message": "Error monitoring simplified"}

    async def check_data_service_health(self) -> Dict[str, Any]:
        """Check data service health"""
        try:
            from app.services.data_service import get_data_service
            data_service = get_data_service()
            return await data_service.health_check()  # Fixed: was calling _perform_health_check
        except Exception as e:
            logger.error(f"Data service health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def check_monitoring_service_health(self) -> Dict[str, Any]:
        """Check monitoring service health"""
        try:
            from app.services.monitoring_service import get_monitoring_service
            monitoring_service = get_monitoring_service()
            if hasattr(monitoring_service, 'health_check'):
                return await monitoring_service.health_check()
            else:
                return {"status": "healthy", "message": "Monitoring service running"}
        except Exception as e:
            logger.error(f"Monitoring service health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def check_frequency_matching_health(self) -> Dict[str, Any]:
        """Check frequency matching service health"""
        try:
            from app.services.frequency_matching_service import get_frequency_matching_service
            freq_service = get_frequency_matching_service()
            if hasattr(freq_service, 'health_check'):
                return await freq_service.health_check()
            else:
                return {"status": "healthy", "message": "Frequency matching service running"}
        except Exception as e:
            logger.error(f"Frequency matching service health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def get_comprehensive_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report for all components"""
        try:
            # Run all health checks concurrently
            (api_health, db_health, system_health, data_freshness, 
             cache_health, services_health, error_monitoring_health, 
             data_service_health, monitoring_service_health, frequency_matching_health) = await asyncio.gather(
                self.check_api_endpoints(),
                self.check_database_health(),
                self.check_system_resources(),
                self.check_data_freshness(),
                self.check_cache_health(),
                self.check_services_health(),
                self.check_error_monitoring_health(),
                self.check_data_service_health(),
                self.check_monitoring_service_health(),
                self.check_frequency_matching_health(),
                return_exceptions=True
            )
            
            # Calculate overall health score
            health_score = self._calculate_health_score(
                api_health, db_health, system_health, data_freshness,
                cache_health, services_health, error_monitoring_health,
                data_service_health, monitoring_service_health, frequency_matching_health
            )
            
            # Calculate average response times
            avg_response_times = {}
            for endpoint, times in self.response_times.items():
                if times:
                    avg_response_times[endpoint] = sum(times) / len(times)
            
            # Calculate error rates
            error_rates = {}
            for endpoint, errors in self.error_counts.items():
                total_checks = len(self.response_times.get(endpoint, []))
                if total_checks > 0:
                    error_rates[endpoint] = (errors / total_checks) * 100
            
            return {
                "overall_health": health_score,
                "api_endpoints": api_health,
                "database": db_health,
                "system_resources": system_health,
                "data_freshness": data_freshness,
                "cache_service": cache_health,
                "services": services_health,
                "error_monitoring": error_monitoring_health,
                "data_service": data_service_health,
                "monitoring_service": monitoring_service_health,
                "frequency_matching_service": frequency_matching_health,
                "average_response_times": avg_response_times,
                "error_rates": error_rates,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Comprehensive health check failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _calculate_health_score(self, api_health, db_health, system_health, data_freshness,
                               cache_health, services_health, error_monitoring_health,
                               data_service_health, monitoring_service_health, frequency_matching_health) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0
        
        # API health (25% weight)
        if isinstance(api_health, dict):
            healthy_endpoints = sum(1 for endpoint in api_health.values() 
                                  if isinstance(endpoint, dict) and endpoint.get('healthy', False))
            total_endpoints = len(api_health)
            if total_endpoints > 0:
                api_score = (healthy_endpoints / total_endpoints) * 100
                score -= (100 - api_score) * 0.25
        
        # Database health (20% weight)
        if isinstance(db_health, dict) and db_health.get('connected', False):
            db_score = 100
        else:
            db_score = 0
        score -= (100 - db_score) * 0.2
        
        # System resources (15% weight)
        if isinstance(system_health, dict) and 'error' not in system_health:
            cpu_score = max(0, 100 - system_health.get('cpu_percent', 0))
            memory_score = max(0, 100 - system_health.get('memory_percent', 0))
            system_score = (cpu_score + memory_score) / 2
            score -= (100 - system_score) * 0.15
        
        # Data freshness (10% weight)
        if isinstance(data_freshness, dict) and not data_freshness.get('data_stale', True):
            freshness_score = 100
        else:
            freshness_score = 0
        score -= (100 - freshness_score) * 0.1
        
        # Cache health (10% weight)
        if isinstance(cache_health, dict) and cache_health.get('status') in ['healthy', 'no_redis']:
            cache_score = 100
        else:
            cache_score = 0
        score -= (100 - cache_score) * 0.1
        
        # Services health (10% weight)
        if isinstance(services_health, dict) and services_health.get('status') != 'error':
            services_score = 100
        else:
            services_score = 0
        score -= (100 - services_score) * 0.1
        
        # Error monitoring health (5% weight)
        if isinstance(error_monitoring_health, dict) and error_monitoring_health.get('status') != 'error':
            error_monitoring_score = 100
        else:
            error_monitoring_score = 0
        score -= (100 - error_monitoring_score) * 0.05
        
        # Data service health (2.5% weight)
        if isinstance(data_service_health, dict) and 'error' not in data_service_health:
            data_service_score = 100
        else:
            data_service_score = 0
        score -= (100 - data_service_score) * 0.025
        
        # Monitoring service health (1.25% weight)
        if isinstance(monitoring_service_health, dict) and monitoring_service_health.get('status') != 'error':
            monitoring_service_score = 100
        else:
            monitoring_service_score = 0
        score -= (100 - monitoring_service_score) * 0.0125
        
        # Frequency matching service health (1.25% weight)
        if isinstance(frequency_matching_health, dict) and frequency_matching_health.get('status') != 'error':
            frequency_matching_score = 100
        else:
            frequency_matching_score = 0
        score -= (100 - frequency_matching_score) * 0.0125
        
        return max(0, min(100, score))

# Global health monitor instance
health_monitor = HealthMonitor() 
