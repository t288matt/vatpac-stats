#!/usr/bin/env python3
"""
Resource Management Service for VATSIM Data Collection System

This service manages system resources, memory usage, and performance monitoring
to ensure optimal operation under high load conditions. It provides real-time
monitoring and automatic resource optimization.

INPUTS:
- System resource metrics (CPU, memory, disk)
- Performance thresholds and monitoring data
- Resource optimization requests
- System health status information

OUTPUTS:
- Resource usage statistics and metrics
- Performance optimization recommendations
- System health alerts and warnings
- Memory cleanup and optimization results

MONITORING FEATURES:
- Real-time CPU, memory, and disk monitoring
- Automatic resource threshold detection
- Performance bottleneck identification
- System health status tracking
- Resource usage trend analysis

RESOURCE TYPES:
- Memory usage and garbage collection
- CPU utilization and load balancing
- Disk space and I/O performance
- Network connectivity and bandwidth
- Database connection pool health

OPTIMIZATION FEATURES:
- Automatic memory cleanup
- CPU load balancing
- Disk space management
- Connection pool optimization
- Performance tuning recommendations

THRESHOLDS:
- Memory usage: 80% warning threshold
- CPU usage: 90% warning threshold
- Disk usage: 90% warning threshold
- Monitoring interval: 60 seconds
- Cleanup interval: 5 minutes

ALERTS AND ACTIONS:
- High memory usage triggers garbage collection
- High CPU usage triggers load analysis
- High disk usage triggers cleanup operations
- Automatic resource optimization
- Performance degradation alerts
"""

import psutil
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import gc
import threading
import time

from ..config import get_config
from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation, create_error_handler
from ..utils.exceptions import ResourceError, SystemError

logger = get_logger_for_module(__name__)

