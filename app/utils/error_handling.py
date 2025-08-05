#!/usr/bin/env python3
"""
Centralized Error Handling for VATSIM Data Collection System

This module provides standardized error handling patterns to eliminate
duplication across services and ensure consistent error management.
"""

import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
import asyncio

from .logging import get_logger_for_module

logger = get_logger_for_module(__name__)


class ServiceError(Exception):
    """Base exception for service layer errors."""
    
    def __init__(self, message: str, service: str, retryable: bool = True, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.service = service
        self.retryable = retryable
        self.details = details or {}


class DatabaseError(ServiceError):
    """Exception for database-related errors."""
    
    def __init__(self, message: str, operation: str, retryable: bool = True, details: Optional[Dict] = None):
        super().__init__(message, "database", retryable, details)
        self.operation = operation


class APIError(ServiceError):
    """Exception for API-related errors."""
    
    def __init__(self, message: str, endpoint: str, status_code: Optional[int] = None, retryable: bool = True):
        super().__init__(message, "api", retryable, {"endpoint": endpoint, "status_code": status_code})
        self.endpoint = endpoint
        self.status_code = status_code


class CacheError(ServiceError):
    """Exception for cache-related errors."""
    
    def __init__(self, message: str, operation: str, retryable: bool = True):
        super().__init__(message, "cache", retryable, {"operation": operation})
        self.operation = operation


def handle_service_errors(func: Callable) -> Callable:
    """Decorator for standardized service error handling."""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ServiceError as e:
            logger.error(f"Service error in {e.service}: {e.message}", extra=e.details)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise ServiceError(f"Unexpected error: {e}", "unknown", retryable=False)
    
    return wrapper


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retry logic on transient failures."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except ServiceError as e:
                    if not e.retryable:
                        raise
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                except Exception as e:
                    last_exception = ServiceError(f"Unexpected error: {e}", "unknown", retryable=False)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))
            
            raise last_exception
        
        return wrapper
    return decorator


def log_operation(operation_name: str):
    """Decorator for operation logging."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"Starting operation: {operation_name}")
            try:
                result = await func(*args, **kwargs)
                logger.info(f"Completed operation: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Failed operation: {operation_name} - {e}")
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
        return DatabaseError(message, operation, retryable=True)
    
    def handle_api_error(self, endpoint: str, error: Exception, status_code: Optional[int] = None) -> APIError:
        """Handle API errors with consistent logging."""
        message = f"API error for {endpoint}: {error}"
        self.logger.error(message, exc_info=True)
        return APIError(message, endpoint, status_code, retryable=True)
    
    def handle_cache_error(self, operation: str, error: Exception) -> CacheError:
        """Handle cache errors with consistent logging."""
        message = f"Cache error in {operation}: {error}"
        self.logger.error(message, exc_info=True)
        return CacheError(message, operation, retryable=True)
    
    def handle_generic_error(self, operation: str, error: Exception) -> ServiceError:
        """Handle generic errors with consistent logging."""
        message = f"Error in {operation}: {error}"
        self.logger.error(message, exc_info=True)
        return ServiceError(message, self.service_name, retryable=False)


def create_error_handler(service_name: str) -> ErrorHandler:
    """Factory function to create error handlers for services."""
    return ErrorHandler(service_name) 