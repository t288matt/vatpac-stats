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
- Proper constraints and validation
- Audit fields for data tracking
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, 
    SmallInteger, Index, DECIMAL, JSON, TIMESTAMP, CheckConstraint, UniqueConstraint,
    BigInteger, event, func
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime, timezone
from .database import Base
import json

class TimestampMixin:
    """Mixin to add timestamp fields to models"""
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

class Controller(Base, TimestampMixin):
    """Controller model representing ATC positions - EXACT API mapping"""
    __tablename__ = "controllers"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), unique=True, index=True, nullable=False)
    frequency = Column(String(20), nullable=True)
    cid = Column(Integer, nullable=True, index=True)  # From API "cid"
    name = Column(String(100), nullable=True)  # From API "name"
    rating = Column(Integer, nullable=True)  # From API "rating" - matches database schema
    facility = Column(Integer, nullable=True)  # From API "facility" - matches database schema
    visual_range = Column(Integer, nullable=True)  # From API "visual_range"
    text_atis = Column(Text, nullable=True)  # From API "text_atis"
    server = Column(String(50), nullable=True)  # From API "server"
    last_updated = Column(TIMESTAMP(timezone=True), nullable=True, index=True)  # From API "last_updated"
    logon_time = Column(TIMESTAMP(timezone=True), nullable=True)  # From API "logon_time"
    
    # Constraints
    __table_args__ = (
        CheckConstraint('rating >= -1 AND rating <= 12', name='valid_rating'),
        CheckConstraint('facility >= 0 AND facility <= 6', name='valid_facility'),
        CheckConstraint('visual_range >= 0', name='valid_visual_range'),
        Index('idx_controllers_cid_rating', 'cid', 'rating'),
        Index('idx_controllers_facility_server', 'facility', 'server'),
        Index('idx_controllers_last_updated', 'last_updated'),
    )
    
    @validates('rating')
    def validate_rating(self, key, value):
        """Validate controller rating"""
        if value is not None and (value < -1 or value > 12):
            raise ValueError("Rating must be between -1 and 12")
        return value
    
    @validates('facility')
    def validate_facility(self, key, value):
        """Validate facility type"""
        if value is not None and (value < 0 or value > 6):
            raise ValueError("Facility must be between 0 and 6")
        return value
    
    @validates('visual_range')
    def validate_visual_range(self, key, value):
        """Validate visual range"""
        if value is not None and value < 0:
            raise ValueError("Visual range must be non-negative")
        return value

class Flight(Base, TimestampMixin):
    """Flight model representing active flights - OPTIMIZED FOR STORAGE"""
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), nullable=False, index=True)
    aircraft_type = Column(String(20), nullable=True)
    
    # Flight tracking fields - using VATSIM API field names directly
    latitude = Column(Float, nullable=True, index=True)  # Position latitude
    longitude = Column(Float, nullable=True, index=True)  # Position longitude
    altitude = Column(Integer, nullable=True)
    heading = Column(Integer, nullable=True)  # Using Integer for consistency with database
    groundspeed = Column(Integer, nullable=True)  # Using Integer for consistency with database
    
    # Flight plan fields - simplified to essential only
    departure = Column(String(10), nullable=True, index=True)
    arrival = Column(String(10), nullable=True, index=True)
    route = Column(Text, nullable=True)
    
    # Additional flight plan fields from VATSIM API
    flight_rules = Column(String(10), nullable=True)  # IFR/VFR from flight_plan.flight_rules
    aircraft_faa = Column(String(20), nullable=True)  # FAA aircraft code from flight_plan.aircraft_faa
    alternate = Column(String(10), nullable=True)  # Alternate airport from flight_plan.alternate
    cruise_tas = Column(String(10), nullable=True)  # True airspeed from flight_plan.cruise_tas
    planned_altitude = Column(String(10), nullable=True)  # Planned cruise altitude from flight_plan.altitude
    deptime = Column(String(10), nullable=True)  # Departure time from flight_plan.deptime
    enroute_time = Column(String(10), nullable=True)  # Enroute time from flight_plan.enroute_time
    fuel_time = Column(String(10), nullable=True)  # Fuel time from flight_plan.fuel_time
    remarks = Column(Text, nullable=True)  # Flight plan remarks from flight_plan.remarks
    
    # Timestamps
    last_updated = Column(TIMESTAMP(timezone=True), default=func.now(), index=True)
    
    # VATSIM API fields - 1:1 mapping with API field names (simplified)
    cid = Column(Integer, nullable=True, index=True)  # VATSIM user ID
    name = Column(String(100), nullable=True)  # Pilot name
    server = Column(String(50), nullable=True)  # Network server
    pilot_rating = Column(Integer, nullable=True)  # Pilot rating - using Integer for consistency
    military_rating = Column(Integer, nullable=True)  # Military rating from VATSIM API
    transponder = Column(String(10), nullable=True)  # Transponder code
    logon_time = Column(TIMESTAMP(timezone=True), nullable=True)  # When pilot connected
    last_updated_api = Column(TIMESTAMP(timezone=True), nullable=True)  # API last_updated timestamp
    
    # Constraints
    __table_args__ = (
        CheckConstraint('latitude >= -90 AND latitude <= 90', name='valid_latitude'),
        CheckConstraint('longitude >= -180 AND longitude <= 180', name='valid_longitude'),
        CheckConstraint('altitude >= 0', name='valid_altitude'),
        CheckConstraint('heading >= 0 AND heading <= 360', name='valid_heading'),
        CheckConstraint('groundspeed >= 0', name='valid_groundspeed'),
        CheckConstraint('pilot_rating >= 0 AND pilot_rating <= 63', name='valid_pilot_rating'),
        Index('idx_flights_callsign_status', 'callsign', 'last_updated'),
        Index('idx_flights_position', 'latitude', 'longitude'),
        Index('idx_flights_departure_arrival', 'departure', 'arrival'),
        Index('idx_flights_cid_server', 'cid', 'server'),
        Index('idx_flights_altitude', 'altitude'),
        Index('idx_flights_flight_rules', 'flight_rules'),
        Index('idx_flights_planned_altitude', 'planned_altitude'),
    )
    
    @validates('latitude')
    def validate_latitude(self, key, value):
        """Validate latitude"""
        if value is not None and (value < -90 or value > 90):
            raise ValueError("Latitude must be between -90 and 90")
        return value
    
    @validates('longitude')
    def validate_longitude(self, key, value):
        """Validate longitude"""
        if value is not None and (value < -180 or value > 180):
            raise ValueError("Longitude must be between -180 and 180")
        return value
    
    @validates('altitude')
    def validate_altitude(self, key, value):
        """Validate altitude"""
        if value is not None and value < 0:
            raise ValueError("Altitude must be non-negative")
        return value
    
    @validates('heading')
    def validate_heading(self, key, value):
        """Validate heading"""
        if value is not None and (value < 0 or value > 360):
            raise ValueError("Heading must be between 0 and 360")
        return value

