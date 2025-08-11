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
- Connection pooling with optimized settings
- SSD-optimized PostgreSQL settings
- Automatic connection recycling
- Connection health monitoring
- FastAPI dependency injection support
- Robust error handling and retry logic

OPTIMIZATIONS:
- Disabled SQL logging for performance
- UTC timezone configuration
- Asynchronous commit for SSD optimization
- Connection pre-ping for reliability
- Optimized pool settings for high throughput
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError
import os
from typing import Generator, AsyncGenerator, Optional
import logging
import time
from contextlib import contextmanager
import asyncio

from .utils.error_handling import handle_service_errors, log_operation, create_error_handler
from .utils.logging import get_logger_for_module

# Configure logging
logger = get_logger_for_module(__name__)

# Initialize centralized error handler
error_handler = create_error_handler("database")

# Database configuration - PostgreSQL only
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data")

# Enhanced PostgreSQL configuration for high-throughput data ingestion
engine = create_engine(
    DATABASE_URL,
    # Connection pooling
    poolclass=QueuePool,
    pool_pre_ping=True,      # Verify connections before use
    pool_recycle=300,        # Recycle connections every 5 minutes
    pool_size=20,            # Increased for high throughput
    max_overflow=30,         # Additional connections when pool is full
    pool_timeout=30,         # Timeout for getting connection from pool
    pool_reset_on_return='commit',  # Reset connection state on return
    
    # Performance optimizations
    echo=False,              # Disable SQL logging for performance
    echo_pool=False,         # Disable pool logging
    future=True,             # Use SQLAlchemy 2.0 style
    
    # Connection settings
    connect_args={
        "connect_timeout": 30,      # PostgreSQL connection timeout
        "application_name": "vatsim_data_collector",  # Application name for monitoring
        "options": "-c timezone=utc -c synchronous_commit=off",  # SSD optimization
        "keepalives": 1,            # Enable TCP keepalives
        "keepalives_idle": 30,      # Start keepalives after 30 seconds of inactivity
        "keepalives_interval": 10,  # Send keepalives every 10 seconds
        "keepalives_count": 5,      # Give up after 5 failed keepalives
    }
)

# Create session factory with enhanced configuration
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Prevent expired object access issues
)

# Create scoped session for thread safety
ScopedSessionLocal = scoped_session(SessionLocal)

# Base class for models
Base = declarative_base()

# Connection event listeners for monitoring and optimization
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance (if using SQLite)"""
    if 'sqlite' in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

@event.listens_for(engine, "connect")
def set_postgresql_settings(dbapi_connection, connection_record):
    """Set PostgreSQL-specific settings for optimization"""
    if 'postgresql' in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("SET timezone = 'UTC'")
        cursor.execute("SET synchronous_commit = off")
        cursor.execute("SET work_mem = '256MB'")
        cursor.execute("SET maintenance_work_mem = '256MB'")
        cursor.execute("SET effective_cache_size = '1GB'")
        cursor.close()

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout for monitoring"""
    logger.debug(f"Database connection checked out. Pool size: {engine.pool.size()}, "
                f"Checked in: {engine.pool.checkedin()}, Checked out: {engine.pool.checkedout()}")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin for monitoring"""
    logger.debug(f"Database connection checked in. Pool size: {engine.pool.size()}, "
                f"Checked in: {engine.pool.checkedin()}, Checked out: {engine.pool.checkedout()}")

async def get_db() -> AsyncGenerator[Session, None]:
    """Dependency to get database session - FastAPI compatible"""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

class DatabaseSession:
    """Enhanced async context manager for database sessions with error handling"""
    def __init__(self):
        self.session = None
        self.retry_count = 0
        self.max_retries = 3
    
    async def __aenter__(self):
        """Get database session with retry logic"""
        while self.retry_count < self.max_retries:
            try:
                self.session = SessionLocal()
                # Test connection
                self.session.execute(text("SELECT 1"))
                return self.session
            except (DisconnectionError, OperationalError) as e:
                self.retry_count += 1
                logger.warning(f"Database connection attempt {self.retry_count} failed: {e}")
                if self.session:
                    self.session.close()
                if self.retry_count >= self.max_retries:
                    raise SQLAlchemyError(f"Failed to connect to database after {self.max_retries} attempts")
                await asyncio.sleep(1)  # Wait before retry
        raise SQLAlchemyError("Failed to establish database connection")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up database session"""
        if self.session:
            try:
                if exc_type is not None:
                    # Rollback on exception
                    self.session.rollback()
                    logger.error(f"Database session rolled back due to error: {exc_val}")
                else:
                    # Commit on success
                    self.session.commit()
                    logger.debug("Database session committed successfully")
            except SQLAlchemyError as e:
                logger.error(f"Error during session cleanup: {e}")
                self.session.rollback()
            finally:
                self.session.close()

def get_database_session():
    """Get database session as async context manager"""
    return DatabaseSession()

@contextmanager
def get_sync_session():
    """Synchronous context manager for database sessions"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database error in sync session: {e}")
        session.rollback()
        raise
    finally:
        session.close()

@handle_service_errors
@log_operation("init_db")
def init_db():
    """Initialize database tables with enhanced error handling"""
    try:
        # Import models to ensure they are registered with Base
        from .models import Controller, Flight, Transceiver, Airports
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Verify tables exist
        with get_sync_session() as session:
            result = session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('controllers', 'flights', 'transceivers', 'airports')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Verified tables: {tables}")
            
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

@handle_service_errors
@log_operation("close_db")
def close_db():
    """Close database connections gracefully"""
    try:
        # Close all sessions
        ScopedSessionLocal.remove()
        
        # Dispose engine
        engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

@handle_service_errors
@log_operation("get_database_info")
async def get_database_info():
    """Get comprehensive database information for monitoring"""
    try:
        pool = engine.pool
        
        # Test database connectivity
        with get_sync_session() as session:
            session.execute(text("SELECT 1"))
            connectivity = "connected"
    except SQLAlchemyError:
        connectivity = "disconnected"
    
    return {
        "database_type": "PostgreSQL",
        "connection_string": DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('://')[1], '***') if '@' in DATABASE_URL else DATABASE_URL,
        "connectivity": connectivity,
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "pool_status": {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid() if hasattr(pool, 'invalid') else 0
        }
    }

@handle_service_errors
@log_operation("health_check")
async def health_check():
    """Perform database health check"""
    try:
        with get_sync_session() as session:
            # Test basic connectivity
            session.execute(text("SELECT 1"))
            
            # Check table counts
            result = session.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM controllers) as controllers_count,
                    (SELECT COUNT(*) FROM flights) as flights_count,
                    (SELECT COUNT(*) FROM transceivers) as transceivers_count,
                    (SELECT COUNT(*) FROM airports) as airports_count
            """))
            counts = result.fetchone()
            
            return {
                "status": "healthy",
                "connectivity": "connected",
                "table_counts": {
                    "controllers": counts[0] or 0,
                    "flights": counts[1] or 0,
                    "transceivers": counts[2] or 0,
                    "airports": counts[3] or 0
                },
                "pool_status": {
                    "size": engine.pool.size(),
                    "checked_in": engine.pool.checkedin(),
                    "checked_out": engine.pool.checkedout(),
                    "overflow": engine.pool.overflow()
                }
            }
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connectivity": "disconnected",
            "error": str(e)
        } 
