#!/usr/bin/env python3
"""
Service Lifecycle Manager for VATSIM Data Collection System

This module provides centralized service lifecycle management including
startup, shutdown, health checks, and graceful restart capabilities.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum

from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation


class ServiceStatus(Enum):
    """Service status enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class ServiceInfo:
    """Information about a service."""
    
    def __init__(self, name: str, service: Any):
        self.name = name
        self.service = service
        self.status = ServiceStatus.STOPPED
        self.start_time: Optional[datetime] = None
        self.last_health_check: Optional[datetime] = None
        self.health_status: Optional[Dict[str, Any]] = None
        self.error_count = 0
        self.last_error: Optional[str] = None


class LifecycleManager:
    """Manages service lifecycle operations."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
        self.services: Dict[str, ServiceInfo] = {}
        self.health_check_task: Optional[asyncio.Task] = None
        self.running = False
    
    @handle_service_errors
    @log_operation("register_service")
    async def register_service(self, name: str, service: Any) -> bool:
        """Register a service with the lifecycle manager."""
        try:
            if name in self.services:
                self.logger.warning(f"Service {name} already registered, overwriting")
            
            self.services[name] = ServiceInfo(name, service)
            self.logger.info(f"Service {name} registered successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register service {name}: {e}")
            return False
    
    @handle_service_errors
    @log_operation("start_service")
    async def start_service(self, name: str) -> bool:
        """Start a specific service."""
        try:
            if name not in self.services:
                self.logger.error(f"Service {name} not registered")
                return False
            
            service_info = self.services[name]
            
            if service_info.status == ServiceStatus.RUNNING:
                self.logger.info(f"Service {name} is already running")
                return True
            
            service_info.status = ServiceStatus.STARTING
            self.logger.info(f"Starting service {name}")
            
            # Initialize the service
            if hasattr(service_info.service, 'initialize'):
                success = await service_info.service.initialize()
                if not success:
                    service_info.status = ServiceStatus.ERROR
                    self.logger.error(f"Failed to initialize service {name}")
                    return False
            
            service_info.status = ServiceStatus.RUNNING
            service_info.start_time = datetime.now(timezone.utc)
            service_info.error_count = 0
            service_info.last_error = None
            
            self.logger.info(f"Service {name} started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start service {name}: {e}")
            if name in self.services:
                self.services[name].status = ServiceStatus.ERROR
                self.services[name].last_error = str(e)
            return False
    
    @handle_service_errors
    @log_operation("stop_service")
    async def stop_service(self, name: str) -> bool:
        """Stop a specific service."""
        try:
            if name not in self.services:
                self.logger.error(f"Service {name} not registered")
                return False
            
            service_info = self.services[name]
            
            if service_info.status == ServiceStatus.STOPPED:
                self.logger.info(f"Service {name} is already stopped")
                return True
            
            service_info.status = ServiceStatus.STOPPING
            self.logger.info(f"Stopping service {name}")
            
            # Cleanup the service
            if hasattr(service_info.service, 'cleanup'):
                await service_info.service.cleanup()
            
            service_info.status = ServiceStatus.STOPPED
            service_info.start_time = None
            
            self.logger.info(f"Service {name} stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop service {name}: {e}")
            if name in self.services:
                self.services[name].status = ServiceStatus.ERROR
                self.services[name].last_error = str(e)
            return False
    
    @handle_service_errors
    @log_operation("restart_service")
    async def restart_service(self, name: str) -> bool:
        """Restart a specific service."""
        try:
            self.logger.info(f"Restarting service {name}")
            
            # Stop the service
            stop_success = await self.stop_service(name)
            if not stop_success:
                self.logger.error(f"Failed to stop service {name} during restart")
                return False
            
            # Wait a moment before starting
            await asyncio.sleep(1)
            
            # Start the service
            start_success = await self.start_service(name)
            if not start_success:
                self.logger.error(f"Failed to start service {name} during restart")
                return False
            
            self.logger.info(f"Service {name} restarted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restart service {name}: {e}")
            return False
    
    @handle_service_errors
    @log_operation("health_check_service")
    async def health_check_service(self, name: str) -> Dict[str, Any]:
        """Perform health check on a specific service."""
        try:
            if name not in self.services:
                return {
                    "service": name,
                    "status": "not_registered",
                    "error": "Service not registered"
                }
            
            service_info = self.services[name]
            service_info.last_health_check = datetime.now(timezone.utc)
            
            if service_info.status != ServiceStatus.RUNNING:
                return {
                    "service": name,
                    "status": "not_running",
                    "service_status": service_info.status.value
                }
            
            # Perform health check
            if hasattr(service_info.service, 'health_check'):
                health_result = await service_info.service.health_check()
                service_info.health_status = health_result
                
                if health_result.get('status') == 'healthy':
                    service_info.status = ServiceStatus.HEALTHY
                    service_info.error_count = 0
                else:
                    service_info.status = ServiceStatus.UNHEALTHY
                    service_info.error_count += 1
                    service_info.last_error = health_result.get('error', 'Unknown error')
                
                return health_result
            else:
                # No health check method, assume healthy if running
                service_info.status = ServiceStatus.HEALTHY
                return {
                    "service": name,
                    "status": "healthy",
                    "message": "No health check method available"
                }
                
        except Exception as e:
            self.logger.error(f"Health check failed for service {name}: {e}")
            if name in self.services:
                self.services[name].error_count += 1
                self.services[name].last_error = str(e)
                self.services[name].status = ServiceStatus.UNHEALTHY
            
            return {
                "service": name,
                "status": "error",
                "error": str(e)
            }
    
    @handle_service_errors
    @log_operation("health_check_all_services")
    async def health_check_all_services(self) -> Dict[str, Any]:
        """Perform health check on all services."""
        try:
            results = {}
            for name in self.services:
                results[name] = await self.health_check_service(name)
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_services": len(self.services),
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to perform health check on all services: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "results": {}
            }
    
    @handle_service_errors
    @log_operation("start_all_services")
    async def start_all_services(self) -> Dict[str, bool]:
        """Start all registered services."""
        try:
            results = {}
            for name in self.services:
                results[name] = await self.start_service(name)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to start all services: {e}")
            return {}
    
    @handle_service_errors
    @log_operation("stop_all_services")
    async def stop_all_services(self) -> Dict[str, bool]:
        """Stop all registered services."""
        try:
            results = {}
            for name in self.services:
                results[name] = await self.stop_service(name)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to stop all services: {e}")
            return {}
    
    def get_service_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status information for a specific service."""
        if name not in self.services:
            return None
        
        service_info = self.services[name]
        return {
            "name": service_info.name,
            "status": service_info.status.value,
            "start_time": service_info.start_time.isoformat() if service_info.start_time else None,
            "last_health_check": service_info.last_health_check.isoformat() if service_info.last_health_check else None,
            "error_count": service_info.error_count,
            "last_error": service_info.last_error,
            "health_status": service_info.health_status
        }
    
    def get_all_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all services."""
        return {
            name: self.get_service_status(name)
            for name in self.services
        }
    
    async def start_health_check_monitoring(self, interval: int = 30) -> None:
        """Start periodic health check monitoring."""
        self.running = True
        self.health_check_task = asyncio.create_task(self._health_check_loop(interval))
        self.logger.info(f"Started health check monitoring with {interval}s interval")
    
    async def stop_health_check_monitoring(self) -> None:
        """Stop periodic health check monitoring."""
        self.running = False
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped health check monitoring")
    
    async def _health_check_loop(self, interval: int) -> None:
        """Background loop for periodic health checks."""
        while self.running:
            try:
                await self.health_check_all_services()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(interval) 