class Airports(Base, TimestampMixin):
    """Global airports table - single source of truth for all airport data"""
    __tablename__ = "airports"
    
    id = Column(Integer, primary_key=True)
    icao_code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Integer, nullable=True)  # Feet above sea level
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)  # State/province
    
    # Constraints
    __table_args__ = (
        CheckConstraint('latitude >= -90 AND latitude <= 90', name='valid_airport_latitude'),
        CheckConstraint('longitude >= -180 AND longitude <= 180', name='valid_airport_longitude'),
        CheckConstraint('elevation >= -1000', name='valid_elevation'),  # Allow negative for below sea level
        Index('idx_airports_region', 'region', 'country'),
        Index('idx_airports_coordinates', 'latitude', 'longitude'),
        Index('idx_airports_country', 'country'),
    )
    
    @validates('latitude')
    def validate_latitude(self, key, value):
        """Validate latitude"""
        if value < -90 or value > 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value
    
    @validates('longitude')
    def validate_longitude(self, key, value):
        """Validate longitude"""
        if value < -180 or value > 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value

class Transceiver(Base, TimestampMixin):
    """Transceiver model for storing radio frequency and position data from VATSIM transceivers API"""
    __tablename__ = "transceivers"
    
    id = Column(Integer, primary_key=True)
    callsign = Column(String(50), nullable=False, index=True)
    transceiver_id = Column(Integer, nullable=False)  # ID from VATSIM API
    frequency = Column(BigInteger, nullable=False, index=True)  # Frequency in Hz
    position_lat = Column(Float, nullable=True)
    position_lon = Column(Float, nullable=True)
    height_msl = Column(Float, nullable=True)  # Height above mean sea level in meters from VATSIM API
    height_agl = Column(Float, nullable=True)  # Height above ground level in meters from VATSIM API
    entity_type = Column(String(20), nullable=False, index=True)  # 'flight' or 'atc'
    entity_id = Column(Integer, nullable=True, index=True)  # Foreign key to flights.id or controllers.id
    timestamp = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False, index=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('frequency > 0', name='valid_frequency'),
        CheckConstraint('position_lat >= -90 AND position_lat <= 90', name='valid_transceiver_latitude'),
        CheckConstraint('position_lon >= -180 AND position_lon <= 180', name='valid_transceiver_longitude'),
        CheckConstraint("entity_type IN ('flight', 'atc')", name='valid_entity_type'),
        Index('idx_transceivers_callsign_timestamp', 'callsign', 'timestamp'),
        Index('idx_transceivers_frequency', 'frequency'),
        Index('idx_transceivers_entity', 'entity_type', 'entity_id'),
        Index('idx_transceivers_position', 'position_lat', 'position_lon'),
    )
    
    @validates('frequency')
    def validate_frequency(self, key, value):
        """Validate frequency"""
        if value <= 0:
            raise ValueError("Frequency must be positive")
        return value
    
    @validates('entity_type')
    def validate_entity_type(self, key, value):
        """Validate entity type"""
        if value not in ['flight', 'atc']:
            raise ValueError("Entity type must be 'flight' or 'atc'")
        return value

# Event listeners for automatic timestamp updates
@event.listens_for(Base, 'before_update', propagate=True)
def timestamp_before_update(mapper, connection, target):
    """Automatically update the updated_at timestamp"""
    target.updated_at = datetime.now(timezone.utc)

@event.listens_for(Base, 'before_insert', propagate=True)
def timestamp_before_insert(mapper, connection, target):
    """Automatically set created_at and updated_at timestamps"""
    now = datetime.now(timezone.utc)
    target.created_at = now
    target.updated_at = now 
