#!/usr/bin/env python3
"""
Traffic Analysis Service for VATSIM Data Collection System

This service handles movement detection and traffic data analysis for the VATSIM
data collection system. It provides algorithms for detecting airport arrivals and
departures, calculating traffic patterns, and generating traffic analytics.

INPUTS:
- Flight data with position, altitude, speed information
- Airport configuration and detection thresholds
- Movement detection configuration settings
- Historical traffic data for trend analysis

OUTPUTS:
- Detected traffic movements (arrivals/departures)
- Traffic pattern analysis and trends
- Movement confidence scores
- Traffic summary statistics
- Airport-specific traffic analytics

ANALYSIS FEATURES:
- Airport arrival/departure detection
- Distance and altitude-based movement validation
- Confidence scoring for movement detection
- Traffic pattern trend analysis
- Regional traffic summaries
- Airport-specific traffic statistics

DETECTION ALGORITHMS:
- Distance-based airport proximity detection
- Altitude threshold validation
- Speed-based movement classification
- Confidence scoring with multiple factors
- Configurable detection parameters

CONFIGURATION:
- Airport-specific detection thresholds
- Default detection parameters
- Confidence scoring weights
- Movement validation criteria

OPTIMIZATIONS:
- Efficient distance calculations (Haversine)
- Database query optimization
- Configurable detection sensitivity
- Batch processing for multiple flights
"""

import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from ..models import Flight, TrafficMovement, AirportConfig, MovementDetectionConfig
from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation, create_error_handler
from ..utils.exceptions import DataProcessingError, ValidationError

