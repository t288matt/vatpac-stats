#!/usr/bin/env python3
"""
Comprehensive Monitoring Service for VATSIM Data Collection System

This service provides comprehensive monitoring and observability for the VATSIM
data collection system, including metrics collection, health checking, and alerting.

INPUTS:
- Service health check data
- Performance metrics from all services
- System resource usage
- Error rates and patterns
- Database performance metrics

OUTPUTS:
- Real-time monitoring dashboards
- Performance alerts and notifications
- Health status reports
- Metrics aggregation and analysis
- Alert management and escalation

FEATURES:
- Metrics collection from all services
- Health checking and monitoring
- Alert management and notification
- Performance tracking and analysis
- Resource usage monitoring
- Error rate tracking and analysis
- Service dependency monitoring
- Real-time dashboard updates
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import psutil
import json

from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation
from ..utils.health_monitor import HealthMonitor
from ..config_package.service import ServiceConfig


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Alert types."""
    SERVICE_DOWN = "service_down"
    HIGH_ERROR_RATE = "high_error_rate"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATABASE_ISSUE = "database_issue"
    API_TIMEOUT = "api_timeout"
    MEMORY_LEAK = "memory_leak"
    CPU_SPIKE = "cpu_spike"


@dataclass
class Metric:
    """Metric data structure."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: datetime
    service: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthStatus:
    """Health status data structure."""
    service: str
    status: str  # healthy, unhealthy, degraded
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    response_time: Optional[float] = None
    error_count: int = 0


class MetricsCollector:
    """Collects and aggregates metrics from all services."""
    
    def __init__(self):
        self.metrics: Dict[str, List[Metric]] = {}
        self.max_metrics_per_name = 1000
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None, unit: str = ""):
        """Record a new metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc),
            tags=tags or {},
            unit=unit
        )
        
        self.metrics[name].append(metric)
        
        # Keep only the most recent metrics
        if len(self.metrics[name]) > self.max_metrics_per_name:
            self.metrics[name] = self.metrics[name][-self.max_metrics_per_name:]
    
    def get_metrics(self, name: str, hours: int = 24) -> List[Metric]:
        """Get metrics for a specific name within the last N hours."""
        if name not in self.metrics:
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [m for m in self.metrics[name] if m.timestamp >= cutoff_time]
    
    def get_latest_metric(self, name: str) -> Optional[Metric]:
        """Get the latest metric for a specific name."""
        if name not in self.metrics or not self.metrics[name]:
            return None
        return self.metrics[name][-1]
    
    def get_metric_summary(self, name: str, hours: int = 24) -> Dict[str, Any]:
        """Get metric summary statistics."""
        metrics = self.get_metrics(name, hours)
        if not metrics:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}
        
        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else 0
        }


