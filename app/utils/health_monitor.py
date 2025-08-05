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
import aiohttp
import psutil
import logging
from datetime import datetime, timedelta
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
        """Check health of all API endpoints"""
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
            "/api/performance/metrics",
            "/api/performance/optimize",
            "/api/health/comprehensive",
            "/api/health/endpoints",
            "/api/health/database",
            "/api/health/system",
            "/api/health/data-freshness",
            "/api/airports/region/Australia",
            "/api/airports/YSSY/coordinates"
        ]
        
        results = {}
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    start_time = datetime.now()
                    async with session.get(f"{self.base_url}{endpoint}", timeout=10) as response:
                        response_time = (datetime.now() - start_time).total_seconds()
                        
                        results[endpoint] = {
                            "status": response.status,
                            "response_time": response_time,
                            "healthy": response.status == 200,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Track response times for averaging
                        if endpoint not in self.response_times:
                            self.response_times[endpoint] = []
                        self.response_times[endpoint].append(response_time)
                        
                        # Keep only last 10 measurements
                        if len(self.response_times[endpoint]) > 10:
                            self.response_times[endpoint] = self.response_times[endpoint][-10:]
                            
                except Exception as e:
                    logger.error(f"Health check failed for {endpoint}: {e}")
                    results[endpoint] = {
                        "status": 0,
                        "response_time": 0,
                        "healthy": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Track errors
                    if endpoint not in self.error_counts:
                        self.error_counts[endpoint] = 0
                    self.error_counts[endpoint] += 1
        
        return results
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            db = SessionLocal()
            
            # Test basic connectivity
            start_time = datetime.now()
            result = db.execute(text("SELECT 1"))
            db_response_time = (datetime.now() - start_time).total_seconds()
            
            # Get database statistics
            atc_count = db.query(text("SELECT COUNT(*) FROM atc_positions WHERE status = 'online'")).scalar()
            flights_count = db.query(text("SELECT COUNT(*) FROM flights WHERE status = 'active'")).scalar()
            
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
                "atc_positions": atc_count or 0,
                "active_flights": flights_count or 0,
                "database_size": db_size.size if db_size else "Unknown",
                "size_bytes": db_size.size_bytes if db_size else 0,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
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
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def check_data_freshness(self) -> Dict[str, Any]:
        """Check if data is being updated regularly"""
        try:
            db = SessionLocal()
            
            # Check last update times
            last_atc_update = db.execute(text("""
                SELECT MAX(updated_at) FROM atc_positions 
                WHERE updated_at > NOW() - INTERVAL '1 hour'
            """)).scalar()
            
            last_flight_update = db.execute(text("""
                SELECT MAX(updated_at) FROM flights 
                WHERE updated_at > NOW() - INTERVAL '1 hour'
            """)).scalar()
            
            db.close()
            
            now = datetime.now()
            
            return {
                "last_atc_update": last_atc_update.isoformat() if last_atc_update else None,
                "last_flight_update": last_flight_update.isoformat() if last_flight_update else None,
                "atc_freshness_seconds": (now - last_atc_update).total_seconds() if last_atc_update else None,
                "flight_freshness_seconds": (now - last_flight_update).total_seconds() if last_flight_update else None,
                "data_stale": (last_atc_update is None or last_flight_update is None),
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data freshness check failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_comprehensive_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report for all components"""
        try:
            # Run all health checks concurrently
            api_health, db_health, system_health, data_freshness = await asyncio.gather(
                self.check_api_endpoints(),
                self.check_database_health(),
                self.check_system_resources(),
                self.check_data_freshness(),
                return_exceptions=True
            )
            
            # Calculate overall health score
            health_score = self._calculate_health_score(api_health, db_health, system_health, data_freshness)
            
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
                "average_response_times": avg_response_times,
                "error_rates": error_rates,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Comprehensive health check failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_health_score(self, api_health, db_health, system_health, data_freshness) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0
        
        # API health (40% weight)
        if isinstance(api_health, dict):
            healthy_endpoints = sum(1 for endpoint in api_health.values() 
                                  if isinstance(endpoint, dict) and endpoint.get('healthy', False))
            total_endpoints = len(api_health)
            if total_endpoints > 0:
                api_score = (healthy_endpoints / total_endpoints) * 100
                score -= (100 - api_score) * 0.4
        
        # Database health (30% weight)
        if isinstance(db_health, dict) and db_health.get('connected', False):
            db_score = 100
        else:
            db_score = 0
        score -= (100 - db_score) * 0.3
        
        # System resources (20% weight)
        if isinstance(system_health, dict) and 'error' not in system_health:
            cpu_score = max(0, 100 - system_health.get('cpu_percent', 0))
            memory_score = max(0, 100 - system_health.get('memory_percent', 0))
            system_score = (cpu_score + memory_score) / 2
            score -= (100 - system_score) * 0.2
        
        # Data freshness (10% weight)
        if isinstance(data_freshness, dict) and not data_freshness.get('data_stale', True):
            freshness_score = 100
        else:
            freshness_score = 0
        score -= (100 - freshness_score) * 0.1
        
        return max(0, min(100, score))

# Global health monitor instance
health_monitor = HealthMonitor() 