from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, SmallInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import json

class Controller(Base):
    """Controller model representing ATC controllers"""
    __tablename__ = "controllers"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(50), unique=True, index=True, nullable=False)
    facility = Column(String(50), nullable=False)
    position = Column(String(50), nullable=True)
    status = Column(String(20), default="offline")  # online, offline, busy
    frequency = Column(String(20), nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    workload_score = Column(Float, default=0.0)
    preferences = Column(Text, nullable=True)  # JSON string for controller preferences
    
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
    
    # Relationships
    controller = relationship("Controller", back_populates="sectors")
    flights = relationship("Flight", back_populates="sector")

class Flight(Base):
    """Flight model representing active flights - OPTIMIZED FOR STORAGE"""
    __tablename__ = "flights"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(20), nullable=False, index=True)
    pilot_name = Column(String(100), nullable=True)  # Actual pilot name from VATSIM
    aircraft_type = Column(String(10), nullable=True)
    departure = Column(String(10), nullable=True)
    arrival = Column(String(10), nullable=True)
    route = Column(Text, nullable=True)
    altitude = Column(SmallInteger, nullable=True)  # SMALLINT: 0-65,535 feet (saves 50% storage)
    speed = Column(SmallInteger, nullable=True)     # SMALLINT: 0-65,535 knots (saves 50% storage)
    position_lat = Column(Integer, nullable=True)   # Compressed lat: multiply by 1M for precision
    position_lng = Column(Integer, nullable=True)   # Compressed lng: multiply by 1M for precision
    controller_id = Column(Integer, ForeignKey("controllers.id"), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    controller = relationship("Controller", back_populates="flights")
    sector = relationship("Sector", back_populates="flights")
    
    @property
    def position(self):
        """Get position as JSON string (for compatibility)"""
        if self.position_lat and self.position_lng:
            return json.dumps({
                'lat': self.position_lat / 1000000.0,
                'lng': self.position_lng / 1000000.0
            })
        return None
    
    @position.setter
    def position(self, value):
        """Set position from JSON string (for compatibility)"""
        if isinstance(value, str):
            try:
                pos = json.loads(value)
                self.position_lat = int(pos.get('lat', 0) * 1000000)
                self.position_lng = int(pos.get('lng', 0) * 1000000)
            except:
                self.position_lat = None
                self.position_lng = None
        elif isinstance(value, dict):
            self.position_lat = int(value.get('lat', 0) * 1000000)
            self.position_lng = int(value.get('lng', 0) * 1000000)
        else:
            self.position_lat = None
            self.position_lng = None

class TrafficMovement(Base):
    """Traffic movement model for tracking arrivals/departures"""
    __tablename__ = "traffic_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    callsign = Column(String(20), nullable=False, index=True)
    airport_icao = Column(String(10), nullable=False, index=True)
    movement_type = Column(String(10), nullable=False)  # 'arrival' or 'departure'
    aircraft_type = Column(String(10), nullable=True)
    pilot_name = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    confidence_score = Column(Float, default=1.0)  # 0.0-1.0 confidence in detection
    detection_method = Column(String(50), nullable=True)  # 'flight_plan', 'position', 'manual'
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=True)
    
    # Relationships
    flight = relationship("Flight")

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