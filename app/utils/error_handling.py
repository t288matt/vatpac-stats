#!/usr/bin/env python3
"""
Simplified Error Handling for VATSIM Data Collection System

This module provides basic error handling decorators without complex
custom exception hierarchies.
"""

import asyncio
import logging
from typing import Callable
from functools import wraps

from .logging import get_logger_for_module

logger = get_logger_for_module(__name__)


class ErrorContext:
    """Context manager for error handling with additional context."""
    
    def __init__(self, operation: str, service: str = None, **context):
        self.operation = operation
        self.service = service
        self.context = context
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(
                f"Error in {self.operation}",
                extra={
                    "operation": self.operation,
                    "service": self.service,
                    **self.context
                },
                exc_info=True
            )
        return False


def handle_service_errors(func: Callable) -> Callable:
    """Basic decorator for service error handling."""
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Service error in {func.__name__}: {e}", exc_info=True)
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Service error in {func.__name__}: {e}", exc_info=True)
            raise
    
    # Return async wrapper for async functions, sync wrapper for sync functions
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def log_operation(operation_name: str, log_args: bool = False, log_result: bool = False):
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
                logger.error(f"Failed operation: {operation_name} - {e}", exc_info=True)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.info(f"Starting operation: {operation_name}")
            
            try:
                result = func(*args, **kwargs)
                logger.info(f"Completed operation: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Failed operation: {operation_name} - {e}", exc_info=True)
                raise
        
        # Return async wrapper for async functions, sync wrapper for sync functions
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


 
