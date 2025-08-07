#!/usr/bin/env python3
"""
Centralized Error Handling for VATSIM Data Collection System

This module provides standardized error handling patterns to eliminate
duplication across services and ensure consistent error management.
"""

import logging
import traceback
import asyncio
from typing import Dict, Any, Optional, Callable, Type, Union
from functools import wraps
from datetime import datetime, timezone, timedelta, timezone
import time

from .logging import get_logger_for_module
from .exceptions import (
    VATSIMSystemError, DatabaseError, APIError, CacheError, 
    ConfigurationError, ConnectionError, DataProcessingError,
    ValidationError, ServiceError, ResourceError, TimeoutError,
    NetworkError, SecurityError, MaintenanceError, create_error
)

logger = get_logger_for_module(__name__)


class ErrorContext:
    """Context manager for error handling with additional context."""
    
    def __init__(self, operation: str, service: str = None, **context):
        self.operation = operation
        self.service = service
        self.context = context
        self.start_time = time.time()
        self.error_count = 0
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error_count += 1
            duration = time.time() - self.start_time
            logger.error(
                f"Error in {self.operation} after {duration:.2f}s",
                extra={
                    "operation": self.operation,
                    "service": self.service,
                    "duration": duration,
                    "error_count": self.error_count,
                    **self.context
                },
                exc_info=True
            )
        return False


class ErrorTracker:
    """Track error patterns and provide analytics."""
    
    def __init__(self):
        self.error_counts = {}
        self.error_timestamps = {}
        self.service_errors = {}
    
    def record_error(self, error_type: str, service: str = None, operation: str = None):
        """Record an error occurrence."""
        key = f"{error_type}:{service}:{operation}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        self.error_timestamps[key] = datetime.now(timezone.utc)
        
        if service:
            if service not in self.service_errors:
                self.service_errors[service] = {}
            self.service_errors[service][error_type] = self.service_errors[service].get(error_type, 0) + 1
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary for monitoring."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts,
            "service_errors": self.service_errors,
            "recent_errors": {
                k: v for k, v in self.error_timestamps.items()
                if datetime.now(timezone.utc) - v < timedelta(hours=1)
            }
        }


# Global error tracker
error_tracker = ErrorTracker()


