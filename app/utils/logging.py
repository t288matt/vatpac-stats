#!/usr/bin/env python3
"""
Simple Logging Configuration for VATSIM Data Collection System

This module provides basic logging functionality without over-engineering.
It maintains the same interface as the previous complex logging system
but with simplified implementation.
"""

import logging
import logging.handlers
import sys
from typing import Optional
from pathlib import Path

from ..config import get_config


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    file_path: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Set up basic application logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (uses simple format if None)
        file_path: Path to log file (optional)
        max_bytes: Maximum log file size in bytes
        backup_count: Number of backup files to keep
    """
    config = get_config()
    
    # Use config values if not provided
    if level == "INFO":
        level = config.logging.level
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    # Simplified config - no file logging for now
    file_path = None
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create simple formatter
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


def get_logger(name: str) -> logging.Logger:
    """
    Get a standard logger for the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        logging.Logger: Standard Python logger
    """
    return logging.getLogger(name)


# Initialize logging on module import
setup_logging()


def get_logger_for_module(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        module_name: Name of the module (usually __name__)
        
    Returns:
        logging.Logger: Logger configured for the module
    """
    return get_logger(module_name) 
