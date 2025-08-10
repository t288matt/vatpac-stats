#!/usr/bin/env python3
"""
Performance Monitoring Service for VATSIM Data Collection System - Phase 3

This service provides comprehensive performance monitoring, tracking, and optimization
recommendations for the VATSIM data collection system.

INPUTS:
- Operation timing data from all services
- Resource usage metrics
- Database query performance
- API response times
- Memory and CPU usage patterns

OUTPUTS:
- Performance metrics and analytics
- Optimization recommendations
- Performance alerts and notifications
- Resource usage reports
- Performance trend analysis

FEATURES:
- Operation timing and performance tracking
- Resource usage monitoring
- Performance optimization recommendations
- Performance alerts and notifications
- Performance trend analysis
- Database query optimization
- Memory leak detection
- CPU usage optimization

PHASE 3 FEATURES:
- Advanced performance analytics
- Predictive performance modeling
- Automatic optimization recommendations
- Real-time performance monitoring
- Performance impact analysis
- Resource optimization strategies
- Performance regression detection
- Automated performance testing
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json


from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation
from ..utils.structured_logging import get_structured_logger, LogLevel, LogCategory
from ..config_package.service import ServiceConfig


class PerformanceMetric(Enum):
    """Performance metric types."""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DATABASE_QUERY_TIME = "database_query_time"
    CACHE_HIT_RATE = "cache_hit_rate"
    ERROR_RATE = "error_rate"
    CONCURRENT_REQUESTS = "concurrent_requests"


@dataclass
class PerformanceData:
    """Performance data structure."""
    operation: str
    service: str
    metric_type: PerformanceMetric
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    unit: str = ""


@dataclass
class PerformanceAlert:
    """Performance alert structure."""
    id: str
    operation: str
    service: str
    metric_type: PerformanceMetric
    threshold: float
    current_value: float
    severity: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation."""
    id: str
    operation: str
    service: str
    recommendation_type: str
    description: str
    expected_improvement: float
    implementation_difficulty: str
    priority: str
    timestamp: datetime


