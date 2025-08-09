#!/usr/bin/env python3
"""
Service Manager for VATSIM Data Collection System

This module provides centralized service management and coordination
using the lifecycle manager for proper service orchestration.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .lifecycle_manager import LifecycleManager
from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation
from ..config_package.service import ServiceConfig


class ServiceManager:
    """Centralized service manager for the VATSIM data collection system."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
        self.lifecycle_manager = LifecycleManager()
        self.config = ServiceConfig.load_from_env()
        self.services: Dict[str, Any] = {}
        self.startup_time: Optional[datetime] = None
        self.running = False
    
    @handle_service_errors
    @log_operation("register_services")
    async def register_services(self, services: Dict[str, Any]) -> bool:
        """Register multiple services with the lifecycle manager."""
        try:
            self.logger.info(f"Registering {len(services)} services")
            
            for name, service in services.items():
                success = await self.lifecycle_manager.register_service(name, service)
                if success:
                    self.services[name] = service
                    self.logger.info(f"Service {name} registered successfully")
                else:
                    self.logger.error(f"Failed to register service {name}")
                    return False
            
            self.logger.info(f"Successfully registered {len(self.services)} services")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register services: {e}")
            return False
    
    @handle_service_errors
    @log_operation("start_all_services")
    async def start_all_services(self) -> Dict[str, bool]:
        """Start all registered services."""
        try:
            self.logger.info("Starting all services")
            self.startup_time = datetime.now(timezone.utc)
            
            # Start services in dependency order
            start_order = [
                'database_service',
                'cache_service', 
                'vatsim_service',
                'flight_processing_service',
                'data_service'
                # 'traffic_analysis_service'  # DISABLED: Traffic Analysis Service Removal - Phase 1
            ]
            
            results = {}
            for service_name in start_order:
                if service_name in self.services:
                    self.logger.info(f"Starting {service_name}")
                    success = await self.lifecycle_manager.start_service(service_name)
                    results[service_name] = success
                    
                    if not success:
                        self.logger.error(f"Failed to start {service_name}")
                        # Continue with other services
                    else:
                        self.logger.info(f"Successfully started {service_name}")
            
            # Start any remaining services not in the order list
            for service_name in self.services:
                if service_name not in start_order:
                    self.logger.info(f"Starting {service_name}")
                    success = await self.lifecycle_manager.start_service(service_name)
                    results[service_name] = success
            
            # Start health check monitoring
            await self.lifecycle_manager.start_health_check_monitoring(
                self.config.health_check_interval
            )
            
            self.running = True
            self.logger.info("All services started successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to start all services: {e}")
            return {}
    
    @handle_service_errors
    @log_operation("stop_all_services")
    async def stop_all_services(self) -> Dict[str, bool]:
        """Stop all registered services."""
        try:
            self.logger.info("Stopping all services")
            
            # Stop health check monitoring first
            await self.lifecycle_manager.stop_health_check_monitoring()
            
            # Stop services in reverse dependency order
            stop_order = [
                # 'traffic_analysis_service',  # DISABLED: Traffic Analysis Service Removal - Phase 1
                'data_service',
                'flight_processing_service',
                'vatsim_service',
                'cache_service',
                'database_service'
            ]
            
            results = {}
            for service_name in stop_order:
                if service_name in self.services:
                    self.logger.info(f"Stopping {service_name}")
                    success = await self.lifecycle_manager.stop_service(service_name)
                    results[service_name] = success
                    
                    if not success:
                        self.logger.error(f"Failed to stop {service_name}")
                        # Continue with other services
                    else:
                        self.logger.info(f"Successfully stopped {service_name}")
            
            # Stop any remaining services not in the order list
            for service_name in self.services:
                if service_name not in stop_order:
                    self.logger.info(f"Stopping {service_name}")
                    success = await self.lifecycle_manager.stop_service(service_name)
                    results[service_name] = success
            
            self.running = False
            self.logger.info("All services stopped successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to stop all services: {e}")
            return {}
    
    @handle_service_errors
    @log_operation("restart_service")
    async def restart_service(self, service_name: str) -> bool:
        """Restart a specific service."""
        try:
            if service_name not in self.services:
                self.logger.error(f"Service {service_name} not registered")
                return False
            
            self.logger.info(f"Restarting service {service_name}")
            success = await self.lifecycle_manager.restart_service(service_name)
            
            if success:
                self.logger.info(f"Successfully restarted {service_name}")
            else:
                self.logger.error(f"Failed to restart {service_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to restart service {service_name}: {e}")
            return False
    
    @handle_service_errors
    @log_operation("health_check_all")
    async def health_check_all(self) -> Dict[str, Any]:
        """Perform health check on all services."""
        try:
            # Get both health check results and service status
            health_results = await self.lifecycle_manager.health_check_all_services()
            service_status = self.lifecycle_manager.get_all_service_status()
            
            # Map service statuses to a more user-friendly format
            mapped_status = {}
            for service_name, status_info in service_status.items():
                if status_info:
                    status_value = status_info.get('status', 'unknown')
                    # Map status values to expected format
                    if status_value in ['stopped', 'stopping']:
                        mapped_status[service_name] = 'not_running'
                    elif status_value in ['starting']:
                        mapped_status[service_name] = 'starting'
                    elif status_value in ['running', 'healthy']:
                        mapped_status[service_name] = 'running'
                    elif status_value in ['error', 'unhealthy']:
                        mapped_status[service_name] = 'error'
                    else:
                        mapped_status[service_name] = status_value
                else:
                    mapped_status[service_name] = 'unknown'
            
            return {
                "timestamp": health_results.get('timestamp'),
                "total_services": health_results.get('total_services', 0),
                "results": health_results.get('results', {}),
                "service_status": mapped_status
            }
        except Exception as e:
            self.logger.error(f"Failed to perform health check: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "results": {},
                "service_status": {}
            }
    
    @handle_service_errors
    @log_operation("health_check_service")
    async def health_check_service(self, service_name: str) -> Dict[str, Any]:
        """Perform health check on a specific service."""
        try:
            return await self.lifecycle_manager.health_check_service(service_name)
        except Exception as e:
            self.logger.error(f"Failed to perform health check on {service_name}: {e}")
            return {
                "service": service_name,
                "status": "error",
                "error": str(e)
            }
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get status information for a specific service."""
        return self.lifecycle_manager.get_service_status(service_name)
    
    def get_all_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all services."""
        return self.lifecycle_manager.get_all_service_status()
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a specific service instance by name."""
        return self.services.get(service_name)
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get service manager status information."""
        return {
            "running": self.running,
            "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            "total_services": len(self.services),
            "registered_services": list(self.services.keys()),
            "config": self.config.to_dict()
        }
    
    async def graceful_shutdown(self) -> bool:
        """Perform graceful shutdown of all services."""
        try:
            self.logger.info("Starting graceful shutdown")
            
            # Stop all services
            stop_results = await self.stop_all_services()
            
            # Check if all services stopped successfully
            all_stopped = all(stop_results.values())
            
            if all_stopped:
                self.logger.info("Graceful shutdown completed successfully")
            else:
                self.logger.warning("Some services failed to stop during graceful shutdown")
            
            return all_stopped
            
        except Exception as e:
            self.logger.error(f"Failed to perform graceful shutdown: {e}")
            return False
    
    async def emergency_shutdown(self) -> bool:
        """Perform emergency shutdown of all services."""
        try:
            self.logger.warning("Starting emergency shutdown")
            
            # Stop health check monitoring immediately
            await self.lifecycle_manager.stop_health_check_monitoring()
            
            # Force stop all services without waiting
            for service_name in self.services:
                try:
                    await self.lifecycle_manager.stop_service(service_name)
                except Exception as e:
                    self.logger.error(f"Failed to stop {service_name} during emergency shutdown: {e}")
            
            self.running = False
            self.logger.warning("Emergency shutdown completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to perform emergency shutdown: {e}")
            return False 