class TrafficAnalysisService:
    """Service for analyzing traffic movements and patterns"""
    
    def __init__(self, db: Session):
        self.db = db
        self.error_handler = create_error_handler("traffic_analysis_service")
        self.config = self._load_detection_config()
    
    def _load_detection_config(self) -> Dict[str, Any]:
        """Load movement detection configuration from database"""
        try:
            configs = self.db.query(MovementDetectionConfig).filter(
                MovementDetectionConfig.is_active == True
            ).all()
            
            config_dict = {}
            for config in configs:
                try:
                    config_dict[config.config_key] = json.loads(config.config_value)
                except json.JSONDecodeError:
                    config_dict[config.config_key] = config.config_value
            
            # Set defaults if not configured
            defaults = {
                'default_detection_radius_nm': 10.0,
                'default_departure_altitude_threshold': 1000,
                'default_arrival_altitude_threshold': 3000,
                'default_departure_speed_threshold': 50,
                'default_arrival_speed_threshold': 150,
                'confidence_threshold': 0.7,
                'position_update_interval_seconds': 30
            }
            
            for key, default_value in defaults.items():
                if key not in config_dict:
                    config_dict[key] = default_value
            
            return config_dict
            
        except Exception as e:
            self.error_handler.logger.error(f"Error loading detection config: {e}")
            return {}
    
    @handle_service_errors
    @log_operation("calculate_distance")
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in nautical miles"""
        try:
            # Convert to radians
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            # Haversine formula
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Earth radius in nautical miles
            earth_radius_nm = 3440.065
            distance = earth_radius_nm * c
            
            return distance
        except Exception as e:
            self.error_handler.logger.error(f"Error calculating distance: {e}")
            return float('inf')
    
    @handle_service_errors
    @log_operation("get_airport_config")
    def get_airport_config(self, icao_code: str) -> Optional[AirportConfig]:
        """Get airport configuration for movement detection"""
        try:
            return self.db.query(AirportConfig).filter(
                and_(
                    AirportConfig.icao_code == icao_code.upper(),
                    AirportConfig.is_active == True
                )
            ).first()
        except Exception as e:
            self.error_handler.logger.error(f"Error getting airport config for {icao_code}: {e}")
            return None
    
    def detect_movements(self, flights: List[Flight]) -> List[TrafficMovement]:
        """Detect traffic movements from current flight data"""
        movements = []
        
        try:
            for flight in flights:
                if not flight.position or not flight.departure or not flight.arrival:
                    continue
                
                # Parse position
                try:
                    position_data = json.loads(flight.position)
                    flight_lat = position_data.get('latitude')
                    flight_lon = position_data.get('longitude')
                    
                    if not flight_lat or not flight_lon:
                        continue
                except (json.JSONDecodeError, TypeError):
                    continue
                
                # Check for departure
                departure_movement = self._detect_departure(flight, flight_lat, flight_lon)
                if departure_movement:
                    movements.append(departure_movement)
                
                # Check for arrival
                arrival_movement = self._detect_arrival(flight, flight_lat, flight_lon)
                if arrival_movement:
                    movements.append(arrival_movement)
        
        except Exception as e:
            self.error_handler.logger.error(f"Error detecting movements: {e}")
        
        return movements
    
    def _detect_departure(self, flight: Flight, lat: float, lon: float) -> Optional[TrafficMovement]:
        """Detect departure movement for a flight"""
        try:
            airport_config = self.get_airport_config(flight.departure)
            if not airport_config:
                return None
            
            # Calculate distance to departure airport
            distance = self.calculate_distance(lat, lon, airport_config.latitude, airport_config.longitude)
            
            # Check if within detection radius
            if distance > airport_config.detection_radius_nm:
                return None
            
            # Check altitude and speed thresholds
            altitude_ok = flight.altitude and flight.altitude <= airport_config.departure_altitude_threshold
            speed_ok = flight.speed and flight.speed <= airport_config.departure_speed_threshold
            
            if altitude_ok and speed_ok:
                # Check if this movement was already recorded recently
                recent_movement = self.db.query(TrafficMovement).filter(
                    and_(
                        TrafficMovement.aircraft_callsign == flight.callsign,
                        TrafficMovement.airport_code == flight.departure.upper(),
                        TrafficMovement.movement_type == 'departure',
                        TrafficMovement.timestamp >= datetime.utcnow() - timedelta(minutes=5)
                    )
                ).first()
                
                if not recent_movement:
                    confidence = self._calculate_departure_confidence(flight, distance, altitude_ok, speed_ok)
                    
                    movement = TrafficMovement(
                        aircraft_callsign=flight.callsign,
                        airport_code=flight.departure.upper(),
                        movement_type='departure',
                        aircraft_type=flight.aircraft_type,
                        timestamp=datetime.utcnow(),
                        altitude=flight.altitude,
                        speed=flight.speed,
                        heading=flight.heading
                    )
                    
                    return movement
        
        except Exception as e:
            self.error_handler.logger.error(f"Error detecting departure for {flight.callsign}: {e}")
        
        return None
    
    def _detect_arrival(self, flight: Flight, lat: float, lon: float) -> Optional[TrafficMovement]:
        """Detect arrival movement for a flight"""
        try:
            airport_config = self.get_airport_config(flight.arrival)
            if not airport_config:
                return None
            
            # Calculate distance to arrival airport
            distance = self.calculate_distance(lat, lon, airport_config.latitude, airport_config.longitude)
            
            # Check if within detection radius
            if distance > airport_config.detection_radius_nm:
                return None
            
            # Check altitude and speed thresholds
            altitude_ok = flight.altitude and flight.altitude <= airport_config.arrival_altitude_threshold
            speed_ok = flight.speed and flight.speed <= airport_config.arrival_speed_threshold
            
            if altitude_ok and speed_ok:
                # Check if this movement was already recorded recently
                recent_movement = self.db.query(TrafficMovement).filter(
                    and_(
                        TrafficMovement.aircraft_callsign == flight.callsign,
                        TrafficMovement.airport_code == flight.arrival.upper(),
                        TrafficMovement.movement_type == 'arrival',
                        TrafficMovement.timestamp >= datetime.utcnow() - timedelta(minutes=5)
                    )
                ).first()
                
                if not recent_movement:
                    confidence = self._calculate_arrival_confidence(flight, distance, altitude_ok, speed_ok)
                    
                    movement = TrafficMovement(
                        aircraft_callsign=flight.callsign,
                        airport_code=flight.arrival.upper(),
                        movement_type='arrival',
                        aircraft_type=flight.aircraft_type,
                        timestamp=datetime.utcnow(),
                        altitude=flight.altitude,
                        speed=flight.speed,
                        heading=flight.heading
                    )
                    
                    return movement
        
        except Exception as e:
            self.error_handler.logger.error(f"Error detecting arrival for {flight.callsign}: {e}")
        
        return None
    
    def _calculate_departure_confidence(self, flight: Flight, distance: float, altitude_ok: bool, speed_ok: bool) -> float:
        """Calculate confidence score for departure detection"""
        confidence = 0.5  # Base confidence
        
        # Distance factor (closer = higher confidence)
        max_distance = self.config.get('default_detection_radius_nm', 10.0)
        distance_factor = 1.0 - (distance / max_distance)
        confidence += distance_factor * 0.3
        
        # Altitude and speed factors
        if altitude_ok:
            confidence += 0.1
        if speed_ok:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_arrival_confidence(self, flight: Flight, distance: float, altitude_ok: bool, speed_ok: bool) -> float:
        """Calculate confidence score for arrival detection"""
        confidence = 0.5  # Base confidence
        
        # Distance factor (closer = higher confidence)
        max_distance = self.config.get('default_detection_radius_nm', 10.0)
        distance_factor = 1.0 - (distance / max_distance)
        confidence += distance_factor * 0.3
        
        # Altitude and speed factors
        if altitude_ok:
            confidence += 0.1
        if speed_ok:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def get_movements_by_airport(self, airport_code: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get movements for a specific airport within time range"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            movements = self.db.query(TrafficMovement).filter(
                and_(
                    TrafficMovement.airport_code == airport_code.upper(),
                    TrafficMovement.timestamp >= cutoff_time
                )
            ).order_by(desc(TrafficMovement.timestamp)).all()
            
            movements_data = []
            for movement in movements:
                movements_data.append({
                    "id": movement.id,
                    "aircraft_callsign": movement.aircraft_callsign,
                    "airport_code": movement.airport_code,
                    "movement_type": movement.movement_type,
                    "aircraft_type": movement.aircraft_type,
                    "timestamp": movement.timestamp.isoformat() if movement.timestamp else None,
                    "runway": movement.runway,
                    "altitude": movement.altitude,
                    "speed": movement.speed,
                    "heading": movement.heading
                })
            
            return movements_data
            
        except Exception as e:
            self.error_handler.logger.error(f"Error getting movements for {airport_code}: {e}")
            return []
    
    def get_movements_summary(self, region: str = 'Australia', hours: int = 24) -> Dict[str, Any]:
        """Get summary of movements by airport for a region"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get airports in region
            airports = self.db.query(AirportConfig).filter(
                and_(
                    AirportConfig.region == region,
                    AirportConfig.is_active == True
                )
            ).all()
            
            summary = {}
            
            for airport in airports:
                movements = self.db.query(TrafficMovement).filter(
                    and_(
                        TrafficMovement.airport_code == airport.icao_code,
                        TrafficMovement.timestamp >= cutoff_time,
                        TrafficMovement.confidence_score >= self.config.get('confidence_threshold', 0.7)
                    )
                ).all()
                
                arrivals = [m for m in movements if m.movement_type == 'arrival']
                departures = [m for m in movements if m.movement_type == 'departure']
                
                summary[airport.icao_code] = {
                    'airport_name': airport.name,
                    'total_movements': len(movements),
                    'arrivals': len(arrivals),
                    'departures': len(departures),
                    'last_movement': movements[-1].timestamp.isoformat() if movements else None
                }
            
            return summary
        
        except Exception as e:
            self.error_handler.logger.error(f"Error getting movements summary for {region}: {e}")
            return {}
    
    def get_traffic_trends(self, airport_icao: str, days: int = 7) -> Dict[str, Any]:
        """Get traffic trends for an airport over time"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # Get daily movement counts
            daily_movements = self.db.query(
                func.date(TrafficMovement.timestamp).label('date'),
                TrafficMovement.movement_type,
                func.count(TrafficMovement.id).label('count')
            ).filter(
                and_(
                    TrafficMovement.airport_code == airport_icao.upper(),
                    TrafficMovement.timestamp >= cutoff_time,
                    TrafficMovement.confidence_score >= self.config.get('confidence_threshold', 0.7)
                )
            ).group_by(
                func.date(TrafficMovement.timestamp),
                TrafficMovement.movement_type
            ).all()
            
            # Organize by date
            trends = {}
            for record in daily_movements:
                date_str = record.date.isoformat()
                if date_str not in trends:
                    trends[date_str] = {'arrivals': 0, 'departures': 0}
                
                trends[date_str][record.movement_type + 's'] = record.count
            
            return trends
        
        except Exception as e:
            self.error_handler.logger.error(f"Error getting traffic trends for {airport_icao}: {e}")
            return {}

def get_traffic_analysis_service(db: Session) -> TrafficAnalysisService:
    """Get traffic analysis service instance"""
    return TrafficAnalysisService(db) 