#!/usr/bin/env python3
"""
Centralized Error Monitoring for VATSIM Data Collection System

This module provides comprehensive error monitoring, analysis, and reporting
capabilities to track system health and identify patterns in errors.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics

from .error_handling import error_tracker, get_error_summary
from .exceptions import VATSIMSystemError
from .logging import get_logger_for_module

logger = get_logger_for_module(__name__)


class ErrorMonitor:
    """Centralized error monitoring and analysis."""
    
    def __init__(self, window_size: int = 1000, alert_threshold: int = 10):
        self.window_size = window_size
        self.alert_threshold = alert_threshold
        self.error_window = deque(maxlen=window_size)
        self.service_health = defaultdict(lambda: {"errors": 0, "last_error": None, "status": "healthy"})
        self.alert_callbacks = []
        self.monitoring_active = True
    
    def record_error(self, error: VATSIMSystemError, service: str = None, operation: str = None):
        """Record an error for monitoring."""
        if not self.monitoring_active:
            return
        
        error_record = {
            "timestamp": datetime.utcnow(),
            "error_type": error.__class__.__name__,
            "message": error.message,
            "service": service,
            "operation": operation,
            "error_code": getattr(error, 'error_code', None),
            "details": getattr(error, 'details', {})
        }
        
        self.error_window.append(error_record)
        
        # Update service health
        if service:
            self.service_health[service]["errors"] += 1
            self.service_health[service]["last_error"] = error_record["timestamp"]
            
            # Check if service should be marked as unhealthy
            if self.service_health[service]["errors"] >= self.alert_threshold:
                self.service_health[service]["status"] = "unhealthy"
                self._trigger_alert("service_unhealthy", service, error_record)
        
        # Check for error patterns
        self._analyze_error_patterns()
    
    def _analyze_error_patterns(self):
        """Analyze error patterns and trigger alerts if needed."""
        if len(self.error_window) < 10:
            return
        
        # Check for rapid error increase
        recent_errors = [e for e in self.error_window if 
                        datetime.utcnow() - e["timestamp"] < timedelta(minutes=5)]
        
        if len(recent_errors) >= self.alert_threshold:
            self._trigger_alert("error_spike", {
                "recent_errors": len(recent_errors),
                "threshold": self.alert_threshold,
                "time_window": "5 minutes"
            })
        
        # Check for specific error type spikes
        error_types = defaultdict(int)
        for error in recent_errors:
            error_types[error["error_type"]] += 1
        
        for error_type, count in error_types.items():
            if count >= self.alert_threshold // 2:  # Lower threshold for specific types
                self._trigger_alert("error_type_spike", {
                    "error_type": error_type,
                    "count": count,
                    "time_window": "5 minutes"
                })
    
    def _trigger_alert(self, alert_type: str, data: Dict[str, Any]):
        """Trigger alerts for error conditions."""
        alert = {
            "type": alert_type,
            "timestamp": datetime.utcnow(),
            "data": data
        }
        
        logger.warning(f"Error alert triggered: {alert_type}", extra=data)
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback for error alerts."""
        self.alert_callbacks.append(callback)
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get current service health status."""
        return dict(self.service_health)
    
    def get_error_statistics(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get error statistics for the specified time window."""
        cutoff_time = datetime.utcnow() - time_window
        recent_errors = [e for e in self.error_window if e["timestamp"] >= cutoff_time]
        
        if not recent_errors:
            return {
                "total_errors": 0,
                "error_types": {},
                "services": {},
                "operations": {},
                "average_errors_per_minute": 0
            }
        
        # Count by error type
        error_types = defaultdict(int)
        services = defaultdict(int)
        operations = defaultdict(int)
        
        for error in recent_errors:
            error_types[error["error_type"]] += 1
            if error["service"]:
                services[error["service"]] += 1
            if error["operation"]:
                operations[error["operation"]] += 1
        
        # Calculate average errors per minute
        time_span = (datetime.utcnow() - cutoff_time).total_seconds() / 60
        avg_errors_per_minute = len(recent_errors) / time_span if time_span > 0 else 0
        
        return {
            "total_errors": len(recent_errors),
            "error_types": dict(error_types),
            "services": dict(services),
            "operations": dict(operations),
            "average_errors_per_minute": round(avg_errors_per_minute, 2),
            "time_window_minutes": round(time_span, 2)
        }
    
    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get error trends over the specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_window if e["timestamp"] >= cutoff_time]
        
        if not recent_errors:
            return {"trends": [], "summary": "No errors in time window"}
        
        # Group errors by hour
        hourly_errors = defaultdict(int)
        for error in recent_errors:
            hour_key = error["timestamp"].replace(minute=0, second=0, microsecond=0)
            hourly_errors[hour_key] += 1
        
        # Calculate trends
        hours_list = sorted(hourly_errors.keys())
        error_counts = [hourly_errors[hour] for hour in hours_list]
        
        if len(error_counts) > 1:
            trend_direction = "increasing" if error_counts[-1] > error_counts[0] else "decreasing"
            trend_magnitude = abs(error_counts[-1] - error_counts[0])
        else:
            trend_direction = "stable"
            trend_magnitude = 0
        
        return {
            "trends": [
                {
                    "hour": hour.isoformat(),
                    "error_count": hourly_errors[hour]
                }
                for hour in hours_list
            ],
            "trend_direction": trend_direction,
            "trend_magnitude": trend_magnitude,
            "total_errors": len(recent_errors),
            "peak_errors_per_hour": max(error_counts) if error_counts else 0
        }
    
    def reset_monitoring(self):
        """Reset monitoring data (useful for testing)."""
        self.error_window.clear()
        self.service_health.clear()
        logger.info("Error monitoring reset")


