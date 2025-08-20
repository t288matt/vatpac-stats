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

from sqlalchemy import Column, Integer, String, Float, Text, TIMESTAMP, BigInteger, CheckConstraint, Index, event
from sqlalchemy.sql import func
from sqlalchemy.orm import validates, declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class TimestampMixin:
    """Mixin to add timestamp fields to models"""
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

class Controller(Base, TimestampMixin):
    """Controller model representing ATC positions - EXACT API mapping"""
    __tablename__ = "controllers"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), index=True, nullable=False)
    frequency = Column(String(20), nullable=True)
    cid = Column(Integer, nullable=True, index=True)  # From API "cid"
    name = Column(String(100), nullable=True)  # From API "name"
    rating = Column(Integer, nullable=True, index=True)  # From API "rating" - matches database schema
    facility = Column(Integer, nullable=True, index=True)  # From API "facility" - matches database schema
    visual_range = Column(Integer, nullable=True, index=True)  # From API "visual_range"
    text_atis = Column(Text, nullable=True)  # From API "text_atis"
    server = Column(String(50), nullable=True, index=True)  # From API "server"
    last_updated = Column(TIMESTAMP(timezone=True), nullable=True, index=True)  # From API "last_updated"
    logon_time = Column(TIMESTAMP(timezone=True), nullable=True)  # From API "logon_time"
    
    # Constraints
    __table_args__ = (
        CheckConstraint('rating >= -1 AND rating <= 12', name='valid_rating'),
        CheckConstraint('facility >= 0 AND facility <= 6', name='valid_facility'),
        CheckConstraint('visual_range >= 0', name='valid_visual_range'),
        Index('idx_controllers_callsign', 'callsign'),
        Index('idx_controllers_cid', 'cid'),
        Index('idx_controllers_cid_rating', 'cid', 'rating'),
        Index('idx_controllers_facility_server', 'facility', 'server'),
        Index('idx_controllers_last_updated', 'last_updated'),
        Index('idx_controllers_rating_last_updated', 'rating', 'last_updated'),
        
        # ATC Detection Performance Indexes
        Index('idx_controllers_callsign_facility', 'callsign', 'facility'),
    )
    
    # Validation handled by database constraints - no Python validators needed

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
    aircraft_short = Column(String(20), nullable=True)  # Short aircraft code from flight_plan.aircraft_short
    alternate = Column(String(10), nullable=True)  # Alternate airport from flight_plan.alternate
    cruise_tas = Column(String(10), nullable=True)  # True airspeed from flight_plan.cruise_tas
    planned_altitude = Column(String(10), nullable=True)  # Planned cruise altitude from flight_plan.altitude
    deptime = Column(String(10), nullable=True)  # Departure time from flight_plan.deptime
    enroute_time = Column(String(10), nullable=True)  # Enroute time from flight_plan.enroute_time
    fuel_time = Column(String(10), nullable=True)  # Fuel time from flight_plan.fuel_time
    remarks = Column(Text, nullable=True)  # Flight plan remarks from flight_plan.remarks
    
    # Additional VATSIM API fields
    revision_id = Column(Integer, nullable=True)  # Flight plan revision from flight_plan.revision_id
    assigned_transponder = Column(String(10), nullable=True)  # Assigned transponder from flight_plan.assigned_transponder
    
    # Timestamps
    last_updated = Column(TIMESTAMP(timezone=True), default=func.now(), index=True)
    
    # VATSIM API fields - 1:1 mapping with API field names (simplified)
    cid = Column(Integer, nullable=True, index=True)  # VATSIM user ID
    name = Column(String(100), nullable=True)  # Pilot name
    server = Column(String(50), nullable=True)  # Network server
    pilot_rating = Column(Integer, nullable=True)  # Pilot rating - using Integer for consistency
    military_rating = Column(Integer, nullable=True)  # Military rating from VATSIM API
    transponder = Column(String(10), nullable=True)  # Transponder code
    qnh_i_hg = Column(Float, nullable=True)  # QNH pressure in inches Hg from VATSIM API
    qnh_mb = Column(Integer, nullable=True)  # QNH pressure in millibars from VATSIM API
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
        Index('idx_flights_callsign', 'callsign'),
        Index('idx_flights_callsign_status', 'callsign', 'last_updated'),
        Index('idx_flights_position', 'latitude', 'longitude'),
        Index('idx_flights_departure_arrival', 'departure', 'arrival'),
        Index('idx_flights_cid_server', 'cid', 'server'),
        Index('idx_flights_altitude', 'altitude'),
        Index('idx_flights_flight_rules', 'flight_rules'),
        Index('idx_flights_planned_altitude', 'planned_altitude'),
        Index('idx_flights_aircraft_short', 'aircraft_short'),
        Index('idx_flights_revision_id', 'revision_id'),
        
        # ATC Detection Performance Indexes
        Index('idx_flights_callsign_departure_arrival', 'callsign', 'departure', 'arrival'),
        Index('idx_flights_callsign_logon', 'callsign', 'logon_time'),
    )
    
    # Validation handled by database constraints - no Python validators needed

