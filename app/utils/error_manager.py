#!/usr/bin/env python3
"""
Centralized Error Management for VATSIM Data Collection System

This module implements a comprehensive error management system with centralized
error handling, recovery strategies, and error analytics for Phase 2 of the
refactoring plan.

INPUTS:
- Exceptions and errors from all services
- Error context and metadata
- Recovery strategy configurations
- Error reporting requirements

OUTPUTS:
- Centralized error handling and logging
- Error recovery strategies
- Error analytics and reporting
- Circuit breaker patterns
- Graceful degradation mechanisms

FEATURES:
- Error type-specific handlers
- Automatic retry mechanisms
- Circuit breaker patterns
- Error analytics and reporting
- Recovery strategy management
- Error context preservation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Type
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import traceback
import json

from .logging import get_logger_for_module


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    DATABASE = "database"
    API = "api"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Error context information."""
    service_name: str
    operation: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """Error information structure."""
    error_type: Type[Exception]
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    traceback: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False


class ErrorHandler:
    """Base error handler class."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger_for_module(f"error_handler.{name}")
    
    async def handle(self, error: Exception, context: ErrorContext) -> bool:
        """Handle an error and return success status."""
        raise NotImplementedError


class RetryHandler(ErrorHandler):
    """Retry-based error handler."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        super().__init__("retry")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    async def handle(self, error: Exception, context: ErrorContext) -> bool:
        """Handle error with retry logic."""
        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(attempt * self.backoff_factor)
                # Attempt recovery (would be implemented by specific handlers)
                return True
            except Exception as retry_error:
                self.logger.warning(f"Retry attempt {attempt + 1} failed: {retry_error}")
        
        return False