class ErrorReporter:
    """Generate error reports for monitoring and analysis."""
    
    def __init__(self, monitor: ErrorMonitor):
        self.monitor = monitor
        self.logger = get_logger_for_module(__name__)
    
    async def generate_daily_report(self) -> Dict[str, Any]:
        """Generate a daily error report."""
        stats = self.monitor.get_error_statistics(timedelta(hours=24))
        trends = self.monitor.get_error_trends(24)
        service_health = self.monitor.get_service_health()
        
        # Identify top issues
        top_error_types = sorted(
            stats["error_types"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        top_services = sorted(
            stats["services"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(stats, trends, service_health)
        
        return {
            "report_type": "daily_error_report",
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_errors": stats["total_errors"],
                "average_errors_per_minute": stats["average_errors_per_minute"],
                "trend_direction": trends.get("trend_direction", "unknown"),
                "unhealthy_services": len([s for s in service_health.values() if s["status"] == "unhealthy"])
            },
            "top_error_types": top_error_types,
            "top_services": top_services,
            "service_health": service_health,
            "trends": trends,
            "recommendations": recommendations
        }
    
    def _generate_recommendations(self, stats: Dict, trends: Dict, service_health: Dict) -> List[str]:
        """Generate recommendations based on error analysis."""
        recommendations = []
        
        # High error rate
        if stats["average_errors_per_minute"] > 1.0:
            recommendations.append("High error rate detected - investigate system stability")
        
        # Increasing trend
        if trends.get("trend_direction") == "increasing":
            recommendations.append("Error trend is increasing - review recent changes")
        
        # Unhealthy services
        unhealthy_services = [name for name, health in service_health.items() 
                            if health["status"] == "unhealthy"]
        if unhealthy_services:
            recommendations.append(f"Unhealthy services detected: {', '.join(unhealthy_services)}")
        
        # Specific error types
        for error_type, count in stats["error_types"].items():
            if count > 10:
                recommendations.append(f"High frequency of {error_type} errors - investigate root cause")
        
        if not recommendations:
            recommendations.append("System appears healthy - continue monitoring")
        
        return recommendations
    
    async def generate_service_report(self, service_name: str) -> Dict[str, Any]:
        """Generate a detailed report for a specific service."""
        service_errors = [
            e for e in self.monitor.error_window 
            if e.get("service") == service_name
        ]
        
        if not service_errors:
            return {
                "service": service_name,
                "status": "healthy",
                "message": "No errors recorded for this service"
            }
        
        # Analyze service-specific errors
        error_types = defaultdict(int)
        operations = defaultdict(int)
        
        for error in service_errors:
            error_types[error["error_type"]] += 1
            if error["operation"]:
                operations[error["operation"]] += 1
        
        # Calculate error rate
        recent_errors = [e for e in service_errors 
                        if datetime.utcnow() - e["timestamp"] < timedelta(hours=1)]
        error_rate = len(recent_errors) / 60  # errors per minute
        
        return {
            "service": service_name,
            "status": "unhealthy" if error_rate > 0.1 else "healthy",
            "total_errors": len(service_errors),
            "error_rate_per_minute": round(error_rate, 3),
            "error_types": dict(error_types),
            "problematic_operations": dict(operations),
            "last_error": max(service_errors, key=lambda x: x["timestamp"])["timestamp"].isoformat(),
            "recommendations": self._generate_service_recommendations(error_types, operations, error_rate)
        }
    
    def _generate_service_recommendations(self, error_types: Dict, operations: Dict, error_rate: float) -> List[str]:
        """Generate service-specific recommendations."""
        recommendations = []
        
        if error_rate > 0.1:
            recommendations.append("High error rate - investigate service stability")
        
        # Check for specific error patterns
        for error_type, count in error_types.items():
            if count > 5:
                recommendations.append(f"Frequent {error_type} errors - review error handling")
        
        for operation, count in operations.items():
            if count > 3:
                recommendations.append(f"Operation '{operation}' failing frequently - investigate implementation")
        
        return recommendations


# Global error monitor instance
error_monitor = ErrorMonitor()
error_reporter = ErrorReporter(error_monitor)


def get_error_monitor() -> ErrorMonitor:
    """Get the global error monitor instance."""
    return error_monitor


def get_error_reporter() -> ErrorReporter:
    """Get the global error reporter instance."""
    return error_reporter


async def start_error_monitoring():
    """Start the error monitoring system."""
    logger.info("Starting error monitoring system")
    
    # Set up periodic reporting
    async def periodic_reporting():
        while True:
            try:
                # Generate daily report every hour
                report = await error_reporter.generate_daily_report()
                logger.info("Daily error report generated", extra=report["summary"])
                
                # Check for critical issues
                if report["summary"]["total_errors"] > 100:
                    logger.error("Critical error count detected", extra=report["summary"])
                
                await asyncio.sleep(3600)  # Report every hour
                
            except Exception as e:
                logger.error(f"Error in periodic reporting: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    # Start monitoring task
    asyncio.create_task(periodic_reporting())
    logger.info("Error monitoring system started") 