class Transceiver(Base):
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
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('frequency >= 0', name='valid_frequency'),
        CheckConstraint('entity_type IN (\'flight\', \'atc\')', name='valid_entity_type'),
        Index('idx_transceivers_callsign_timestamp', 'callsign', 'timestamp'),
        Index('idx_transceivers_entity', 'entity_type', 'entity_id'),
        Index('idx_transceivers_frequency', 'frequency'),
        
        # ATC Detection Performance Indexes
        Index('idx_transceivers_entity_type_callsign', 'entity_type', 'callsign'),
        Index('idx_transceivers_entity_type_timestamp', 'entity_type', 'timestamp'),
        Index('idx_transceivers_atc_detection', 'entity_type', 'callsign', 'timestamp', 'frequency', 'position_lat', 'position_lon'),
        
        # Performance-optimized index for controller flight counting queries
        Index('idx_transceivers_flight_frequency_callsign', 'entity_type', 'frequency', 'callsign'),
    )
    
    # Validation handled by database constraints - no Python validators needed

class FlightSectorOccupancy(Base, TimestampMixin):
    """Flight sector occupancy model for tracking aircraft entry/exit from Australian airspace sectors"""
    __tablename__ = "flight_sector_occupancy"
    
    id = Column(BigInteger, primary_key=True, index=True)
    callsign = Column(String(50), nullable=False, index=True)  # Flight callsign (e.g., QFA123, PHENX88)
    sector_name = Column(String(10), nullable=False, index=True)  # Australian airspace sector identifier (e.g., SYA, BLA, WOL)
    entry_timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)  # When flight entered sector
    exit_timestamp = Column(TIMESTAMP(timezone=True), nullable=True)  # When flight exited sector (nullable)
    duration_seconds = Column(Integer, default=0)  # Time spent in sector (calculated)
    entry_lat = Column(Float, nullable=False)  # Entry latitude
    entry_lon = Column(Float, nullable=False)  # Entry longitude
    exit_lat = Column(Float, nullable=True)  # Exit latitude (nullable)
    exit_lon = Column(Float, nullable=True)  # Exit longitude (nullable)
    entry_altitude = Column(Integer, nullable=True)  # Entry altitude in feet
    exit_altitude = Column(Integer, nullable=True)  # Exit altitude in feet
    
    # Constraints
    __table_args__ = (
        CheckConstraint('entry_lat >= -90 AND entry_lat <= 90', name='valid_entry_latitude'),
        CheckConstraint('entry_lon >= -180 AND entry_lon <= 180', name='valid_entry_longitude'),
        CheckConstraint('exit_lat >= -90 AND exit_lat <= 90', name='valid_exit_latitude'),
        CheckConstraint('exit_lon >= -180 AND exit_lon <= 180', name='valid_exit_longitude'),
        CheckConstraint('duration_seconds >= 0', name='valid_duration'),
        Index('idx_flight_sector_occupancy_callsign', 'callsign'),
        Index('idx_flight_sector_occupancy_entry_timestamp', 'entry_timestamp'),
        Index('idx_flight_sector_occupancy_sector_name', 'sector_name'),
        Index('idx_flight_sector_occupancy_callsign_sector', 'callsign', 'sector_name'),
    )

