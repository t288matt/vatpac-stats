from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, SmallInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import json

class ATCPosition(Base):
    """ATC Position model representing ATC positions that can be controlled or uncontrolled"""
    __tablename__ = "atc_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), unique=True, index=True, nullable=False)
    facility = Column(String(50), nullable=False)
    position = Column(String(50), nullable=True)
    status = Column(String(20), default="offline")  # online, offline, busy
    frequency = Column(String(20), nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    workload_score = Column(Float, default=0.0)
    preferences = Column(Text, nullable=True)  # JSON string for position preferences
    operator_id = Column(String(50), nullable=True, index=True)  # VATSIM user ID (links multiple positions)
    operator_name = Column(String(100), nullable=True)  # Operator's real name
    operator_rating = Column(Integer, nullable=True)  # Operator rating (0-5)
    
    # Relationships
    sectors = relationship("Sector", back_populates="atc_position")
    flights = relationship("Flight", back_populates="atc_position")

class Sector(Base):
    """Airspace sector model"""
    __tablename__ = "sectors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    facility = Column(String(50), nullable=False)
    atc_position_id = Column(Integer, ForeignKey("atc_positions.id"), nullable=True)
    traffic_density = Column(Integer, default=0)
    status = Column(String(20), default="unmanned")  # manned, unmanned, busy
    priority_level = Column(Integer, default=1)  # 1-5 priority scale
    boundaries = Column(Text, nullable=True)  # JSON string for sector boundaries
    
    # Relationships
    atc_position = relationship("ATCPosition", back_populates="sectors")

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
    flight_plan = Column(Text, nullable=True)  # JSON string
    atc_position_id = Column(Integer, ForeignKey("atc_positions.id"), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    departure = Column(String(10), nullable=True)
    arrival = Column(String(10), nullable=True)
    route = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active, completed, cancelled
    
    # Relationships
    atc_position = relationship("ATCPosition", back_populates="flights")
    
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
    atc_position_id = Column(Integer, ForeignKey("atc_positions.id"), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    completed_at = Column(DateTime, nullable=False)
    
    # Relationships
    atc_position = relationship("ATCPosition")
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

class MovementDetectionConfig(Base):
    """Configuration for movement detection algorithms"""
    __tablename__ = "movement_detection_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)

class SystemConfig(Base):
    """System configuration model"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    environment = Column(String(20), default="development")

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