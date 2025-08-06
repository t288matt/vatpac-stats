#!/usr/bin/env python3
"""
Centralized Exceptions for VATSIM Data Collection System

This module defines all custom exceptions used throughout the system
to provide consistent error handling and meaningful error messages.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


class VATSIMSystemError(Exception):
    """Base exception for all VATSIM system errors."""
    
    def __init__(self, message: str, error_code: str = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)


class ConfigurationError(VATSIMSystemError):
    """Exception for configuration-related errors."""
    
    def __init__(self, message: str, config_key: str = None, details: Optional[Dict] = None):
        super().__init__(message, "CONFIG_ERROR", details)
        self.config_key = config_key


class DatabaseError(VATSIMSystemError):
    """Exception for database-related errors."""
    
    def __init__(self, message: str, operation: str = None, table: str = None, details: Optional[Dict] = None):
        super().__init__(message, "DATABASE_ERROR", details)
        self.operation = operation
        self.table = table


class ConnectionError(VATSIMSystemError):
    """Exception for connection-related errors."""
    
    def __init__(self, message: str, service: str = None, endpoint: str = None, details: Optional[Dict] = None):
        super().__init__(message, "CONNECTION_ERROR", details)
        self.service = service
        self.endpoint = endpoint


class APIError(VATSIMSystemError):
    """Exception for API-related errors."""
    
    def __init__(self, message: str, endpoint: str = None, status_code: int = None, details: Optional[Dict] = None):
        super().__init__(message, "API_ERROR", details)
        self.endpoint = endpoint
        self.status_code = status_code


class CacheError(VATSIMSystemError):
    """Exception for cache-related errors."""
    
    def __init__(self, message: str, operation: str = None, key: str = None, details: Optional[Dict] = None):
        super().__init__(message, "CACHE_ERROR", details)
        self.operation = operation
        self.key = key


class DataProcessingError(VATSIMSystemError):
    """Exception for data processing errors."""
    
    def __init__(self, message: str, data_type: str = None, record_id: str = None, details: Optional[Dict] = None):
        super().__init__(message, "DATA_PROCESSING_ERROR", details)
        self.data_type = data_type
        self.record_id = record_id


class ValidationError(VATSIMSystemError):
    """Exception for data validation errors."""
    
    def __init__(self, message: str, field: str = None, value: Any = None, details: Optional[Dict] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value


class ServiceError(VATSIMSystemError):
    """Exception for service-related errors."""
    
    def __init__(self, message: str, service_name: str = None, operation: str = None, details: Optional[Dict] = None):
        super().__init__(message, "SERVICE_ERROR", details)
        self.service_name = service_name
        self.operation = operation


class ResourceError(VATSIMSystemError):
    """Exception for resource-related errors (memory, CPU, etc.)."""
    
    def __init__(self, message: str, resource_type: str = None, current_usage: float = None, threshold: float = None, details: Optional[Dict] = None):
        super().__init__(message, "RESOURCE_ERROR", details)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.threshold = threshold


class SystemError(VATSIMSystemError):
    """Exception for system-level errors."""
    
    def __init__(self, message: str, system_component: str = None, operation: str = None, details: Optional[Dict] = None):
        super().__init__(message, "SYSTEM_ERROR", details)
        self.system_component = system_component
        self.operation = operation


class TimeoutError(VATSIMSystemError):
    """Exception for timeout-related errors."""
    
    def __init__(self, message: str, operation: str = None, timeout_seconds: float = None, details: Optional[Dict] = None):
        super().__init__(message, "TIMEOUT_ERROR", details)
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class NetworkError(VATSIMSystemError):
    """Exception for network-related errors."""
    
    def __init__(self, message: str, network_operation: str = None, retry_count: int = None, details: Optional[Dict] = None):
        super().__init__(message, "NETWORK_ERROR", details)
        self.network_operation = network_operation
        self.retry_count = retry_count


class SecurityError(VATSIMSystemError):
    """Exception for security-related errors."""
    
    def __init__(self, message: str, security_type: str = None, details: Optional[Dict] = None):
        super().__init__(message, "SECURITY_ERROR", details)
        self.security_type = security_type


class MaintenanceError(VATSIMSystemError):
    """Exception for maintenance-related errors."""
    
    def __init__(self, message: str, maintenance_operation: str = None, details: Optional[Dict] = None):
        super().__init__(message, "MAINTENANCE_ERROR", details)
        self.maintenance_operation = maintenance_operation


# Error code constants for consistent error handling
ERROR_CODES = {
    # Configuration errors
    "MISSING_CONFIG": "CONFIG_001",
    "INVALID_CONFIG": "CONFIG_002",
    "ENV_VAR_MISSING": "CONFIG_003",
    
    # Database errors
    "DB_CONNECTION_FAILED": "DB_001",
    "DB_QUERY_FAILED": "DB_002",
    "DB_TRANSACTION_FAILED": "DB_003",
    "DB_TIMEOUT": "DB_004",
    
    # API errors
    "API_UNAVAILABLE": "API_001",
    "API_TIMEOUT": "API_002",
    "API_RATE_LIMIT": "API_003",
    "API_INVALID_RESPONSE": "API_004",
    
    # Cache errors
    "CACHE_CONNECTION_FAILED": "CACHE_001",
    "CACHE_OPERATION_FAILED": "CACHE_002",
    "CACHE_KEY_NOT_FOUND": "CACHE_003",
    
    # Data processing errors
    "DATA_PARSE_FAILED": "DATA_001",
    "DATA_VALIDATION_FAILED": "DATA_002",
    "DATA_TRANSFORM_FAILED": "DATA_003",
    
    # Service errors
    "SERVICE_INIT_FAILED": "SERVICE_001",
    "SERVICE_HEALTH_CHECK_FAILED": "SERVICE_002",
    "SERVICE_OPERATION_FAILED": "SERVICE_003",
    
    # Resource errors
    "MEMORY_LIMIT_EXCEEDED": "RESOURCE_001",
    "CPU_LIMIT_EXCEEDED": "RESOURCE_002",
    "DISK_SPACE_LOW": "RESOURCE_003",
    
    # Network errors
    "NETWORK_TIMEOUT": "NETWORK_001",
    "NETWORK_CONNECTION_FAILED": "NETWORK_002",
    "NETWORK_RETRY_EXHAUSTED": "NETWORK_003",
    
    # Security errors
    "AUTHENTICATION_FAILED": "SECURITY_001",
    "AUTHORIZATION_FAILED": "SECURITY_002",
    "INVALID_TOKEN": "SECURITY_003",
    
    # Maintenance errors
    "CLEANUP_FAILED": "MAINT_001",
    "BACKUP_FAILED": "MAINT_002",
    "RESTORE_FAILED": "MAINT_003",
}


def create_error(error_type: str, message: str, **kwargs) -> VATSIMSystemError:
    """
    Factory function to create appropriate exceptions based on error type.
    
    Args:
        error_type: Type of error (e.g., 'database', 'api', 'cache')
        message: Error message
        **kwargs: Additional error details
        
    Returns:
        VATSIMSystemError: Appropriate exception instance
    """
    error_type = error_type.lower()
    
    if error_type == 'database':
        return DatabaseError(message, **kwargs)
    elif error_type == 'api':
        return APIError(message, **kwargs)
    elif error_type == 'cache':
        return CacheError(message, **kwargs)
    elif error_type == 'config':
        return ConfigurationError(message, **kwargs)
    elif error_type == 'connection':
        return ConnectionError(message, **kwargs)
    elif error_type == 'data':
        return DataProcessingError(message, **kwargs)
    elif error_type == 'validation':
        return ValidationError(message, **kwargs)
    elif error_type == 'service':
        return ServiceError(message, **kwargs)
    elif error_type == 'resource':
        return ResourceError(message, **kwargs)
    elif error_type == 'timeout':
        return TimeoutError(message, **kwargs)
    elif error_type == 'network':
        return NetworkError(message, **kwargs)
    elif error_type == 'security':
        return SecurityError(message, **kwargs)
    elif error_type == 'maintenance':
        return MaintenanceError(message, **kwargs)
    else:
        return VATSIMSystemError(message, **kwargs) 
