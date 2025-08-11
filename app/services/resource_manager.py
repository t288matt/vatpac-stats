#!/usr/bin/env python3
"""
Resource Manager Service for VATSIM Data Collection System

This service manages system resources including memory, CPU, and database connections
to ensure optimal performance and prevent resource exhaustion.
"""

import asyncio
import logging
import psutil
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation

logger = get_logger_for_module(__name__)

@dataclass
class ResourceUsage:
    """Resource usage information."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    disk_usage_percent: float = 0.0
    network_connections: int = 0
    open_files: int = 0

@dataclass
class ResourceThresholds:
    """Resource usage thresholds."""
    cpu_warning: float = 80.0
    cpu_critical: float = 95.0
    memory_warning: float = 80.0
    memory_critical: float = 95.0
    disk_warning: float = 85.0
    disk_critical: float = 95.0

class ResourceManager:
    """Manages system resources and provides monitoring capabilities."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
        self.service_name = "resource_manager"
        self.thresholds = ResourceThresholds()
        self.usage_history: List[ResourceUsage] = []
        self.max_history_size = 1000
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
    
    async def initialize(self):
        """Initialize resource manager."""
        self.logger.info("Initializing resource manager")
        await self.start_monitoring()
    
    async def cleanup(self):
        """Cleanup resource manager."""
        self.logger.info("Cleaning up resource manager")
        await self.stop_monitoring()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check resource manager health."""
        try:
            current_usage = await self.get_current_usage()
            return {
                "status": "healthy",
                "service": "resource_manager",
                "current_usage": current_usage.__dict__,
                "thresholds": self.thresholds.__dict__,
                "monitoring_active": self.is_monitoring
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "resource_manager",
                "error": str(e)
            }
    
    async def get_current_usage(self) -> ResourceUsage:
        """Get current resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            # Network connections
            network_connections = len(psutil.net_connections())
            
            # Open files
            try:
                process = psutil.Process()
                open_files = len(process.open_files())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                open_files = 0
            
            usage = ResourceUsage(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                network_connections=network_connections,
                open_files=open_files
            )
            
            # Store in history
            self.usage_history.append(usage)
            if len(self.usage_history) > self.max_history_size:
                self.usage_history.pop(0)
            
            return usage
            
        except Exception as e:
            self.logger.error(f"Failed to get resource usage: {e}")
            raise
    
    async def check_resource_health(self) -> Dict[str, Any]:
        """Check if resources are within healthy thresholds."""
        try:
            current_usage = await self.get_current_usage()
            
            warnings = []
            criticals = []
            
            # CPU checks
            if current_usage.cpu_percent >= self.thresholds.cpu_critical:
                criticals.append(f"CPU usage critical: {current_usage.cpu_percent:.1f}%")
            elif current_usage.cpu_percent >= self.thresholds.cpu_warning:
                warnings.append(f"CPU usage high: {current_usage.cpu_percent:.1f}%")
            
            # Memory checks
            if current_usage.memory_percent >= self.thresholds.memory_critical:
                criticals.append(f"Memory usage critical: {current_usage.memory_percent:.1f}%")
            elif current_usage.memory_percent >= self.thresholds.memory_warning:
                warnings.append(f"Memory usage high: {current_usage.memory_percent:.1f}%")
            
            # Disk checks
            if current_usage.disk_usage_percent >= self.thresholds.disk_critical:
                criticals.append(f"Disk usage critical: {current_usage.disk_usage_percent:.1f}%")
            elif current_usage.disk_usage_percent >= self.thresholds.disk_warning:
                warnings.append(f"Disk usage high: {current_usage.disk_usage_percent:.1f}%")
            
            return {
                "status": "critical" if criticals else "warning" if warnings else "healthy",
                "warnings": warnings,
                "criticals": criticals,
                "current_usage": current_usage.__dict__,
                "thresholds": self.thresholds.__dict__
            }
            
        except Exception as e:
            self.logger.error(f"Failed to check resource health: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_usage_history(self, hours: int = 24) -> List[ResourceUsage]:
        """Get resource usage history for the specified number of hours."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            return [
                usage for usage in self.usage_history
                if usage.timestamp >= cutoff_time
            ]
        except Exception as e:
            self.logger.error(f"Failed to get usage history: {e}")
            return []
    
    async def set_thresholds(self, **kwargs):
        """Set resource thresholds."""
        try:
            for key, value in kwargs.items():
                if hasattr(self.thresholds, key):
                    setattr(self.thresholds, key, value)
                    self.logger.info(f"Set {key} threshold to {value}")
                else:
                    self.logger.warning(f"Unknown threshold: {key}")
        except Exception as e:
            self.logger.error(f"Failed to set thresholds: {e}")
            raise
    
    async def start_monitoring(self):
        """Start resource monitoring."""
        if self.is_monitoring:
            self.logger.warning("Resource monitoring already active")
            return
        
        try:
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Resource monitoring started")
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            self.is_monitoring = False
            raise
    
    async def stop_monitoring(self):
        """Stop resource monitoring."""
        if not self.is_monitoring:
            return
        
        try:
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            self.logger.info("Resource monitoring stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            raise
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        try:
            while self.is_monitoring:
                try:
                    # Check resource health
                    health_status = await self.check_resource_health()
                    
                    # Log warnings and criticals
                    if health_status["warnings"]:
                        for warning in health_status["warnings"]:
                            self.logger.warning(warning)
                    
                    if health_status["criticals"]:
                        for critical in health_status["criticals"]:
                            self.logger.critical(critical)
                    
                    # Wait before next check
                    await asyncio.sleep(30)  # Check every 30 seconds
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(60)  # Wait longer on error
                    
        except asyncio.CancelledError:
            self.logger.info("Monitoring loop cancelled")
        except Exception as e:
            self.logger.error(f"Monitoring loop failed: {e}")
        finally:
            self.is_monitoring = False


# Global resource manager instance
_resource_manager: Optional[ResourceManager] = None

async def get_resource_manager() -> ResourceManager:
    """Get or create resource manager instance."""
    global _resource_manager
    
    if _resource_manager is None:
        _resource_manager = ResourceManager()
        await _resource_manager.initialize()
    
    return _resource_manager 