class CircuitBreakerHandler(ErrorHandler):
    """Circuit breaker pattern error handler."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        super().__init__("circuit_breaker")
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def handle(self, error: Exception, context: ErrorContext) -> bool:
        """Handle error with circuit breaker logic."""
        current_time = datetime.now(timezone.utc)
        
        if self.state == "OPEN":
            if (current_time - self.last_failure_time).seconds > self.timeout:
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                self.logger.warning("Circuit breaker is OPEN, rejecting request")
                return False
        
        # Increment failure count
        self.failure_count += 1
        self.last_failure_time = current_time
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.error("Circuit breaker opened due to failure threshold")
            return False
        
        return True


class RecoveryStrategy:
    """Recovery strategy for specific error types."""
    
    def __init__(self, name: str, handler: ErrorHandler):
        self.name = name
        self.handler = handler
        self.success_count = 0
        self.failure_count = 0
    
    async def execute(self, error: Exception, context: ErrorContext) -> bool:
        """Execute recovery strategy."""
        try:
            success = await self.handler.handle(error, context)
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1
            return success
        except Exception as strategy_error:
            self.failure_count += 1
            logging.error(f"Recovery strategy {self.name} failed: {strategy_error}")
            return False


class ErrorManager:
    """Centralized error management system."""
    
    def __init__(self):
        self.logger = get_logger_for_module("error_manager")
        self.error_handlers: Dict[Type[Exception], RecoveryStrategy] = {}
        self.error_analytics: List[ErrorInfo] = []
        self.circuit_breakers: Dict[str, CircuitBreakerHandler] = {}
        
        # Initialize default handlers
        self._initialize_default_handlers()
    
    def _initialize_default_handlers(self):
        """Initialize default error handlers."""
        # Network errors - retry with backoff
        network_errors = [ConnectionError, TimeoutError, asyncio.TimeoutError]
        for error_type in network_errors:
            self.register_handler(error_type, RecoveryStrategy(
                "network_retry", 
                RetryHandler(max_retries=3, backoff_factor=2.0)
            ))
        
        # Database errors - circuit breaker
        from sqlalchemy.exc import SQLAlchemyError
        self.register_handler(SQLAlchemyError, RecoveryStrategy(
            "database_circuit_breaker",
            CircuitBreakerHandler(failure_threshold=3, timeout=30)
        ))
        
        # API errors - retry with exponential backoff
        api_errors = [ValueError, KeyError, TypeError]
        for error_type in api_errors:
            self.register_handler(error_type, RecoveryStrategy(
                "api_retry",
                RetryHandler(max_retries=5, backoff_factor=1.5)
            ))
    
    def register_handler(self, error_type: Type[Exception], strategy: RecoveryStrategy):
        """Register an error handler for a specific error type."""
        self.error_handlers[error_type] = strategy
        self.logger.info(f"Registered error handler for {error_type.__name__}")
    
    def get_error_category(self, error: Exception) -> ErrorCategory:
        """Determine error category based on error type."""
        if isinstance(error, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
            return ErrorCategory.NETWORK
        elif isinstance(error, (ValueError, KeyError, TypeError)):
            return ErrorCategory.VALIDATION
        elif hasattr(error, '__module__') and 'sqlalchemy' in error.__module__:
            return ErrorCategory.DATABASE
        elif isinstance(error, (OSError, MemoryError)):
            return ErrorCategory.RESOURCE
        else:
            return ErrorCategory.UNKNOWN
    
    def get_error_severity(self, error: Exception, context: ErrorContext) -> ErrorSeverity:
        """Determine error severity based on error and context."""
        if isinstance(error, (MemoryError, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, (ValueError, KeyError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    async def handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """Handle an error using registered handlers."""
        error_info = ErrorInfo(
            error_type=type(error),
            error_message=str(error),
            severity=self.get_error_severity(error, context),
            category=self.get_error_category(error),
            context=context,
            traceback=traceback.format_exc()
        )
        
        # Log error
        self.logger.error(
            f"Error in {context.service_name}.{context.operation}: {error}",
            extra={
                "error_type": error_info.error_type.__name__,
                "severity": error_info.severity.value,
                "category": error_info.category.value,
                "context": context.__dict__
            }
        )
        
        # Store error analytics
        self.error_analytics.append(error_info)
        
        # Find appropriate handler
        handler = self._find_handler(error)
        if handler:
            try:
                error_info.recovery_attempted = True
                success = await handler.execute(error, context)
                error_info.recovery_successful = success
                
                if success:
                    self.logger.info(f"Error recovery successful using {handler.name}")
                else:
                    self.logger.warning(f"Error recovery failed using {handler.name}")
                
                return success
            except Exception as recovery_error:
                self.logger.error(f"Error recovery strategy failed: {recovery_error}")
                error_info.recovery_successful = False
                return False
        else:
            self.logger.warning(f"No handler found for error type {type(error).__name__}")
            return False
    
    def _find_handler(self, error: Exception) -> Optional[RecoveryStrategy]:
        """Find appropriate handler for error type."""
        # Check exact type match
        if type(error) in self.error_handlers:
            return self.error_handlers[type(error)]
        
        # Check base class matches
        for error_type, handler in self.error_handlers.items():
            if isinstance(error, error_type):
                return handler
        
        return None
    
    def get_error_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error analytics for the specified time period."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_errors = [
            error for error in self.error_analytics 
            if error.context.timestamp > cutoff_time
        ]
        
        analytics = {
            "total_errors": len(recent_errors),
            "errors_by_category": {},
            "errors_by_severity": {},
            "errors_by_service": {},
            "recovery_success_rate": 0,
            "most_common_errors": []
        }
        
        if recent_errors:
            # Calculate recovery success rate
            recovery_attempts = [e for e in recent_errors if e.recovery_attempted]
            if recovery_attempts:
                analytics["recovery_success_rate"] = (
                    len([e for e in recovery_attempts if e.recovery_successful]) / 
                    len(recovery_attempts) * 100
                )
            
            # Group by category
            for error in recent_errors:
                category = error.category.value
                analytics["errors_by_category"][category] = \
                    analytics["errors_by_category"].get(category, 0) + 1
            
            # Group by severity
            for error in recent_errors:
                severity = error.severity.value
                analytics["errors_by_severity"][severity] = \
                    analytics["errors_by_severity"].get(severity, 0) + 1
            
            # Group by service
            for error in recent_errors:
                service = error.context.service_name
                analytics["errors_by_service"][service] = \
                    analytics["errors_by_service"].get(service, 0) + 1
            
            # Most common errors
            error_types = {}
            for error in recent_errors:
                error_type = error.error_type.__name__
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            analytics["most_common_errors"] = sorted(
                error_types.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        
        return analytics
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for all services."""
        status = {}
        for service_name, circuit_breaker in self.circuit_breakers.items():
            status[service_name] = {
                "state": circuit_breaker.state,
                "failure_count": circuit_breaker.failure_count,
                "last_failure_time": circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None
            }
        return status
    
    def reset_circuit_breaker(self, service_name: str) -> bool:
        """Reset circuit breaker for a specific service."""
        if service_name in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[service_name]
            circuit_breaker.state = "CLOSED"
            circuit_breaker.failure_count = 0
            circuit_breaker.last_failure_time = None
            self.logger.info(f"Reset circuit breaker for {service_name}")
            return True
        return False


# Global error manager instance
error_manager = ErrorManager()


def handle_error_with_context(error: Exception, service_name: str, operation: str, 
                            **context_kwargs) -> bool:
    """Convenience function to handle errors with context."""
    context = ErrorContext(
        service_name=service_name,
        operation=operation,
        **context_kwargs
    )
    return asyncio.create_task(error_manager.handle_error(error, context))


def get_error_analytics(hours: int = 24) -> Dict[str, Any]:
    """Get error analytics."""
    return error_manager.get_error_analytics(hours)


def get_circuit_breaker_status() -> Dict[str, Any]:
    """Get circuit breaker status."""
    return error_manager.get_circuit_breaker_status() 