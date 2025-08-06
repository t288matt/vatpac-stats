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
- Sector: Airspace sector definitions and traffic density
- TrafficMovement: Airport arrival/departure tracking
- FlightSummary: Compressed historical flight data
- MovementSummary: Hourly movement statistics
- Airports: Global airport database
- AirportConfig: Movement detection settings
- SystemConfig: Application configuration storage
- Event: Special events and scheduling
- Transceiver: Radio frequency and position data

OPTIMIZATIONS:
- Storage-efficient data types (SMALLINT for durations)
- Optimized indexes for query performance
- JSON fields for flexible metadata storage
- Relationship mappings for efficient joins
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, SmallInteger, Index, DECIMAL, JSON
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
    status = Column(String(20), default="offline")  # online, offline, busy
    frequency = Column(String(20), nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    workload_score = Column(Float, default=0.0)
    preferences = Column(JSON, nullable=True)  # JSON object for position preferences
    # VATSIM API fields
    controller_id = Column(Integer, nullable=True, index=True)  # From API "cid"
    controller_name = Column(String(100), nullable=True)  # From API "name"
    controller_rating = Column(Integer, nullable=True)  # From API "rating"
    # Missing VATSIM API fields
    visual_range = Column(Integer, nullable=True)  # From API "visual_range"
    text_atis = Column(Text, nullable=True)  # From API "text_atis"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sectors = relationship("Sector", back_populates="controller")
    flights = relationship("Flight", back_populates="controller")

class Sector(Base):
    """Airspace sector model"""
    __tablename__ = "sectors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    facility = Column(String(50), nullable=False)
    controller_id = Column(Integer, ForeignKey("controllers.id"), nullable=True)
    traffic_density = Column(Integer, default=0)
    status = Column(String(20), default="unmanned")  # manned, unmanned, busy
    priority_level = Column(Integer, default=1)  # 1-5 priority scale
    boundaries = Column(Text, nullable=True)  # JSON string for sector boundaries
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    controller = relationship("Controller", back_populates="sectors")

class Flight(Base):
    """Flight model representing active flights - OPTIMIZED FOR STORAGE"""
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), nullable=False, index=True)
    aircraft_type = Column(String(20), nullable=True)
    position_lat = Column(Float, nullable=True)
    position_lng = Column(Float, nullable=True)
    altitude = Column(Integer, nullable=True)
    speed = Column(Integer, nullable=True)
    heading = Column(Integer, nullable=True)
    ground_speed = Column(Integer, nullable=True)
    vertical_speed = Column(Integer, nullable=True)
    squawk = Column(String(10), nullable=True)
    flight_plan = Column(JSON, nullable=True)  # JSON object
    controller_id = Column(Integer, ForeignKey("controllers.id"), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    departure = Column(String(10), nullable=True)
    arrival = Column(String(10), nullable=True)
    route = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active, completed, cancelled
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Missing VATSIM API fields - 1:1 mapping with API field names
    cid = Column(Integer, nullable=True, index=True)  # VATSIM user ID
    name = Column(String(100), nullable=True)  # Pilot name
    server = Column(String(50), nullable=True)  # Network server
    pilot_rating = Column(Integer, nullable=True)  # Pilot rating
    military_rating = Column(Integer, nullable=True)  # Military rating
    latitude = Column(Float, nullable=True)  # Position latitude
    longitude = Column(Float, nullable=True)  # Position longitude
    groundspeed = Column(Integer, nullable=True)  # Ground speed
    transponder = Column(String(10), nullable=True)  # Transponder code
    qnh_i_hg = Column(DECIMAL(4,2), nullable=True)  # QNH in inches Hg
    qnh_mb = Column(Integer, nullable=True)  # QNH in millibars
    logon_time = Column(DateTime, nullable=True)  # When pilot connected
    last_updated_api = Column(DateTime, nullable=True)  # API last_updated timestamp
    
    # Flight plan fields (nested object)
    flight_rules = Column(String(10), nullable=True)  # IFR/VFR
    aircraft_faa = Column(String(20), nullable=True)  # FAA aircraft code
    aircraft_short = Column(String(10), nullable=True)  # Short aircraft code
    alternate = Column(String(10), nullable=True)  # Alternate airport
    cruise_tas = Column(Integer, nullable=True)  # True airspeed
    planned_altitude = Column(Integer, nullable=True)  # Planned cruise altitude
    deptime = Column(String(10), nullable=True)  # Departure time
    enroute_time = Column(String(10), nullable=True)  # Enroute time
    fuel_time = Column(String(10), nullable=True)  # Fuel time
    remarks = Column(Text, nullable=True)  # Flight plan remarks
    revision_id = Column(Integer, nullable=True)  # Flight plan revision
    assigned_transponder = Column(String(10), nullable=True)  # Assigned transponder
    
    # Relationships
    controller = relationship("Controller", back_populates="flights")
    
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

class TrafficMovement(Base):
    """Traffic movement model for tracking arrivals/departures"""
    __tablename__ = "traffic_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    airport_code = Column(String(10), nullable=False, index=True)
    movement_type = Column(String(20), nullable=False)  # 'arrival' or 'departure'
    aircraft_callsign = Column(String(50), nullable=True)
    aircraft_type = Column(String(20), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    runway = Column(String(10), nullable=True)
    altitude = Column(Integer, nullable=True)
    speed = Column(Integer, nullable=True)
    heading = Column(Integer, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # No relationships for now

class FlightSummary(Base):
    """Flight summary for analytics - COMPRESSED HISTORICAL DATA"""
    __tablename__ = "flight_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(20), nullable=False, index=True)
    aircraft_type = Column(String(10), nullable=True)
    departure = Column(String(10), nullable=True)
    arrival = Column(String(10), nullable=True)
    route = Column(Text, nullable=True)
    max_altitude = Column(SmallInteger, nullable=True)  # SMALLINT for storage efficiency
    duration_minutes = Column(SmallInteger, nullable=True)  # SMALLINT: max 65,535 minutes
    controller_id = Column(Integer, ForeignKey("controllers.id"), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    completed_at = Column(DateTime, nullable=False)
    
    # Relationships
    controller = relationship("Controller")
    sector = relationship("Sector")

class MovementSummary(Base):
    """Movement summary for analytics - COMPRESSED HISTORICAL DATA"""
    __tablename__ = "movement_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    airport_icao = Column(String(10), nullable=False, index=True)
    movement_type = Column(String(10), nullable=False)  # 'arrival' or 'departure'
    aircraft_type = Column(String(10), nullable=True)
    date = Column(DateTime, nullable=False, index=True)  # Date only
    hour = Column(SmallInteger, nullable=False)  # 0-23 hour
    count = Column(SmallInteger, default=1)  # Number of movements in this hour
    
    # Composite index for efficient queries
    __table_args__ = (
        {'sqlite_autoincrement': True}
    )

class AirportConfig(Base):
    """Airport configuration for movement detection"""
    __tablename__ = "airport_config"
    
    id = Column(Integer, primary_key=True, index=True)
    icao_code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    detection_radius_nm = Column(Float, default=10.0)  # Detection radius in nautical miles
    departure_altitude_threshold = Column(Integer, default=1000)  # Feet
    arrival_altitude_threshold = Column(Integer, default=3000)  # Feet
    departure_speed_threshold = Column(Integer, default=50)  # Knots
    arrival_speed_threshold = Column(Integer, default=150)  # Knots
    is_active = Column(Boolean, default=True)
    region = Column(String(50), nullable=True)  # 'Australia', 'Asia', etc.
    last_updated = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    )

class MovementDetectionConfig(Base):
    """Configuration for movement detection algorithms"""
    __tablename__ = "movement_detection_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SystemConfig(Base):
    """System configuration model"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    environment = Column(String(20), default="development")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Event(Base):
    """Event model for special events and scheduling"""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    expected_traffic = Column(Integer, default=0)
    required_controllers = Column(Integer, default=0)
    status = Column(String(20), default="scheduled")  # scheduled, active, completed
    notes = Column(Text, nullable=True)

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
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_transceivers_callsign_timestamp', 'callsign', 'timestamp'),
        Index('idx_transceivers_entity_type', 'entity_type'),
        Index('idx_transceivers_frequency', 'frequency'),
        Index('idx_transceivers_timestamp', 'timestamp'),
    )

class VatsimStatus(Base):
    """VATSIM network status and general information"""
    __tablename__ = "vatsim_status"
    
    id = Column(Integer, primary_key=True, index=True)
    api_version = Column(Integer, nullable=True)  # From API "version"
    reload = Column(Integer, nullable=True)  # From API "reload"
    update_timestamp = Column(DateTime, nullable=True)  # From API "update_timestamp"
    connected_clients = Column(Integer, nullable=True)  # From API "connected_clients"
    unique_users = Column(Integer, nullable=True)  # From API "unique_users"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
