#!/usr/bin/env python3
"""
SQLAlchemy Data Models for VATSIM Data Collection System

This module defines all database models and relationships for the VATSIM data
collection system. It provides optimized data structures for real-time flight
data, ATC positions, and analytics.

INPUTS:
- VATSIM API data (controllers, flights)
- Real-time flight tracking data
- Airport information
- System configuration settings

OUTPUTS:
- SQLAlchemy model classes for database tables
- Database schema definitions
- Model relationships and constraints
- Data validation and type conversion

MODELS INCLUDED:
- Controller: ATC controller positions and status
- Flight: Real-time flight data with position tracking
- Airports: Global airport database
- Transceiver: Radio frequency and position data

OPTIMIZATIONS:
- Storage-efficient data types (SMALLINT for durations)
- Optimized indexes for query performance
- JSON fields for flexible metadata storage
- Relationship mappings for efficient joins
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, SmallInteger, Index, DECIMAL, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import json

class Controller(Base):
    """Controller model representing ATC positions that can be controlled or uncontrolled"""
    __tablename__ = "controllers"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), unique=True, index=True, nullable=False)
    facility = Column(String(50), nullable=False)
    position = Column(String(50), nullable=True)
    status = Column(String(20), default="offline", index=True)  # online, offline, busy
    frequency = Column(String(20), nullable=True)
    last_seen = Column(TIMESTAMP, default=datetime.utcnow)
    workload_score = Column(DECIMAL(10,2), default=0.0)
    preferences = Column(Text, nullable=True)  # JSON object for position preferences
    # VATSIM API fields
    controller_id = Column(Integer, nullable=True, index=True)  # From API "cid"
    controller_name = Column(String(100), nullable=True)  # From API "name"
    controller_rating = Column(Integer, nullable=True)  # From API "rating"
    # Missing VATSIM API fields
    visual_range = Column(Integer, nullable=True)  # From API "visual_range"
    text_atis = Column(Text, nullable=True)  # From API "text_atis"
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class Flight(Base):
    """Flight model representing active flights - OPTIMIZED FOR STORAGE"""
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), nullable=False, index=True)
    aircraft_type = Column(String(20), nullable=True)
    
    # Flight tracking fields - using VATSIM API field names directly
    latitude = Column(Float, nullable=True, index=True)  # Position latitude
    longitude = Column(Float, nullable=True, index=True)  # Position longitude
    altitude = Column(Integer, nullable=True)
    heading = Column(Integer, nullable=True)
    groundspeed = Column(Integer, nullable=True)
    cruise_tas = Column(Integer, nullable=True)
    
    # Flight plan fields
    departure = Column(String(10), nullable=True, index=True)
    arrival = Column(String(10), nullable=True, index=True)
    route = Column(Text, nullable=True)
    
    # Timestamps
    last_updated = Column(TIMESTAMP, default=datetime.utcnow, index=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # VATSIM API fields - 1:1 mapping with API field names
    cid = Column(Integer, nullable=True, index=True)  # VATSIM user ID
    name = Column(String(100), nullable=True)  # Pilot name
    server = Column(String(50), nullable=True)  # Network server
    pilot_rating = Column(Integer, nullable=True)  # Pilot rating
    military_rating = Column(Integer, nullable=True)  # Military rating
    transponder = Column(String(10), nullable=True)  # Transponder code
    qnh_i_hg = Column(DECIMAL(4,2), nullable=True)  # QNH in inches Hg
    qnh_mb = Column(Integer, nullable=True)  # QNH in millibars
    logon_time = Column(TIMESTAMP, nullable=True)  # When pilot connected
    last_updated_api = Column(TIMESTAMP, nullable=True)  # API last_updated timestamp
    
    # Flight plan fields (nested object)
    flight_rules = Column(String(10), nullable=True)  # IFR/VFR
    aircraft_faa = Column(String(20), nullable=True)  # FAA aircraft code
    aircraft_short = Column(String(10), nullable=True)  # Short aircraft code
    alternate = Column(String(10), nullable=True)  # Alternate airport
    planned_altitude = Column(Integer, nullable=True)  # Planned cruise altitude
    deptime = Column(String(10), nullable=True)  # Departure time
    enroute_time = Column(String(10), nullable=True)  # Enroute time
    fuel_time = Column(String(10), nullable=True)  # Fuel time
    remarks = Column(Text, nullable=True)  # Flight plan remarks
    revision_id = Column(Integer, nullable=True)  # Flight plan revision
    assigned_transponder = Column(String(10), nullable=True)  # Assigned transponder
    
    # Optimized indexes for common queries
    __table_args__ = (
        Index('idx_flights_callsign_status', 'callsign', 'last_updated'),
        Index('idx_flights_departure_arrival', 'departure', 'arrival'),
        Index('idx_flights_position', 'latitude', 'longitude'),
        Index('idx_flights_altitude', 'altitude'),
        Index('idx_flights_heading', 'heading'),
        Index('idx_flights_groundspeed', 'groundspeed'),
    )

class Airports(Base):
    """Global airports table - single source of truth for all airport data"""
    __tablename__ = "airports"
    
    id = Column(Integer, primary_key=True, index=True)
    icao_code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Integer, nullable=True)  # Feet above sea level
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)  # State/province

    # Optimized indexes for common queries
    __table_args__ = (
        Index('idx_airports_country', 'country'),
        Index('idx_airports_region', 'region'),
        Index('idx_airports_lat_lon', 'latitude', 'longitude'),  # Geographic queries
        Index('idx_airports_elevation', 'elevation'),  # Elevation-based queries
        Index('idx_airports_country_region', 'country', 'region'),  # Geographic filtering
    )

class Transceiver(Base):
    """Transceiver model for storing radio frequency and position data from VATSIM transceivers API"""
    __tablename__ = "transceivers"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), nullable=False, index=True)
    transceiver_id = Column(Integer, nullable=False)  # ID from VATSIM API
    frequency = Column(Integer, nullable=False, index=True)  # Frequency in Hz
    position_lat = Column(Float, nullable=True)
    position_lon = Column(Float, nullable=True)
    height_msl = Column(Float, nullable=True)  # Height above mean sea level in meters
    height_agl = Column(Float, nullable=True)  # Height above ground level in meters
    entity_type = Column(String(20), nullable=False, index=True)  # 'flight' or 'atc'
    entity_id = Column(Integer, nullable=True, index=True)  # Foreign key to flights.id or controllers.id
    timestamp = Column(TIMESTAMP, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optimized indexes for common queries
    __table_args__ = (
        Index('idx_transceivers_callsign_timestamp', 'callsign', 'timestamp'),
        Index('idx_transceivers_entity_type_id', 'entity_type', 'entity_id'),  # Composite for entity lookups
        Index('idx_transceivers_position', 'position_lat', 'position_lon'),  # Geographic queries
        Index('idx_transceivers_frequency', 'frequency'),
    ) 