class FlightSummary(Base, TimestampMixin):
    """Flight summary model for completed flights with sector breakdown and analytics"""
    __tablename__ = "flight_summaries"
    
    id = Column(BigInteger, primary_key=True, index=True)
    callsign = Column(String(50), nullable=False, index=True)  # Flight callsign
    aircraft_type = Column(String(20), nullable=True)  # Aircraft type
    departure = Column(String(10), nullable=True, index=True)  # Departure airport
    arrival = Column(String(10), nullable=True, index=True)  # Arrival airport
    deptime = Column(String(10), nullable=True)  # Departure time from flight plan
    logon_time = Column(TIMESTAMP(timezone=True), nullable=True)  # When pilot connected
    route = Column(Text, nullable=True)  # Flight plan route
    flight_rules = Column(String(10), nullable=True)  # IFR/VFR
    aircraft_faa = Column(String(20), nullable=True)  # FAA aircraft code
    aircraft_short = Column(String(20), nullable=True)  # Short aircraft code
    planned_altitude = Column(String(10), nullable=True)  # Planned cruise altitude
    cid = Column(Integer, nullable=True, index=True)  # VATSIM user ID
    name = Column(String(100), nullable=True)  # Pilot name
    server = Column(String(50), nullable=True)  # Network server
    pilot_rating = Column(Integer, nullable=True)  # Pilot rating
    military_rating = Column(Integer, nullable=True)  # Military rating
    controller_callsigns = Column(Text, nullable=True)  # JSON array of ATC callsigns
    controller_time_percentage = Column(Float, nullable=True)  # Percentage of time on ATC
    time_online_minutes = Column(Integer, nullable=True)  # Total time online
    primary_enroute_sector = Column(String(10), nullable=True)  # Primary sector flown
    total_enroute_sectors = Column(Integer, nullable=True)  # Total sectors visited
    total_enroute_time_minutes = Column(Integer, nullable=True)  # Total enroute time
    sector_breakdown = Column(Text, nullable=True)  # JSON sector breakdown
    completion_time = Column(TIMESTAMP(timezone=True), nullable=True)  # When flight completed
    
    # Constraints
    __table_args__ = (
        CheckConstraint('pilot_rating >= 0 AND pilot_rating <= 63', name='valid_pilot_rating'),
        CheckConstraint('military_rating >= 0 AND military_rating <= 63', name='valid_military_rating'),
        CheckConstraint('controller_time_percentage >= 0 AND controller_time_percentage <= 100', name='valid_controller_time'),
        CheckConstraint('time_online_minutes >= 0', name='valid_time_online'),
        CheckConstraint('total_enroute_sectors >= 0', name='valid_total_sectors'),
        CheckConstraint('total_enroute_time_minutes >= 0', name='valid_enroute_time'),
        Index('idx_flight_summaries_callsign', 'callsign'),
        Index('idx_flight_summaries_departure_arrival', 'departure', 'arrival'),
        Index('idx_flight_summaries_completion_time', 'completion_time'),
        Index('idx_flight_summaries_primary_sector', 'primary_enroute_sector'),
        Index('idx_flight_summaries_cid', 'cid'),
    )

