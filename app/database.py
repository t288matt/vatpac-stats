#!/usr/bin/env python3
"""
Database configuration and connection management for VATSIM Data Collection System.

This module provides database connection management, configuration, and utility functions
for the VATSIM data collection system.
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
import asyncio

from app.config import get_config
from app.utils.logging import get_logger_for_module
from app.utils.error_handling import handle_service_errors, log_operation

logger = get_logger_for_module(__name__)

# Database configuration
config = get_config()

# Database URLs
DATABASE_URL = config.database.url
# Convert to async URL format for async operations
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

# Engine configuration - simplified
ENGINE_CONFIG = {
    "pool_size": config.database.pool_size,
    "max_overflow": config.database.max_overflow,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
    "echo": False,
    "echo_pool": False,
}

# Create database engines
engine = None
async_engine = None
SessionLocal = None
AsyncSessionLocal = None

def _create_engines():
    """Create database engines with configuration."""
    global engine, async_engine, SessionLocal, AsyncSessionLocal
    
    try:
        # Create synchronous engine
        engine = create_engine(
            DATABASE_URL,
            **ENGINE_CONFIG,
            poolclass=QueuePool
        )
        
        # Create synchronous session factory
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        
        # Create asynchronous engine
        async_engine = create_async_engine(
            ASYNC_DATABASE_URL,
            **ENGINE_CONFIG,
            poolclass=QueuePool
        )
        
        # Create asynchronous session factory
        AsyncSessionLocal = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("Database engines created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create database engines: {e}")
        raise

# Initialize engines
_create_engines()

# Database event handlers
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance."""
    if "sqlite" in DATABASE_URL.lower():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

@event.listens_for(engine, "connect")
def set_postgresql_settings(dbapi_connection, connection_record):
    """Set PostgreSQL settings for better performance."""
    if "postgresql" in DATABASE_URL.lower():
        cursor = dbapi_connection.cursor()
        cursor.execute("SET statement_timeout = 30000")  # 30 seconds
        cursor.execute("SET idle_in_transaction_session_timeout = 30000")  # 30 seconds
        cursor.close()

# Connection pool event handlers
@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Handle connection checkout."""
    logger.debug("Database connection checked out")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Handle connection checkin."""
    logger.debug("Database connection checked in")

# Database connection context manager
class DatabaseConnection:
    """Database connection context manager."""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = AsyncSessionLocal()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def __enter__(self):
        """Sync context manager entry."""
        self.session = SessionLocal()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        if self.session:
            self.session.close()
    
    def execute(self, query, params=None):
        """Execute a query."""
        if not self.session:
            raise RuntimeError("No active database session")
        return self.session.execute(text(query), params or {})
    
    def commit(self):
        """Commit the current transaction."""
        if not self.session:
            raise RuntimeError("No active database session")
        self.session.commit()
    
    def rollback(self):
        """Rollback the current transaction."""
        if not self.session:
            raise RuntimeError("No active database session")
        self.session.rollback()

# Database session functions
def get_database_session():
    """Get an async database session context manager."""
    return AsyncSessionLocal()

def get_sync_session() -> Session:
    """Get a synchronous database session."""
    return SessionLocal()

# Database initialization
async def init_db():
    """Initialize database connection and test connectivity."""
    try:
        # Test synchronous connection
        with get_sync_session() as session:
            result = session.execute(text("SELECT 1"))
            logger.info("Synchronous database connection successful")
        
        # Test asynchronous connection
        async with get_database_session() as session:
            result = await session.execute(text("SELECT 1"))
            logger.info("Asynchronous database connection successful")
        
        logger.info("Database initialization completed successfully")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        return False

# Database cleanup
async def close_db():
    """Close database connections and cleanup resources."""
    global engine, async_engine
    
    try:
        if engine:
            engine.dispose()
            logger.info("Synchronous database engine disposed")
        
        if async_engine:
            await async_engine.dispose()
            logger.info("Asynchronous database engine disposed")
        
        logger.info("Database cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")
        raise 
