#!/usr/bin/env python3
"""
Error Handling - Simplified

Basic decorators for service error handling and operation logging.
"""

import asyncio
import logging
from typing import Callable
from functools import wraps

from app.utils.logging import get_logger_for_module

logger = get_logger_for_module(__name__)


def handle_service_errors(func: Callable) -> Callable:
    """Basic decorator for service error handling."""
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Service error in {func.__name__}: {e}")
            # Fail fast on critical database errors
            if "UniqueViolation" in str(e) or "duplicate key value violates unique constraint" in str(e):
                logger.critical(f"Database constraint violation in {func.__name__} - failing fast")
                raise
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Service error in {func.__name__}: {e}")
            # Fail fast on critical database errors
            if "UniqueViolation" in str(e) or "duplicate key value violates unique constraint" in str(e):
                logger.critical(f"Database constraint violation in {func.__name__} - failing fast")
                raise
            raise
    
    # Return async wrapper for async functions, sync wrapper for sync functions
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def log_operation(operation_name: str):
    """Basic decorator for operation logging."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.info(f"Starting operation: {operation_name}")
            try:
                result = await func(*args, **kwargs)
                logger.info(f"Completed operation: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Failed operation: {operation_name} - {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.info(f"Starting operation: {operation_name}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"Completed operation: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Failed operation: {operation_name} - {e}")
                raise
        
        # Return async wrapper for async functions, sync wrapper for sync functions
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def fail_fast_on_critical_errors(func: Callable) -> Callable:
    """Decorator that makes the application fail fast on critical database errors."""
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Check for critical database errors
            if "UniqueViolation" in str(e) or "duplicate key value violates unique constraint" in str(e):
                logger.critical(f"CRITICAL: Database constraint violation in {func.__name__} - Application will fail")
                # Re-raise to stop the application
                raise
            # For other errors, log and re-raise
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check for critical database errors
            if "UniqueViolation" in str(e) or "duplicate key value violates unique constraint" in str(e):
                logger.critical(f"CRITICAL: Database constraint violation in {func.__name__}: {e}")
                # Re-raise to stop the application
                raise
            # For other errors, log and re-raise
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    
    # Return async wrapper for async functions, sync wrapper for sync functions
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


 
