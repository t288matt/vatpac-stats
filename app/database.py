from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import os
from typing import Generator

# Database configuration - use SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./atc_optimization.db")

# Create engine with optimization settings for long-running operation
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    pool_size=10,        # Maintain 10 connections
    max_overflow=20,     # Allow up to 20 additional connections
    connect_args={
        "check_same_thread": False,  # SQLite threading
        "timeout": 30,              # Connection timeout
        "isolation_level": None,    # Autocommit mode for better performance
        "pragma": {
            "journal_mode": "WAL",      # Write-Ahead Logging for better concurrency
            "cache_size": -64000,       # 64MB cache (negative = KB)
            "temp_store": "memory",     # Store temp tables in memory
            "mmap_size": 268435456,     # 256MB memory mapping
            "synchronous": "NORMAL",    # Balance between safety and speed
            "auto_vacuum": "INCREMENTAL",  # Automatic cleanup
            "incremental_vacuum": 1000,    # Vacuum every 1000 pages
            "page_size": 4096,         # 4KB pages for better compression
            "cache_spill": 0,          # Disable cache spilling
            "foreign_keys": "ON"       # Enable foreign key constraints
        }
    } if "sqlite" in DATABASE_URL else {
        "connect_timeout": 30,      # PostgreSQL connection timeout
        "application_name": "vatpac_stats"  # Application identifier
    },
    echo=False,  # Disable SQL logging for production
    echo_pool=False  # Disable pool logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    # Import models to ensure they are registered with Base
    from .models import Controller, Sector, Flight, SystemConfig, Event
    Base.metadata.create_all(bind=engine)

def close_db():
    """Close database connections"""
    engine.dispose() 