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
        logger.info("🔍 Creating database engines...")
        logger.info(f"🔍 Database URL: {DATABASE_URL.replace('vatsim_password', '***')}")
        
        # Create synchronous engine
        engine = create_engine(
            DATABASE_URL,
            **ENGINE_CONFIG,
            poolclass=QueuePool
        )
        logger.info("✅ Synchronous database engine created successfully")
        
        # Create synchronous session factory
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        logger.info("✅ Synchronous session factory created successfully")
        
        # Create asynchronous engine
        async_engine = create_async_engine(
            ASYNC_DATABASE_URL,
            **ENGINE_CONFIG,
            poolclass=QueuePool
        )
        logger.info("✅ Asynchronous database engine created successfully")
        
        # Create asynchronous session factory
        AsyncSessionLocal = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("✅ Asynchronous session factory created successfully")
        
        logger.info("✅ All database engines created successfully")
        
    except Exception as e:
        error_msg = f"🚨 CRITICAL: Failed to create database engines: {e}"
        logger.critical(error_msg)
        
        # Provide specific error guidance
        if "connection" in str(e).lower() or "connect" in str(e).lower():
            logger.critical("🚨 CRITICAL: Database connection failed - check:")
            logger.critical("   - Database service is running (docker-compose ps)")
            logger.critical("   - Database credentials are correct")
            logger.critical("   - Network connectivity between app and database")
            logger.critical("   - Database port is accessible")
        elif "authentication" in str(e).lower() or "password" in str(e).lower():
            logger.critical("🚨 CRITICAL: Database authentication failed - check:")
            logger.critical("   - Database username and password")
            logger.critical("   - Database user permissions")
        elif "database" in str(e).lower() and "does not exist" in str(e).lower():
            logger.critical("🚨 CRITICAL: Database does not exist - check:")
            logger.critical("   - Database name in connection string")
            logger.critical("   - Database initialization script ran successfully")
        
        raise RuntimeError(f"Database engine creation failed: {e}")

# Initialize engines lazily - only when needed
# _create_engines()  # REMOVED: Don't create engines on import

# Lazy getter functions
def _get_engine():
    """Get or create the synchronous database engine."""
    global engine
    try:
        if engine is None:
            _create_engines()
        return engine
    except Exception as e:
        error_msg = f"🚨 CRITICAL: Failed to get synchronous database engine: {e}"
        logger.critical(error_msg)
        raise RuntimeError(f"Database engine unavailable: {e}")

def _get_async_engine():
    """Get or create the asynchronous database engine."""
    global async_engine
    try:
        if async_engine is None:
            _create_engines()
        return async_engine
    except Exception as e:
        error_msg = f"🚨 CRITICAL: Failed to get asynchronous database engine: {e}"
        logger.critical(error_msg)
        raise RuntimeError(f"Database engine unavailable: {e}")

def _get_session_local():
    """Get or create the synchronous session factory."""
    global SessionLocal
    try:
        if SessionLocal is None:
            _create_engines()
        return SessionLocal
    except Exception as e:
        error_msg = f"🚨 CRITICAL: Failed to get synchronous session factory: {e}"
        logger.critical(error_msg)
        raise RuntimeError(f"Database session factory unavailable: {e}")

def _get_async_session_local():
    """Get or create the asynchronous session factory."""
    global AsyncSessionLocal
    try:
        if AsyncSessionLocal is None:
            _create_engines()
        return AsyncSessionLocal
    except Exception as e:
        error_msg = f"🚨 CRITICAL: Failed to get asynchronous session factory: {e}"
        logger.critical(error_msg)
        raise RuntimeError(f"Database session factory unavailable: {e}")

