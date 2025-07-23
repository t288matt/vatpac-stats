from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import os
from typing import Generator

# Database configuration - use SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./atc_optimization.db")

# Create engine with SSD-optimized settings for long-running operation
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
            "journal_mode": "WAL",      # Write-Ahead Logging for better concurrency and SSD wear reduction
            "synchronous": "NORMAL",    # Reduced sync for better performance (FULL is safer but slower)
            "cache_size": -64000,       # 64MB cache to reduce disk I/O
            "temp_store": "MEMORY",     # Store temp tables in memory
            "mmap_size": 268435456,     # 256MB memory mapping
            "page_size": 65536,         # 64KB page size for better SSD performance
            "auto_vacuum": "INCREMENTAL", # Incremental vacuum to reduce fragmentation
            "incremental_vacuum": 1000,  # Vacuum 1000 pages at a time
            "wal_autocheckpoint": 1000,  # Checkpoint every 1000 pages
            "busy_timeout": 30000,       # 30 second busy timeout
            "foreign_keys": "ON",        # Enable foreign key constraints
            "recursive_triggers": "ON"   # Enable recursive triggers
        } if "sqlite" in DATABASE_URL else {
            "connect_timeout": 30,      # PostgreSQL connection timeout
            "application_name": "vatpac_stats"  # Application name for monitoring
        }
    }
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