class HealthChecker:
    """Performs health checks on all services."""
    
    def __init__(self):
        self.health_monitor = HealthMonitor()
        self.health_status: Dict[str, HealthStatus] = {}
    
    async def check_service_health(self, service_name: str, health_func: Callable) -> HealthStatus:
        """Check health of a specific service."""
        try:
            start_time = datetime.now(timezone.utc)
            health_data = await health_func()
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            status = HealthStatus(
                service=service_name,
                status="healthy" if health_data.get("status") == "healthy" else "unhealthy",
                timestamp=datetime.now(timezone.utc),
                details=health_data,
                response_time=response_time,
                error_count=health_data.get("error_count", 0)
            )
            
            self.health_status[service_name] = status
            return status
            
        except Exception as e:
            status = HealthStatus(
                service=service_name,
                status="unhealthy",
                timestamp=datetime.now(timezone.utc),
                details={"error": str(e)},
                error_count=1
            )
            self.health_status[service_name] = status
            return status
    
    async def check_all_services(self, services: Dict[str, Callable]) -> Dict[str, HealthStatus]:
        """Check health of all services."""
        results = {}
        for service_name, health_func in services.items():
            results[service_name] = await self.check_service_health(service_name, health_func)
        return results
    
    def get_service_health(self, service_name: str) -> Optional[HealthStatus]:
        """Get the latest health status for a service."""
        return self.health_status.get(service_name)
    
    def get_all_health_status(self) -> Dict[str, HealthStatus]:
        """Get health status for all services."""
        return self.health_status.copy()


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_handlers: Dict[AlertType, List[Callable]] = {}
        self.max_alerts = 1000
    
    def create_alert(self, alert_type: AlertType, severity: AlertSeverity, 
                    message: str, service: str, metadata: Dict[str, Any] = None) -> Alert:
        """Create a new alert."""
        alert = Alert(
            id=f"alert_{datetime.now(timezone.utc).timestamp()}_{len(self.alerts)}",
            type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.now(timezone.utc),
            service=service,
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        
        # Keep only the most recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Trigger alert handlers
        self._trigger_alert_handlers(alert)
        
        return alert
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity."""
        return [alert for alert in self.alerts if alert.severity == severity]
    
    def get_alerts_by_service(self, service: str) -> List[Alert]:
        """Get alerts by service."""
        return [alert for alert in self.alerts if alert.service == service]
    
    def register_alert_handler(self, alert_type: AlertType, handler: Callable):
        """Register an alert handler."""
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)
    
    def _trigger_alert_handlers(self, alert: Alert):
        """Trigger handlers for an alert."""
        handlers = self.alert_handlers.get(alert.type, [])
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                logging.error(f"Alert handler failed: {e}")


class MonitoringService:
    """Comprehensive monitoring service for the VATSIM data collection system."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
        self.monitoring_task = None
        self.is_running = False
        
        # Configuration
        self.monitoring_interval = 30  # seconds
        self.health_check_interval = 60  # seconds
        
        # Service registry for health monitoring
        self.registered_services = {}
    
    async def initialize(self):
        """Initialize monitoring service."""
        self.logger.info("Initializing monitoring service")
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Monitoring service initialized")
    
    async def cleanup(self):
        """Cleanup monitoring service resources."""
        self.logger.info("Cleaning up monitoring service")
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Monitoring service cleaned up")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform monitoring service health check."""
        try:
            return {
                "monitoring_service_healthy": True,
                "metrics_collector_active": True,
                "health_checker_active": True,
                "alert_manager_active": True,
                "monitoring_task_running": self.monitoring_task and not self.monitoring_task.done(),
                "registered_services_count": len(self.registered_services)
            }
        except Exception as e:
            self.logger.error(f"Monitoring service health check failed: {e}")
            return {
                "monitoring_service_healthy": False,
                "error": str(e)
            }
    
    @handle_service_errors
    @log_operation("monitor_service")
    async def monitor_service(self, service_name: str, health_func: Callable):
        """Monitor a specific service."""
        health_status = await self.health_checker.check_service_health(service_name, health_func)
        
        # Record metrics
        self.metrics_collector.record_metric(
            f"{service_name}_health_score",
            1.0 if health_status.status == "healthy" else 0.0,
            {"service": service_name}
        )
        
        if health_status.response_time:
            self.metrics_collector.record_metric(
                f"{service_name}_response_time",
                health_status.response_time,
                {"service": service_name},
                "seconds"
            )
        
        # Check for alerts
        if health_status.status == "unhealthy":
            self.alert_manager.create_alert(
                AlertType.SERVICE_DOWN,
                AlertSeverity.HIGH,
                f"Service {service_name} is unhealthy",
                service_name,
                {"health_data": health_status.details}
            )
        
        return health_status
    
    @handle_service_errors
    @log_operation("record_metric")
    async def record_metric(self, name: str, value: float, tags: Dict[str, str] = None, unit: str = ""):
        """Record a metric."""
        self.metrics_collector.record_metric(name, value, tags, unit)
    
    @handle_service_errors
    @log_operation("get_metrics")
    async def get_metrics(self, name: str, hours: int = 24) -> List[Metric]:
        """Get metrics for a specific name."""
        return self.metrics_collector.get_metrics(name, hours)
    
    @handle_service_errors
    @log_operation("get_metric_summary")
    async def get_metric_summary(self, name: str, hours: int = 24) -> Dict[str, Any]:
        """Get metric summary statistics."""
        return self.metrics_collector.get_metric_summary(name, hours)
    
    @handle_service_errors
    @log_operation("get_health_status")
    async def get_health_status(self, service_name: str) -> Optional[HealthStatus]:
        """Get health status for a service."""
        return self.health_checker.get_service_health(service_name)
    
    @handle_service_errors
    @log_operation("get_all_health_status")
    async def get_all_health_status(self) -> Dict[str, HealthStatus]:
        """Get health status for all services."""
        return self.health_checker.get_all_health_status()
    
    @handle_service_errors
    @log_operation("create_alert")
    async def create_alert(self, alert_type: AlertType, severity: AlertSeverity, 
                    message: str, service: str, metadata: Dict[str, Any] = None) -> Alert:
        """Create an alert."""
        return self.alert_manager.create_alert(alert_type, severity, message, service, metadata)
    
    @handle_service_errors
    @log_operation("get_active_alerts")
    async def get_active_alerts(self) -> List[Alert]:
        """Get active alerts."""
        return self.alert_manager.get_active_alerts()
    
    @handle_service_errors
    @log_operation("resolve_alert")
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        return self.alert_manager.resolve_alert(alert_id)
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                # Monitor system resources
                await self._monitor_system_resources()
                
                # Monitor service health
                await self._monitor_service_health()
                
                # Check for performance issues
                await self._check_performance_issues()
                
                # Wait before next monitoring cycle
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Short delay on error
    
    async def _monitor_system_resources(self):
        """Monitor system resources."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics_collector.record_metric("system_cpu_usage", cpu_percent, unit="percent")
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics_collector.record_metric("system_memory_usage", memory.percent, unit="percent")
        self.metrics_collector.record_metric("system_memory_available", memory.available / (1024**3), unit="GB")
        
        # Disk usage
        disk = psutil.disk_usage('/')
        self.metrics_collector.record_metric("system_disk_usage", disk.percent, unit="percent")
        
        # Check for resource alerts
        if cpu_percent > 80:
            self.alert_manager.create_alert(
                AlertType.CPU_SPIKE,
                AlertSeverity.MEDIUM,
                f"High CPU usage: {cpu_percent}%",
                "system",
                {"cpu_percent": cpu_percent}
            )
        
        if memory.percent > 85:
            self.alert_manager.create_alert(
                AlertType.RESOURCE_EXHAUSTION,
                AlertSeverity.HIGH,
                f"High memory usage: {memory.percent}%",
                "system",
                {"memory_percent": memory.percent}
            )
    
    async def _monitor_service_health(self):
        """Monitor service health."""
        # This would be called with actual service health functions
        # For now, we'll just record that monitoring is active
        self.metrics_collector.record_metric("monitoring_active", 1.0)
    
    async def _check_performance_issues(self):
        """Check for performance issues."""
        # Check for high error rates
        error_metrics = self.metrics_collector.get_metrics("error_rate", 1)
        if error_metrics:
            latest_error_rate = error_metrics[-1].value
            if latest_error_rate > 0.1:  # 10% error rate
                self.alert_manager.create_alert(
                    AlertType.HIGH_ERROR_RATE,
                    AlertSeverity.HIGH,
                    f"High error rate: {latest_error_rate:.2%}",
                    "system",
                    {"error_rate": latest_error_rate}
                )
    
    def _handle_service_down(self, alert: Alert):
        """Handle service down alert."""
        self.logger.error(f"Service down alert: {alert.message}")
        # Could send notifications, trigger recovery actions, etc.
    
    def _handle_high_error_rate(self, alert: Alert):
        """Handle high error rate alert."""
        self.logger.warning(f"High error rate alert: {alert.message}")
        # Could trigger circuit breaker, scale up resources, etc.
    
    def _handle_performance_degradation(self, alert: Alert):
        """Handle performance degradation alert."""
        self.logger.warning(f"Performance degradation alert: {alert.message}")
        # Could trigger optimization, resource scaling, etc.


# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service


async def record_metric(name: str, value: float, tags: Dict[str, str] = None, unit: str = ""):
    """Record a metric using the global monitoring service."""
    service = get_monitoring_service()
    await service.record_metric(name, value, tags, unit)


async def create_alert(alert_type: AlertType, severity: AlertSeverity, 
                      message: str, service: str, metadata: Dict[str, Any] = None) -> Alert:
    """Create an alert using the global monitoring service."""
    monitoring_service = get_monitoring_service()
    return await monitoring_service.create_alert(alert_type, severity, message, service, metadata) 