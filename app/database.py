from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import os
from typing import Generator

# Database configuration - PostgreSQL only
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data")

# PostgreSQL configuration for SSD preservation and memory caching
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Verify connections before use
    pool_recycle=300,        # Recycle connections every 5 minutes
    pool_size=20,            # Maintain 20 connections for concurrent access
    max_overflow=30,         # Allow up to 30 additional connections
    pool_timeout=30,         # Connection timeout
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
    from .models import ATCPosition, Sector, Flight, SystemConfig, Event, TrafficMovement, FlightSummary, MovementSummary, AirportConfig, MovementDetectionConfig
    Base.metadata.create_all(bind=engine)

def close_db():
    """Close database connections"""
    engine.dispose()

def get_database_info():
    """Get database information for monitoring"""
    return {
        "database_type": "PostgreSQL",
        "connection_string": DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('://')[1], '***') if '@' in DATABASE_URL else DATABASE_URL,
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow()
    } 