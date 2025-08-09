#!/usr/bin/env python3
"""
SQLAlchemy Data Models for VATSIM Data Collection System

This module defines all database models and relationships for the VATSIM data
collection system. It provides optimized data structures for real-time flight
data, ATC positions, traffic movements, and analytics.

INPUTS:
- VATSIM API data (controllers, flights, sectors)
- Real-time flight tracking data
- Airport and sector information
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
- FrequencyMatch: Frequency matching events between pilots and controllers
# REMOVED: TrafficMovement - Traffic Analysis Service removed in Phase 3

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
    
    # Relationships removed - sectors table no longer exists

# Sector model removed - VATSIM API v3 does not provide sectors data

class Flight(Base):
    """Flight model representing active flights - OPTIMIZED FOR STORAGE"""
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), nullable=False, index=True)
    aircraft_type = Column(String(20), nullable=True)
    position_lat = Column(DECIMAL(10,8), nullable=True)
    position_lng = Column(DECIMAL(11,8), nullable=True)
    
    # Flight tracking fields
    altitude = Column(Integer, nullable=True)
    heading = Column(Integer, nullable=True)
    groundspeed = Column(Integer, nullable=True)
    cruise_tas = Column(Integer, nullable=True)
    
    # Flight plan fields
    departure = Column(String(10), nullable=True)
    arrival = Column(String(10), nullable=True)
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
    latitude = Column(Float, nullable=True)  # Position latitude
    longitude = Column(Float, nullable=True)  # Position longitude
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
    
    @property
    def position(self):
        """Get position as JSON string (for compatibility)"""
        if self.position_lat and self.position_lng:
            return json.dumps({
                'lat': self.position_lat,
                'lng': self.position_lng
            })
        return None
    
    @position.setter
    def position(self, value):
        """Set position from JSON string (for compatibility)"""
        if isinstance(value, str):
            try:
                pos = json.loads(value)
                self.position_lat = float(pos.get('lat', 0))
                self.position_lng = float(pos.get('lng', 0))
            except:
                self.position_lat = None
                self.position_lng = None
        elif isinstance(value, dict):
            self.position_lat = float(value.get('lat', 0))
            self.position_lng = float(value.get('lng', 0))
        else:
            self.position_lat = None
            self.position_lng = None

# REMOVED: Traffic Analysis Service - Phase 3
# TrafficMovement model removed


# AirportConfig model removed - functionality merged with airports table

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

    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_airports_country', 'country'),
        Index('idx_airports_region', 'region'),
        Index('idx_airports_icao_prefix', 'icao_code'),
        Index('idx_airports_lat_lon', 'latitude', 'longitude'),  # Geographic queries
        Index('idx_airports_elevation', 'elevation'),  # Elevation-based queries
        Index('idx_airports_country_region', 'country', 'region'),  # Geographic filtering
        Index('idx_airports_name', 'name'),  # Name-based searches
        Index('idx_airports_icao_country', 'icao_code', 'country'),  # Country-specific ICAO lookups
    )

# MovementDetectionConfig model removed - configuration handled via environment variables





class Transceiver(Base):
    """Transceiver model for storing radio frequency and position data from VATSIM transceivers API"""
    __tablename__ = "transceivers"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), nullable=False, index=True)
    transceiver_id = Column(Integer, nullable=False)  # ID from VATSIM API
    frequency = Column(Integer, nullable=False)  # Frequency in Hz
    position_lat = Column(Float, nullable=True)
    position_lon = Column(Float, nullable=True)
    height_msl = Column(Float, nullable=True)  # Height above mean sea level in meters
    height_agl = Column(Float, nullable=True)  # Height above ground level in meters
    entity_type = Column(String(20), nullable=False)  # 'flight' or 'atc'
    entity_id = Column(Integer, nullable=True)  # Foreign key to flights.id or controllers.id
    timestamp = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_transceivers_callsign_timestamp', 'callsign', 'timestamp'),
        Index('idx_transceivers_entity_type', 'entity_type'),
        Index('idx_transceivers_frequency', 'frequency'),
        Index('idx_transceivers_timestamp', 'timestamp'),
        Index('idx_transceivers_entity_id', 'entity_id'),  # Foreign key to flights/controllers
        Index('idx_transceivers_entity_type_id', 'entity_type', 'entity_id'),  # Composite for entity lookups
        Index('idx_transceivers_callsign_entity', 'callsign', 'entity_type'),  # Callsign + entity type
        Index('idx_transceivers_position', 'position_lat', 'position_lon'),  # Geographic queries
        Index('idx_transceivers_height', 'height_msl', 'height_agl'),  # Height-based queries
    )




class FrequencyMatch(Base):
    """Frequency matching events between pilots and ATC controllers"""
    __tablename__ = "frequency_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    pilot_callsign = Column(String(50), nullable=False, index=True)
    controller_callsign = Column(String(50), nullable=False, index=True)
    frequency = Column(Integer, nullable=False, index=True)  # Frequency in Hz
    pilot_lat = Column(Float, nullable=True)
    pilot_lon = Column(Float, nullable=True)
    controller_lat = Column(Float, nullable=True)
    controller_lon = Column(Float, nullable=True)
    distance_nm = Column(Float, nullable=True)  # Distance between pilot and controller
    match_timestamp = Column(DateTime, nullable=False, index=True)
    duration_seconds = Column(Integer, nullable=True)  # Duration of the match
    match_confidence = Column(Float, default=1.0)  # Confidence score (0.0 to 1.0)
    communication_type = Column(String(20), nullable=False, index=True)  # 'approach', 'departure', 'enroute', 'ground', 'tower', 'hf_enroute', 'unknown'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_frequency_matches_pilot_controller', 'pilot_callsign', 'controller_callsign'),
        Index('idx_frequency_matches_frequency_timestamp', 'frequency', 'match_timestamp'),
        Index('idx_frequency_matches_communication_type', 'communication_type'),
        Index('idx_frequency_matches_distance', 'distance_nm'),
    ) 