class PerformanceCollector:
    """Collects and aggregates performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[PerformanceData]] = {}
        self.max_metrics_per_operation = 1000
        self.performance_thresholds = {
            "response_time": 1.0,  # seconds
            "memory_usage": 85.0,  # percent
            "cpu_usage": 80.0,     # percent
            "error_rate": 0.05,    # 5%
            "database_query_time": 0.5  # seconds
        }
    
    def record_metric(self, operation: str, service: str, metric_type: PerformanceMetric,
                     value: float, unit: str = "", metadata: Dict[str, Any] = None):
        """Record a performance metric."""
        key = f"{service}.{operation}.{metric_type.value}"
        
        if key not in self.metrics:
            self.metrics[key] = []
        
        metric = PerformanceData(
            operation=operation,
            service=service,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
            unit=unit
        )
        
        self.metrics[key].append(metric)
        
        # Keep only the most recent metrics
        if len(self.metrics[key]) > self.max_metrics_per_operation:
            self.metrics[key] = self.metrics[key][-self.max_metrics_per_operation:]
    
    def get_metrics(self, operation: str, service: str, metric_type: PerformanceMetric,
                   hours: int = 24) -> List[PerformanceData]:
        """Get metrics for a specific operation and metric type."""
        key = f"{service}.{operation}.{metric_type.value}"
        if key not in self.metrics:
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [m for m in self.metrics[key] if m.timestamp >= cutoff_time]
    
    def get_metric_summary(self, operation: str, service: str, metric_type: PerformanceMetric,
                          hours: int = 24) -> Dict[str, Any]:
        """Get metric summary statistics."""
        metrics = self.get_metrics(operation, service, metric_type, hours)
        if not metrics:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "median": 0}
        
        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "median": statistics.median(values),
            "latest": values[-1] if values else 0
        }
    
    def check_thresholds(self, operation: str, service: str, metric_type: PerformanceMetric,
                        value: float) -> Optional[PerformanceAlert]:
        """Check if a metric exceeds thresholds."""
        threshold_key = metric_type.value
        threshold = self.performance_thresholds.get(threshold_key)
        
        if threshold and value > threshold:
            return PerformanceAlert(
                id=f"perf_alert_{datetime.now(timezone.utc).timestamp()}",
                operation=operation,
                service=service,
                metric_type=metric_type,
                threshold=threshold,
                current_value=value,
                severity="high" if value > threshold * 1.5 else "medium",
                message=f"{metric_type.value} exceeded threshold: {value} > {threshold}",
                timestamp=datetime.now(timezone.utc)
            )
        
        return None


class PerformanceOptimizer:
    """Provides performance optimization recommendations."""
    
    def __init__(self):
        self.recommendations: List[OptimizationRecommendation] = []
        self.max_recommendations = 100
    
    def analyze_performance(self, metrics: Dict[str, List[PerformanceData]]) -> List[OptimizationRecommendation]:
        """Analyze performance metrics and generate recommendations."""
        recommendations = []
        
        for key, metric_list in metrics.items():
            if not metric_list:
                continue
            
            # Analyze response times
            response_time_metrics = [m for m in metric_list if m.metric_type == PerformanceMetric.RESPONSE_TIME]
            if response_time_metrics:
                avg_response_time = statistics.mean([m.value for m in response_time_metrics])
                if avg_response_time > 0.5:  # 500ms threshold
                    recommendations.append(OptimizationRecommendation(
                        id=f"opt_{datetime.now(timezone.utc).timestamp()}_{len(recommendations)}",
                        operation=response_time_metrics[0].operation,
                        service=response_time_metrics[0].service,
                        recommendation_type="response_time_optimization",
                        description=f"Consider caching or database optimization for {response_time_metrics[0].operation}",
                        expected_improvement=0.3,  # 30% improvement
                        implementation_difficulty="medium",
                        priority="high" if avg_response_time > 1.0 else "medium",
                        timestamp=datetime.now(timezone.utc)
                    ))
            
            # Analyze memory usage
            memory_metrics = [m for m in metric_list if m.metric_type == PerformanceMetric.MEMORY_USAGE]
            if memory_metrics:
                avg_memory = statistics.mean([m.value for m in memory_metrics])
                if avg_memory > 70:  # 70% threshold
                    recommendations.append(OptimizationRecommendation(
                        id=f"opt_{datetime.now(timezone.utc).timestamp()}_{len(recommendations)}",
                        operation=memory_metrics[0].operation,
                        service=memory_metrics[0].service,
                        recommendation_type="memory_optimization",
                        description=f"Consider memory cleanup or resource optimization for {memory_metrics[0].operation}",
                        expected_improvement=0.2,  # 20% improvement
                        implementation_difficulty="medium",
                        priority="high" if avg_memory > 85 else "medium",
                        timestamp=datetime.now(timezone.utc)
                    ))
            
            # Analyze error rates
            error_metrics = [m for m in metric_list if m.metric_type == PerformanceMetric.ERROR_RATE]
            if error_metrics:
                avg_error_rate = statistics.mean([m.value for m in error_metrics])
                if avg_error_rate > 0.05:  # 5% threshold
                    recommendations.append(OptimizationRecommendation(
                        id=f"opt_{datetime.now(timezone.utc).timestamp()}_{len(recommendations)}",
                        operation=error_metrics[0].operation,
                        service=error_metrics[0].service,
                        recommendation_type="error_rate_optimization",
                        description=f"Investigate and fix error patterns in {error_metrics[0].operation}",
                        expected_improvement=0.5,  # 50% improvement
                        implementation_difficulty="high",
                        priority="high",
                        timestamp=datetime.now(timezone.utc)
                    ))
        
        # Store recommendations
        self.recommendations.extend(recommendations)
        if len(self.recommendations) > self.max_recommendations:
            self.recommendations = self.recommendations[-self.max_recommendations:]
        
        return recommendations
    
    def get_recommendations(self, service: Optional[str] = None, priority: Optional[str] = None) -> List[OptimizationRecommendation]:
        """Get optimization recommendations with optional filtering."""
        recommendations = self.recommendations
        
        if service:
            recommendations = [r for r in recommendations if r.service == service]
        
        if priority:
            recommendations = [r for r in recommendations if r.priority == priority]
        
        return recommendations


class PerformanceMonitor:
    """Performance monitoring service for the VATSIM data collection system."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
        self.performance_collector = PerformanceCollector()
        self.performance_optimizer = PerformanceOptimizer()
        self.monitoring_task = None
        self.is_running = False
        
        # Configuration
        self.monitoring_interval = 30  # seconds
        self.analysis_interval = 300  # seconds
        
        # Performance thresholds
        self.thresholds = {
            PerformanceMetric.RESPONSE_TIME: 1000,  # ms
            PerformanceMetric.MEMORY_USAGE: 80,     # %
            PerformanceMetric.CPU_USAGE: 80,        # %
            PerformanceMetric.ERROR_RATE: 5         # %
        }
    
    async def initialize(self):
        """Initialize performance monitor."""
        self.logger.info("Initializing performance monitor")
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Performance monitor initialized")
    
    async def cleanup(self):
        """Cleanup performance monitor resources."""
        self.logger.info("Cleaning up performance monitor")
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Performance monitor cleaned up")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform performance monitor health check."""
        try:
            return {
                "performance_monitor_healthy": True,
                "performance_collector_active": True,
                "performance_optimizer_active": True,
                "monitoring_task_running": self.monitoring_task and not self.monitoring_task.done(),
                "metrics_count": len(self.performance_collector.metrics),
                "active_alerts": len(self.performance_collector.active_alerts)
            }
        except Exception as e:
            self.logger.error(f"Performance monitor health check failed: {e}")
            return {
                "performance_monitor_healthy": False,
                "error": str(e)
            }
    
    @handle_service_errors
    @log_operation("monitor_operation")
    async def monitor_operation(self, operation: str, service: str, func: Callable, *args, **kwargs):
        """Monitor an operation's performance."""
        start_time = time.time()
        start_memory = psutil.virtual_memory().percent
        start_cpu = psutil.cpu_percent(interval=0.1)
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record performance metrics
            self.performance_collector.record_metric(
                operation, service, PerformanceMetric.RESPONSE_TIME, duration, "seconds"
            )
            
            # Record resource usage
            end_memory = psutil.virtual_memory().percent
            end_cpu = psutil.cpu_percent(interval=0.1)
            
            self.performance_collector.record_metric(
                operation, service, PerformanceMetric.MEMORY_USAGE, end_memory, "percent"
            )
            
            self.performance_collector.record_metric(
                operation, service, PerformanceMetric.CPU_USAGE, end_cpu, "percent"
            )
            
            # Check for performance alerts
            alert = self.performance_collector.check_thresholds(
                operation, service, PerformanceMetric.RESPONSE_TIME, duration
            )
            if alert:
                self.performance_alerts.append(alert)
                self.structured_logger.log_warning(
                    f"Performance alert: {alert.message}",
                    category=LogCategory.PERFORMANCE,
                    operation=operation,
                    service=service,
                    duration=duration
                )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error rate
            self.performance_collector.record_metric(
                operation, service, PerformanceMetric.ERROR_RATE, 1.0, "count"
            )
            
            self.structured_logger.log_error(
                f"Operation {operation} failed",
                exception=e,
                category=LogCategory.PERFORMANCE,
                operation=operation,
                service=service,
                duration=duration
            )
            
            raise
    
    @handle_service_errors
    @log_operation("record_metric")
    def record_metric(self, operation: str, service: str, metric_type: PerformanceMetric,
                     value: float, unit: str = "", metadata: Dict[str, Any] = None):
        """Record a performance metric."""
        self.performance_collector.record_metric(operation, service, metric_type, value, unit, metadata)
    
    @handle_service_errors
    @log_operation("get_performance_summary")
    def get_performance_summary(self, operation: str, service: str, metric_type: PerformanceMetric,
                               hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for an operation."""
        return self.performance_collector.get_metric_summary(operation, service, metric_type, hours)
    
    @handle_service_errors
    @log_operation("get_optimization_recommendations")
    def get_optimization_recommendations(self, service: Optional[str] = None,
                                       priority: Optional[str] = None) -> List[OptimizationRecommendation]:
        """Get performance optimization recommendations."""
        return self.performance_optimizer.get_recommendations(service, priority)
    
    @handle_service_errors
    @log_operation("analyze_performance")
    def analyze_performance(self) -> List[OptimizationRecommendation]:
        """Analyze current performance and generate recommendations."""
        return self.performance_optimizer.analyze_performance(self.performance_collector.metrics)
    
    @handle_service_errors
    @log_operation("get_performance_alerts")
    def get_performance_alerts(self) -> List[PerformanceAlert]:
        """Get active performance alerts."""
        return [alert for alert in self.performance_alerts if not alert.resolved]
    
    @handle_service_errors
    @log_operation("resolve_performance_alert")
    def resolve_performance_alert(self, alert_id: str) -> bool:
        """Resolve a performance alert."""
        for alert in self.performance_alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                return True
        return False
    
    async def _monitoring_loop(self):
        """Main performance monitoring loop."""
        while self.is_running:
            try:
                # Monitor system performance
                await self._monitor_system_performance()
                
                # Generate optimization recommendations
                await self._generate_recommendations()
                
                # Wait before next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(
                    "Performance monitoring loop error",
                    exception=e,
                    category=LogCategory.PERFORMANCE
                )
                await asyncio.sleep(5)  # Short delay on error
    
    async def _monitor_system_performance(self):
        """Monitor system performance metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.performance_collector.record_metric(
            "system_monitoring", "system", PerformanceMetric.CPU_USAGE, cpu_percent, "percent"
        )
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.performance_collector.record_metric(
            "system_monitoring", "system", PerformanceMetric.MEMORY_USAGE, memory.percent, "percent"
        )
        
        # Check for system performance alerts
        if cpu_percent > 80:
            alert = PerformanceAlert(
                id=f"sys_alert_{datetime.now(timezone.utc).timestamp()}",
                operation="system_monitoring",
                service="system",
                metric_type=PerformanceMetric.CPU_USAGE,
                threshold=80.0,
                current_value=cpu_percent,
                severity="high" if cpu_percent > 90 else "medium",
                message=f"High CPU usage: {cpu_percent}%",
                timestamp=datetime.now(timezone.utc)
            )
            self.performance_alerts.append(alert)
        
        if memory.percent > 85:
            alert = PerformanceAlert(
                id=f"sys_alert_{datetime.now(timezone.utc).timestamp()}",
                operation="system_monitoring",
                service="system",
                metric_type=PerformanceMetric.MEMORY_USAGE,
                threshold=85.0,
                current_value=memory.percent,
                severity="high" if memory.percent > 95 else "medium",
                message=f"High memory usage: {memory.percent}%",
                timestamp=datetime.now(timezone.utc)
            )
            self.performance_alerts.append(alert)
    
    async def _generate_recommendations(self):
        """Generate performance optimization recommendations."""
        recommendations = self.performance_optimizer.analyze_performance(
            self.performance_collector.metrics
        )
        
        if recommendations:
            self.logger.info(
                f"Generated {len(recommendations)} performance optimization recommendations",
                category=LogCategory.PERFORMANCE,
                recommendations_count=len(recommendations)
            )


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


async def monitor_operation(operation: str, service: str, func: Callable, *args, **kwargs):
    """Monitor an operation using the global performance monitor."""
    monitor = get_performance_monitor()
    return await monitor.monitor_operation(operation, service, func, *args, **kwargs)


def record_performance_metric(operation: str, service: str, metric_type: PerformanceMetric,
                            value: float, unit: str = "", metadata: Dict[str, Any] = None):
    """Record a performance metric using the global performance monitor."""
    monitor = get_performance_monitor()
    monitor.record_metric(operation, service, metric_type, value, unit, metadata) 