def handle_service_errors(func: Callable) -> Callable:
    """Decorator for standardized service error handling."""
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        operation = func.__name__
        service = getattr(args[0], 'service_name', 'unknown') if args else 'unknown'
        
        try:
            return await func(*args, **kwargs)
        except VATSIMSystemError as e:
            error_tracker.record_error(e.__class__.__name__, service, operation)
            logger.error(f"Service error in {service}: {e.message}", extra=e.details)
            raise
        except Exception as e:
            error_tracker.record_error("UnexpectedError", service, operation)
            logger.error(f"Unexpected error in {operation}: {e}", exc_info=True)
            raise create_error("service", f"Unexpected error: {e}", service_name=service, operation=operation)
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        operation = func.__name__
        service = getattr(args[0], 'service_name', 'unknown') if args else 'unknown'
        
        try:
            return func(*args, **kwargs)
        except VATSIMSystemError as e:
            error_tracker.record_error(e.__class__.__name__, service, operation)
            logger.error(f"Service error in {service}: {e.message}", extra=e.details)
            raise
        except Exception as e:
            error_tracker.record_error("UnexpectedError", service, operation)
            logger.error(f"Unexpected error in {operation}: {e}", exc_info=True)
            raise create_error("service", f"Unexpected error: {e}", service_name=service, operation=operation)
    
    # Return async wrapper for async functions, sync wrapper for sync functions
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def retry_on_failure(
    max_retries: int = 3, 
    delay: float = 1.0, 
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (VATSIMSystemError,),
    max_delay: float = 60.0
):
    """Decorator for retry logic on transient failures."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    if not getattr(e, 'retryable', True):
                        raise
                    
                    last_exception = e
                    if attempt < max_retries:
                        # Exponential backoff with jitter
                        jitter = (0.5 + asyncio.get_event_loop().time() % 1) * 0.1
                        sleep_time = min(current_delay * (backoff_factor ** attempt) + jitter, max_delay)
                        
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {sleep_time:.2f}s",
                            extra={
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "delay": sleep_time,
                                "error": str(e)
                            }
                        )
                        
                        await asyncio.sleep(sleep_time)
                    else:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                        raise
                except Exception as e:
                    last_exception = create_error("service", f"Unexpected error: {e}", operation=func.__name__)
                    if attempt < max_retries:
                        await asyncio.sleep(current_delay * (backoff_factor ** attempt))
            
            raise last_exception
        
        return wrapper
    return decorator


def log_operation(operation_name: str, log_args: bool = False, log_result: bool = False):
    """Decorator for operation logging."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            service = getattr(args[0], 'service_name', 'unknown') if args else 'unknown'
            
            # Log operation start
            log_data = {
                "operation": operation_name,
                "service": service,
                "start_time": datetime.now(timezone.utc).isoformat()
            }
            
            if log_args:
                log_data["args"] = str(args[1:]) if len(args) > 1 else "[]"
                log_data["kwargs"] = str(kwargs)
            
            logger.info(f"Starting operation: {operation_name}", extra=log_data)
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log operation completion
                completion_data = {
                    "operation": operation_name,
                    "service": service,
                    "duration": duration,
                    "status": "success"
                }
                
                if log_result:
                    completion_data["result"] = str(result)[:200]  # Truncate long results
                
                logger.info(f"Completed operation: {operation_name} in {duration:.2f}s", extra=completion_data)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Failed operation: {operation_name} after {duration:.2f}s - {e}",
                    extra={
                        "operation": operation_name,
                        "service": service,
                        "duration": duration,
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            service = getattr(args[0], 'service_name', 'unknown') if args else 'unknown'
            
            # Log operation start
            log_data = {
                "operation": operation_name,
                "service": service,
                "start_time": datetime.now(timezone.utc).isoformat()
            }
            
            if log_args:
                log_data["args"] = str(args[1:]) if len(args) > 1 else "[]"
                log_data["kwargs"] = str(kwargs)
            
            logger.info(f"Starting operation: {operation_name}", extra=log_data)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log operation completion
                completion_data = {
                    "operation": operation_name,
                    "service": service,
                    "duration": duration,
                    "status": "success"
                }
                
                if log_result:
                    completion_data["result"] = str(result)[:200]  # Truncate long results
                
                logger.info(f"Completed operation: {operation_name} in {duration:.2f}s", extra=completion_data)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Failed operation: {operation_name} after {duration:.2f}s - {e}",
                    extra={
                        "operation": operation_name,
                        "service": service,
                        "duration": duration,
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
        
        # Return async wrapper for async functions, sync wrapper for sync functions
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
):
    """Circuit breaker pattern to prevent cascading failures."""
    
    def decorator(func: Callable) -> Callable:
        failure_count = 0
        last_failure_time = 0
        circuit_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal failure_count, last_failure_time, circuit_state
            
            current_time = time.time()
            
            # Check if circuit is open and recovery timeout has passed
            if circuit_state == "OPEN":
                if current_time - last_failure_time >= recovery_timeout:
                    circuit_state = "HALF_OPEN"
                    logger.info(f"Circuit breaker for {func.__name__} moved to HALF_OPEN")
                else:
                    raise create_error(
                        "service", 
                        f"Circuit breaker is OPEN for {func.__name__}",
                        service_name="circuit_breaker",
                        operation=func.__name__
                    )
            
            try:
                result = await func(*args, **kwargs)
                
                # Success - reset failure count and close circuit
                if circuit_state == "HALF_OPEN":
                    circuit_state = "CLOSED"
                    logger.info(f"Circuit breaker for {func.__name__} moved to CLOSED")
                
                failure_count = 0
                return result
                
            except expected_exception as e:
                failure_count += 1
                last_failure_time = current_time
                
                if failure_count >= failure_threshold:
                    circuit_state = "OPEN"
                    logger.error(
                        f"Circuit breaker for {func.__name__} moved to OPEN after {failure_count} failures"
                    )
                
                raise
        
        return wrapper
    return decorator


class ErrorHandler:
    """Centralized error handling utility."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger_for_module(f"services.{service_name}")
    
    def handle_database_error(self, operation: str, error: Exception) -> DatabaseError:
        """Handle database errors with consistent logging."""
        message = f"Database error in {operation}: {error}"
        self.logger.error(message, exc_info=True)
        return DatabaseError(message, operation)
    
    def handle_api_error(self, endpoint: str, error: Exception, status_code: Optional[int] = None) -> APIError:
        """Handle API errors with consistent logging."""
        message = f"API error for {endpoint}: {error}"
        self.logger.error(message, exc_info=True)
        return APIError(message, endpoint, status_code)
    
    def handle_cache_error(self, operation: str, error: Exception) -> CacheError:
        """Handle cache errors with consistent logging."""
        message = f"Cache error in {operation}: {error}"
        self.logger.error(message, exc_info=True)
        return CacheError(message, operation)
    
    def handle_generic_error(self, operation: str, error: Exception) -> ServiceError:
        """Handle generic errors with consistent logging."""
        message = f"Error in {operation}: {error}"
        self.logger.error(message, exc_info=True)
        return ServiceError(message, self.service_name)
    
    def handle_validation_error(self, field: str, value: Any, message: str) -> ValidationError:
        """Handle validation errors with consistent logging."""
        error_msg = f"Validation error for {field}: {message}"
        self.logger.warning(error_msg, extra={"field": field, "value": str(value)})
        return ValidationError(error_msg, field, value)
    
    def handle_timeout_error(self, operation: str, timeout_seconds: float) -> TimeoutError:
        """Handle timeout errors with consistent logging."""
        message = f"Timeout in {operation} after {timeout_seconds}s"
        self.logger.error(message)
        return TimeoutError(message, operation, timeout_seconds)
    
    def handle_resource_error(self, resource_type: str, current_usage: float, threshold: float) -> ResourceError:
        """Handle resource errors with consistent logging."""
        message = f"Resource limit exceeded: {resource_type} usage {current_usage} > {threshold}"
        self.logger.error(message)
        return ResourceError(message, resource_type, current_usage, threshold)


def create_error_handler(service_name: str) -> ErrorHandler:
    """Factory function to create error handlers for services."""
    return ErrorHandler(service_name)


def get_error_summary() -> Dict[str, Any]:
    """Get current error summary for monitoring."""
    return error_tracker.get_error_summary()


def clear_error_tracking():
    """Clear error tracking data (useful for testing)."""
    global error_tracker
    error_tracker = ErrorTracker()


 