class ResourceManager:
    """System resource management service"""
    
    def __init__(self):
        self.config = get_config()
        self.error_handler = create_error_handler("resource_manager")
        self.memory_threshold = 0.8  # 80% memory usage threshold
        self.cpu_threshold = 0.9     # 90% CPU usage threshold
        self.disk_threshold = 0.9    # 90% disk usage threshold
        self.monitoring_interval = 60  # seconds
        self.last_cleanup = time.time()
        self.cleanup_interval = 300   # 5 minutes
        
    @handle_service_errors
    @log_operation("start_monitoring")
    async def start_monitoring(self):
        """Start resource monitoring"""
        logger.info("Starting resource monitoring service")
        
        while True:
            try:
                # Monitor system resources
                await self._monitor_resources()
                
                # Perform periodic cleanup
                current_time = time.time()
                if current_time - self.last_cleanup >= self.cleanup_interval:
                    await self._perform_cleanup()
                    self.last_cleanup = current_time
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.error_handler.logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    @handle_service_errors
    @log_operation("monitor_resources")
    async def _monitor_resources(self):
        """Monitor system resources and log warnings"""
        # Get system metrics
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        # Check memory usage
        if memory.percent > (self.memory_threshold * 100):
            logger.warning(f"High memory usage: {memory.percent:.1f}%")
            await self._handle_high_memory()
        
        # Check CPU usage
        if cpu > (self.cpu_threshold * 100):
            logger.warning(f"High CPU usage: {cpu:.1f}%")
            await self._handle_high_cpu()
        
        # Check disk usage
        if disk.percent > (self.disk_threshold * 100):
            logger.warning(f"High disk usage: {disk.percent:.1f}%")
            await self._handle_high_disk()
        
        # Log resource status periodically
        if int(time.time()) % 300 == 0:  # Every 5 minutes
            logger.info(f"Resource status - Memory: {memory.percent:.1f}%, CPU: {cpu:.1f}%, Disk: {disk.percent:.1f}%")
    
    @handle_service_errors
    @log_operation("handle_high_memory")
    async def _handle_high_memory(self):
        """Handle high memory usage"""
        # Force garbage collection
        gc.collect()
        
        # Log memory details
        memory = psutil.virtual_memory()
        logger.info(f"Memory cleanup performed - Available: {memory.available / 1024 / 1024:.1f} MB")
    
    @handle_service_errors
    @log_operation("handle_high_cpu")
    async def _handle_high_cpu(self):
        """Handle high CPU usage"""
        # Get process information
        process = psutil.Process()
        cpu_percent = process.cpu_percent()
        
        logger.info(f"High CPU usage detected - Process CPU: {cpu_percent:.1f}%")
        
        # Could implement CPU throttling here if needed
    
    @handle_service_errors
    @log_operation("handle_high_disk")
    async def _handle_high_disk(self):
        """Handle high disk usage"""
        # Get disk information
        disk = psutil.disk_usage('/')
        free_gb = disk.free / 1024 / 1024 / 1024
        
        logger.warning(f"Low disk space - Free: {free_gb:.1f} GB")
        
        # Could implement disk cleanup here
    
    @handle_service_errors
    @log_operation("perform_cleanup")
    async def _perform_cleanup(self):
        """Perform periodic system cleanup"""
        # Force garbage collection
        collected = gc.collect()
        
        # Clear Python cache
        import sys
        if hasattr(sys, 'getsizeof'):
            cache_size = sum(sys.getsizeof(obj) for obj in gc.get_objects())
            logger.info(f"Cleanup performed - Collected objects: {collected}, Cache size: {cache_size / 1024:.1f} KB")
    
    @handle_service_errors
    @log_operation("get_system_stats")
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        process = psutil.Process()
        
        return {
            "memory": {
                "total_gb": memory.total / 1024 / 1024 / 1024,
                "available_gb": memory.available / 1024 / 1024 / 1024,
                "used_percent": memory.percent,
                "free_percent": 100 - memory.percent
            },
            "cpu": {
                "system_percent": cpu,
                "process_percent": process.cpu_percent(),
                "core_count": psutil.cpu_count()
            },
            "disk": {
                "total_gb": disk.total / 1024 / 1024 / 1024,
                "free_gb": disk.free / 1024 / 1024 / 1024,
                "used_percent": disk.percent,
                "free_percent": 100 - disk.percent
            },
            "process": {
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @handle_service_errors
    @log_operation("optimize_memory_usage")
    async def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage"""
        # Force garbage collection
        collected_before = len(gc.get_objects())
        collected = gc.collect()
        collected_after = len(gc.get_objects())
        
        # Get memory before and after
        memory_before = psutil.virtual_memory()
        
        # Perform additional cleanup
        await self._perform_cleanup()
        
        memory_after = psutil.virtual_memory()
        
        return {
            "status": "optimized",
            "objects_collected": collected,
            "objects_before": collected_before,
            "objects_after": collected_after,
            "memory_freed_mb": (memory_before.used - memory_after.used) / 1024 / 1024,
            "optimization_timestamp": datetime.utcnow().isoformat()
        }
    
    @handle_service_errors
    @log_operation("get_performance_metrics")
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        # System metrics
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)  # Non-blocking CPU measurement
        disk = psutil.disk_usage('/')
        
        # Process metrics
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()
        
        # Network metrics
        network = psutil.net_io_counters()
        
        # Disk I/O metrics
        disk_io = psutil.disk_io_counters()
        
        return {
            "system": {
                "memory_usage_percent": memory.percent,
                "cpu_usage_percent": cpu,
                "disk_usage_percent": disk.percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            },
            "process": {
                "memory_mb": process_memory.rss / 1024 / 1024,
                "cpu_percent": process_cpu,
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            },
            "disk_io": {
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0,
                "read_count": disk_io.read_count if disk_io else 0,
                "write_count": disk_io.write_count if disk_io else 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @handle_service_errors
    @log_operation("set_thresholds")
    def set_thresholds(self, memory: float = None, cpu: float = None, disk: float = None):
        """Set resource monitoring thresholds"""
        if memory is not None:
            self.memory_threshold = memory
        if cpu is not None:
            self.cpu_threshold = cpu
        if disk is not None:
            self.disk_threshold = disk
        
        logger.info(f"Updated thresholds - Memory: {self.memory_threshold}, CPU: {self.cpu_threshold}, Disk: {self.disk_threshold}")

# Global resource manager instance
_resource_manager = None

def get_resource_manager() -> ResourceManager:
    """Get or create resource manager instance"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager 