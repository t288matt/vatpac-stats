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
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

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

# Initialize engines lazily - only when needed
# _create_engines()  # REMOVED: Don't create engines on import

# Lazy getter functions
def _get_engine():
    """Get or create the synchronous database engine."""
    global engine
    if engine is None:
        _create_engines()
    return engine

def _get_async_engine():
    """Get or create the asynchronous database engine."""
    global async_engine
    if async_engine is None:
        _create_engines()
    return async_engine

def _get_session_local():
    """Get or create the synchronous session factory."""
    global SessionLocal
    if SessionLocal is None:
        _create_engines()
    return SessionLocal

def _get_async_session_local():
    """Get or create the asynchronous session factory."""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        _create_engines()
    return AsyncSessionLocal

# Database session functions - following standard SQLAlchemy patterns
def get_database_session():
    """Get an async database session context manager."""
    class AsyncSessionContextManager:
        def __init__(self):
            self.session = None
        
        async def __aenter__(self):
            self.session = _get_async_session_local()()
            return self.session
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.session:
                await self.session.close()
    
    return AsyncSessionContextManager()

def get_sync_session():
    """Get a synchronous database session object."""
    return _get_session_local()()

# Database initialization
async def init_db():
    """Initialize database connection and test connectivity."""
    try:
        # Test synchronous connection
        session = get_sync_session()
        try:
            result = session.execute(text("SELECT 1"))
            logger.info("Synchronous database connection successful")
        finally:
            session.close()
        
        # Test asynchronous connection
        async_session_factory = get_database_session()
        async with async_session_factory() as session:
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