class ControllerSummary(Base, TimestampMixin):
    """Controller summary model for completed ATC sessions with aircraft interaction data"""
    __tablename__ = "controller_summaries"
    
    id = Column(BigInteger, primary_key=True, index=True)
    callsign = Column(String(50), nullable=False, index=True)  # Controller callsign
    cid = Column(Integer, nullable=True, index=True)  # Controller ID from VATSIM
    name = Column(String(100), nullable=True)  # Controller name
    session_start_time = Column(TIMESTAMP(timezone=True), nullable=False, index=True)  # Session start
    session_end_time = Column(TIMESTAMP(timezone=True), nullable=True, index=True)  # Session end
    session_duration_minutes = Column(Integer, nullable=True, default=0)  # Session duration
    rating = Column(Integer, nullable=True, index=True)  # Controller rating
    facility = Column(Integer, nullable=True, index=True)  # Facility type
    server = Column(String(50), nullable=True)  # Network server
    total_aircraft_handled = Column(Integer, nullable=True, default=0)  # Total aircraft count
    peak_aircraft_count = Column(Integer, nullable=True, default=0)  # Peak aircraft count
    hourly_aircraft_breakdown = Column(Text, nullable=True)  # JSON hourly breakdown
    frequencies_used = Column(Text, nullable=True)  # JSON array of frequencies
    aircraft_details = Column(Text, nullable=True)  # JSON aircraft interaction details
    
    # Constraints
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 11', name='valid_rating'),
        CheckConstraint('total_aircraft_handled >= 0', name='valid_aircraft_counts'),
        CheckConstraint('peak_aircraft_count >= 0 AND peak_aircraft_count <= total_aircraft_handled', name='valid_peak_aircraft'),
        CheckConstraint('session_duration_minutes >= 0', name='valid_session_duration'),
        CheckConstraint('session_end_time IS NULL OR session_end_time > session_start_time', name='valid_session_times'),
        Index('idx_controller_summaries_callsign', 'callsign'),
        Index('idx_controller_summaries_callsign_session', 'callsign', 'session_start_time'),
        Index('idx_controller_summaries_session_time', 'session_start_time', 'session_end_time'),
        Index('idx_controller_summaries_rating', 'rating'),
        Index('idx_controller_summaries_facility', 'facility'),
        Index('idx_controller_summaries_duration_aircraft', 'session_duration_minutes', 'total_aircraft_handled'),
        Index('idx_controller_summaries_rating_facility', 'rating', 'facility'),
        Index('idx_controller_summaries_aircraft_count', 'total_aircraft_handled'),
    )

class ControllersArchive(Base, TimestampMixin):
    """Archive table for old controller records after summarization"""
    __tablename__ = "controllers_archive"
    
    id = Column(Integer, primary_key=True)  # Keep original ID for reference
    callsign = Column(String(50), nullable=False)  # Controller callsign
    frequency = Column(String(20), nullable=True)  # Frequency used
    cid = Column(Integer, nullable=True)  # Controller ID
    name = Column(String(100), nullable=True)  # Controller name
    rating = Column(Integer, nullable=True)  # Controller rating
    facility = Column(Integer, nullable=True)  # Facility type
    visual_range = Column(Integer, nullable=True)  # Visual range
    text_atis = Column(Text, nullable=True)  # ATIS text
    server = Column(String(50), nullable=True)  # Network server
    last_updated = Column(TIMESTAMP(timezone=True), nullable=True)  # Last update
    logon_time = Column(TIMESTAMP(timezone=True), nullable=True)  # Logon time
    archived_at = Column(TIMESTAMP(timezone=True), default=func.now())  # When archived
    
    # Constraints
    __table_args__ = (
        CheckConstraint('rating >= -1 AND rating <= 12', name='valid_rating'),
        CheckConstraint('facility >= 0 AND facility <= 6', name='valid_facility'),
        CheckConstraint('visual_range >= 0', name='valid_visual_range'),
        Index('idx_controllers_archive_callsign', 'callsign'),
        Index('idx_controllers_archive_cid', 'cid'),
        Index('idx_controllers_archive_archived_at', 'archived_at'),
    )

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
