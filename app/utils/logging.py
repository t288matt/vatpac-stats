#!/usr/bin/env python3
"""
Logging Configuration for VATSIM Data Collection System

This module provides structured logging following architecture principles
of maintainability and supportability. It implements JSON-structured logging
with context support for better debugging and monitoring.

INPUTS:
- Log level configuration (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Log format specifications (JSON, text)
- File path and rotation settings
- Context information for structured logging

OUTPUTS:
- Structured JSON log entries
- Rotated log files with size limits
- Context-aware log messages
- Exception tracking and stack traces
- Performance and monitoring logs

LOGGING FEATURES:
- Structured JSON logging for easy parsing
- Context-aware logging with variable binding
- Log file rotation with size limits
- Exception tracking with stack traces
- Performance monitoring integration
- Configurable log levels and formats

LOG LEVELS:
- DEBUG: Detailed debugging information
- INFO: General application information
- WARNING: Warning messages for potential issues
- ERROR: Error messages for recoverable issues
- CRITICAL: Critical errors requiring immediate attention

STRUCTURED LOGGING:
- JSON format for easy parsing and analysis
- Context variables for request tracking
- Timestamp and module information
- Exception details with stack traces
- Performance metrics and timing data

CONFIGURATION:
- Environment-based log level configuration
- File-based logging with rotation
- Console and file output support
- Custom formatters and handlers
- Context variable binding
"""

import logging
import logging.handlers
import sys
from typing import Optional
from datetime import datetime, timezone
import json
from pathlib import Path

from ..config import get_config


class StructuredFormatter(logging.Formatter):
    """
    Structured JSON formatter for consistent log output.
    
    This formatter creates structured JSON logs that are easy to parse
    and analyze, following our architecture principles.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields:
            log_entry.update(extra_fields)
        
        return json.dumps(log_entry, default=str)


class ContextLogger:
    """
    Logger with context support for structured logging.
    
    This logger allows adding context information to log messages,
    making debugging and monitoring easier.
    """
    
    def __init__(self, name: str):
        """Initialize context logger."""
        self.logger = logging.getLogger(name)
        self.context = {}
    
    def bind(self, **kwargs) -> 'ContextLogger':
        """
        Bind context variables to this logger.
        
        Args:
            **kwargs: Context variables to bind
            
        Returns:
            ContextLogger: Self for method chaining
        """
        self.context.update(kwargs)
        return self
    
    def _log_with_context(self, level: int, message: str, *args, **kwargs):
        """Log message with context information."""
        extra_fields = self.context.copy()
        if "extra" in kwargs:
            extra_fields.update(kwargs["extra"])
        
        kwargs["extra"] = {"extra_fields": extra_fields}
        self.logger.log(level, message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception message with context."""
        kwargs["exc_info"] = True
        self._log_with_context(logging.ERROR, message, *args, **kwargs)


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    file_path: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Set up application logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (uses structured JSON if None)
        file_path: Path to log file (optional)
        max_bytes: Maximum log file size in bytes
        backup_count: Number of backup files to keep
    """
    config = get_config()
    
    # Use config values if not provided
    if level == "INFO":
        level = config.logging.level
    if format_string is None:
        format_string = config.logging.format
    if file_path is None:
        file_path = config.logging.file_path
    if max_bytes == 10 * 1024 * 1024:
        max_bytes = config.logging.max_file_size
    if backup_count == 5:
        backup_count = config.logging.backup_count
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    if format_string == "json" or format_string is None:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if file_path:
        # Ensure log directory exists
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> ContextLogger:
    """
    Get a context logger for the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        ContextLogger: Logger with context support
    """
    return ContextLogger(name)


# Initialize logging on module import
setup_logging()


# Convenience function for getting logger
def get_logger_for_module(module_name: str) -> ContextLogger:
    """
    Get a logger for a specific module.
    
    Args:
        module_name: Name of the module (usually __name__)
        
    Returns:
        ContextLogger: Logger configured for the module
    """
    return get_logger(module_name) 
