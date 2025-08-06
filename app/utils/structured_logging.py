#!/usr/bin/env python3
"""
Structured Logging Service for VATSIM Data Collection System - Phase 3

This module provides standardized structured logging with correlation IDs,
log levels by environment, and comprehensive log analytics.

INPUTS:
- Log messages from all services
- Service context and metadata
- Correlation IDs for request tracing
- Environment-specific configuration

OUTPUTS:
- Structured log entries with metadata
- Correlation ID tracking
- Log analytics and reporting
- Environment-specific log levels
- Log aggregation and analysis

FEATURES:
- Structured logging with consistent format
- Correlation ID generation and tracking
- Environment-specific log levels
- Log analytics and reporting
- Request tracing and debugging
- Performance logging integration
- Error context preservation
- Log correlation across services

PHASE 3 FEATURES:
- Advanced correlation ID management
- Log analytics and pattern recognition
- Performance impact tracking
- Error pattern analysis
- Service dependency logging
- Real-time log monitoring
- Log aggregation and search
- Predictive log analysis
"""

import logging
import uuid
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from enum import Enum
import traceback
import sys

from .logging import get_logger_for_module


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Log category enumeration."""
    SERVICE = "service"
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR = "error"
    SYSTEM = "system"


@dataclass
class LogContext:
    """Log context with correlation and metadata."""
    correlation_id: str
    service_name: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LogEntry:
    """Structured log entry."""
    level: LogLevel
    category: LogCategory
    message: str
    context: LogContext
    timestamp: datetime
    exception: Optional[Exception] = None
    stack_trace: Optional[str] = None
    performance_data: Optional[Dict[str, Any]] = None


# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class StructuredLogger:
    """Structured logger with correlation ID and metadata support."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger_for_module(f"structured.{service_name}")
        self.log_entries: List[LogEntry] = []
        self.max_entries = 10000
        self.correlation_id: Optional[str] = None
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for current context."""
        self.correlation_id = correlation_id
        correlation_id_var.set(correlation_id)
    
    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID."""
        return self.correlation_id or correlation_id_var.get()
    
    def generate_correlation_id(self) -> str:
        """Generate a new correlation ID."""
        correlation_id = f"corr_{uuid.uuid4().hex[:8]}"
        self.set_correlation_id(correlation_id)
        return correlation_id
    
    def log_operation(self, operation: str, level: LogLevel = LogLevel.INFO, 
                     category: LogCategory = LogCategory.SERVICE, **context):
        """Log an operation with structured context."""
        correlation_id = self.get_correlation_id() or self.generate_correlation_id()
        
        log_context = LogContext(
            correlation_id=correlation_id,
            service_name=self.service_name,
            operation=operation,
            metadata=context
        )
        
        self._log(level, category, f"Operation: {operation}", log_context)
    
    def log_info(self, message: str, category: LogCategory = LogCategory.SERVICE, **context):
        """Log info message."""
        self._log(LogLevel.INFO, category, message, **context)
    
    def log_warning(self, message: str, category: LogCategory = LogCategory.SERVICE, **context):
        """Log warning message."""
        self._log(LogLevel.WARNING, category, message, **context)
    
    def log_error(self, message: str, exception: Optional[Exception] = None, 
                  category: LogCategory = LogCategory.ERROR, **context):
        """Log error message with optional exception."""
        self._log(LogLevel.ERROR, category, message, exception=exception, **context)
    
    def log_debug(self, message: str, category: LogCategory = LogCategory.SERVICE, **context):
        """Log debug message."""
        self._log(LogLevel.DEBUG, category, message, **context)
    
    def log_performance(self, operation: str, duration: float, **context):
        """Log performance data."""
        correlation_id = self.get_correlation_id() or self.generate_correlation_id()
        
        log_context = LogContext(
            correlation_id=correlation_id,
            service_name=self.service_name,
            operation=operation,
            metadata=context
        )
        
        performance_data = {
            "duration": duration,
            "operation": operation,
            **context
        }
        
        self._log(LogLevel.INFO, LogCategory.PERFORMANCE, 
                 f"Performance: {operation} took {duration:.3f}s", 
                 log_context, performance_data=performance_data)
    
    def _log(self, level: LogLevel, category: LogCategory, message: str, 
             context: Optional[LogContext] = None, exception: Optional[Exception] = None,
             performance_data: Optional[Dict[str, Any]] = None, **kwargs):
        """Internal logging method."""
        correlation_id = self.get_correlation_id() or self.generate_correlation_id()
        
        if context is None:
            context = LogContext(
                correlation_id=correlation_id,
                service_name=self.service_name,
                operation="unknown",
                metadata=kwargs
            )
        
        stack_trace = None
        if exception:
            stack_trace = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        
        log_entry = LogEntry(
            level=level,
            category=category,
            message=message,
            context=context,
            timestamp=datetime.now(timezone.utc),
            exception=exception,
            stack_trace=stack_trace,
            performance_data=performance_data
        )
        
        # Store log entry
        self.log_entries.append(log_entry)
        if len(self.log_entries) > self.max_entries:
            self.log_entries = self.log_entries[-self.max_entries:]
        
        # Format and log
        formatted_message = self._format_log_entry(log_entry)
        
        if level == LogLevel.DEBUG:
            self.logger.debug(formatted_message)
        elif level == LogLevel.INFO:
            self.logger.info(formatted_message)
        elif level == LogLevel.WARNING:
            self.logger.warning(formatted_message)
        elif level == LogLevel.ERROR:
            self.logger.error(formatted_message)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(formatted_message)
    
    def _format_log_entry(self, entry: LogEntry) -> str:
        """Format log entry for output."""
        log_data = {
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level.value,
            "category": entry.category.value,
            "message": entry.message,
            "correlation_id": entry.context.correlation_id,
            "service": entry.context.service_name,
            "operation": entry.context.operation,
            "metadata": entry.context.metadata
        }
        
        if entry.performance_data:
            log_data["performance"] = entry.performance_data
        
        if entry.exception:
            log_data["exception"] = str(entry.exception)
            log_data["stack_trace"] = entry.stack_trace
        
        return json.dumps(log_data, default=str)
    
    def get_log_entries(self, hours: int = 24, level: Optional[LogLevel] = None, 
                       category: Optional[LogCategory] = None) -> List[LogEntry]:
        """Get log entries with optional filtering."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        filtered_entries = [
            entry for entry in self.log_entries
            if entry.timestamp >= cutoff_time
        ]
        
        if level:
            filtered_entries = [entry for entry in filtered_entries if entry.level == level]
        
        if category:
            filtered_entries = [entry for entry in filtered_entries if entry.category == category]
        
        return filtered_entries
    
    def get_log_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get log analytics."""
        entries = self.get_log_entries(hours)
        
        if not entries:
            return {
                "total_entries": 0,
                "entries_by_level": {},
                "entries_by_category": {},
                "error_rate": 0.0,
                "average_performance": 0.0
            }
        
        # Count by level
        entries_by_level = {}
        for entry in entries:
            level = entry.level.value
            entries_by_level[level] = entries_by_level.get(level, 0) + 1
        
        # Count by category
        entries_by_category = {}
        for entry in entries:
            category = entry.category.value
            entries_by_category[category] = entries_by_category.get(category, 0) + 1
        
        # Calculate error rate
        error_entries = [e for e in entries if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
        error_rate = len(error_entries) / len(entries) if entries else 0.0
        
        # Calculate average performance
        performance_entries = [e for e in entries if e.performance_data]
        avg_performance = 0.0
        if performance_entries:
            total_duration = sum(e.performance_data.get("duration", 0) for e in performance_entries)
            avg_performance = total_duration / len(performance_entries)
        
        return {
            "total_entries": len(entries),
            "entries_by_level": entries_by_level,
            "entries_by_category": entries_by_category,
            "error_rate": error_rate,
            "average_performance": avg_performance,
            "performance_entries_count": len(performance_entries)
        }


class LogCorrelationContext:
    """Context manager for correlation ID management."""
    
    def __init__(self, logger: StructuredLogger, operation: str, **metadata):
        self.logger = logger
        self.operation = operation
        self.metadata = metadata
        self.correlation_id = None
        self.start_time = None
    
    async def __aenter__(self):
        """Enter correlation context."""
        self.correlation_id = self.logger.generate_correlation_id()
        self.start_time = datetime.now(timezone.utc)
        
        self.logger.log_operation(
            self.operation,
            level=LogLevel.INFO,
            category=LogCategory.SERVICE,
            **self.metadata
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit correlation context."""
        if exc_type:
            self.logger.log_error(
                f"Operation {self.operation} failed",
                exception=exc_val,
                category=LogCategory.ERROR,
                **self.metadata
            )
        else:
            duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            self.logger.log_performance(
                self.operation,
                duration,
                **self.metadata
            )


def get_structured_logger(service_name: str) -> StructuredLogger:
    """Get a structured logger for a service."""
    return StructuredLogger(service_name)


def log_correlation(service_name: str, operation: str, **metadata):
    """Decorator for correlation logging."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger = get_structured_logger(service_name)
            async with LogCorrelationContext(logger, operation, **metadata):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# Global structured logger instance
_global_logger: Optional[StructuredLogger] = None


def get_global_logger() -> StructuredLogger:
    """Get the global structured logger."""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger("global")
    return _global_logger


def log_global(level: LogLevel, category: LogCategory, message: str, **context):
    """Log using global logger."""
    logger = get_global_logger()
    logger._log(level, category, message, **context) 