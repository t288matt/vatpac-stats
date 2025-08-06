#!/usr/bin/env python3
"""
Database Connection and Session Management

This module provides database connection management for the VATSIM data collection
system. It handles PostgreSQL connection pooling, session management, and database
initialization with optimized settings for high-throughput data ingestion.

INPUTS:
- Environment variable DATABASE_URL for connection string
- SQLAlchemy model definitions
- Database session requests from application

OUTPUTS:
- Database engine with connection pooling
- Database sessions for data access
- Database initialization and table creation
- Connection monitoring and health information

FEATURES:
- Connection pooling (20 connections + 30 overflow)
- SSD-optimized PostgreSQL settings
- Automatic connection recycling (5 minutes)
- Connection health monitoring
- FastAPI dependency injection support

OPTIMIZATIONS:
- Disabled SQL logging for performance
- UTC timezone configuration
- Asynchronous commit for SSD optimization
- Connection pre-ping for reliability
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import os
from typing import Generator, AsyncGenerator
import logging

from .utils.error_handling import handle_service_errors, log_operation, create_error_handler
from .utils.logging import get_logger_for_module

# Configure logging
logger = get_logger_for_module(__name__)

# Initialize centralized error handler
error_handler = create_error_handler("database")

# Database configuration - PostgreSQL only
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data")

# PostgreSQL configuration for SSD preservation and memory caching
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Verify connections before use
    pool_recycle=180,        # Recycle connections every 3 minutes (reduced)
    pool_size=10,            # Reduced from 20 to 10 connections
    max_overflow=20,         # Reduced from 30 to 20 additional connections
    pool_timeout=60,         # Increased timeout to 60 seconds
    echo=False,              # Disable SQL logging for performance
    connect_args={
        "connect_timeout": 30,      # PostgreSQL connection timeout
        "application_name": "vatpac_stats",  # Application name for monitoring
        "options": "-c timezone=utc -c synchronous_commit=off"  # SSD optimization
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

async def get_db() -> AsyncGenerator[Session, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@handle_service_errors
@log_operation("init_db")
def init_db():
    """Initialize database tables"""
    # Import models to ensure they are registered with Base
    from .models import Controller, Sector, Flight, SystemConfig, Event, TrafficMovement, FlightSummary, MovementSummary, AirportConfig, MovementDetectionConfig, Transceiver, Airports
    Base.metadata.create_all(bind=engine)

@handle_service_errors
@log_operation("close_db")
def close_db():
    """Close database connections"""
    engine.dispose()

@handle_service_errors
@log_operation("get_database_info")
async def get_database_info():
    """Get database information for monitoring"""
    return {
        "database_type": "PostgreSQL",
        "connection_string": DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('://')[1], '***') if '@' in DATABASE_URL else DATABASE_URL,
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow()
    } 