# Database session functions - following standard SQLAlchemy patterns
def get_database_session():
    """Get an async database session context manager."""
    class AsyncSessionContextManager:
        def __init__(self):
            self.session = None
        
        async def __aenter__(self):
            try:
                self.session = _get_async_session_local()()
                logger.debug("Database session created successfully")
                return self.session
            except Exception as e:
                error_msg = f"🚨 CRITICAL: Failed to create database session: {e}"
                logger.critical(error_msg)
                logger.critical("🚨 CRITICAL: This indicates a database connection failure")
                raise RuntimeError(f"Database session creation failed: {e}")
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.session:
                try:
                    if exc_type is None:  # No exception occurred
                        await self.session.commit()  # COMMIT THE TRANSACTION
                        logger.debug("Database session committed successfully")
                    else:
                        await self.session.rollback()  # Rollback on exception
                        logger.warning(f"Database session rolled back due to exception: {exc_val}")
                except Exception as e:
                    logger.error(f"Error during database session cleanup: {e}")
                finally:
                    await self.session.close()
                    logger.debug("Database session closed")
    
    return AsyncSessionContextManager()

def get_sync_session():
    """Get a synchronous database session object."""
    return _get_session_local()()

# Database initialization
async def init_db():
    """Initialize database connection and test connectivity."""
    try:
        logger.info("🔍 Initializing database connections...")
        
        # Test synchronous connection
        try:
            session = get_sync_session()
            try:
                result = session.execute(text("SELECT 1"))
                logger.info("✅ Synchronous database connection successful")
            finally:
                session.close()
        except Exception as e:
            error_msg = f"🚨 CRITICAL: Synchronous database connection failed: {e}"
            logger.critical(error_msg)
            raise RuntimeError(f"Synchronous database connection failed: {e}")
        
        # Test asynchronous connection
        try:
            async_session_factory = get_database_session()
            async with async_session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                logger.info("✅ Asynchronous database connection successful")
        except Exception as e:
            error_msg = f"🚨 CRITICAL: Asynchronous database connection failed: {e}"
            logger.critical(error_msg)
            raise RuntimeError(f"Asynchronous database connection failed: {e}")
        
        # Test basic table access
        try:
            async_session_factory = get_database_session()
            async with async_session_factory() as session:
                # Check if we can access the information_schema
                result = await session.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                table_count = result.scalar()
                logger.info(f"✅ Database schema accessible - {table_count} tables found")
                
                # Check for critical tables
                critical_tables = ['flights', 'controllers', 'flight_summaries']
                for table in critical_tables:
                    try:
                        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        logger.info(f"✅ Table {table} accessible - {count} records")
                    except Exception as table_error:
                        error_msg = f"🚨 CRITICAL: Critical table {table} is not accessible: {table_error}"
                        logger.critical(error_msg)
                        logger.critical("🚨 CRITICAL: This indicates a database schema issue")
                        logger.critical("🚨 CRITICAL: Check if database initialization script ran successfully")
                        raise RuntimeError(f"Critical table {table} not accessible: {table_error}")
        
        except Exception as e:
            if "relation" in str(e).lower() or "table" in str(e).lower():
                error_msg = f"🚨 CRITICAL: Database schema issue detected: {e}"
                logger.critical(error_msg)
                logger.critical("🚨 CRITICAL: This usually means:")
                logger.critical("   - Database initialization script didn't run")
                logger.critical("   - Database schema is incomplete")
                logger.critical("   - Tables are missing or corrupted")
                logger.critical("🚨 CRITICAL: Please check:")
                logger.critical("   - Run 'docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c \"\\dt\"'")
                logger.critical("   - Check database logs for initialization errors")
                logger.critical("   - Verify init.sql script is correct")
                raise RuntimeError(f"Database schema issue: {e}")
            else:
                raise
        
        logger.info("✅ Database initialization completed successfully")
        return True
        
    except SQLAlchemyError as e:
        error_msg = f"🚨 CRITICAL: Database initialization failed - SQLAlchemy error: {e}"
        logger.critical(error_msg)
        logger.critical("🚨 CRITICAL: This indicates a database-level issue")
        return False
    except Exception as e:
        error_msg = f"🚨 CRITICAL: Unexpected error during database initialization: {e}"
        logger.critical(error_msg)
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
