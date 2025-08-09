#!/usr/bin/env python3
"""
Frequency Matching Service for VATSIM Data Collection System

This service detects when pilots and ATC controllers are on the same frequency,
enabling analysis of communication patterns and frequency utilization.

INPUTS:
- Transceiver data from VATSIM API
- Controller frequency data
- Flight position and status data
- Real-time VATSIM network data

OUTPUTS:
- Frequency matching events and statistics
- Communication pattern analysis
- Frequency utilization metrics
- Real-time frequency matching alerts

FEATURES:
- Real-time frequency matching detection
- Communication pattern analysis
- Frequency utilization statistics
- Historical frequency matching data
- Geographic frequency matching analysis
- Controller workload based on frequency usage

DATA STRUCTURES:
- FrequencyMatch: Individual frequency matching event
- FrequencyMatchSummary: Aggregated frequency matching statistics
- CommunicationPattern: Pattern analysis of frequency usage
- FrequencyUtilization: Frequency usage metrics and statistics
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from ..database import SessionLocal
from ..models import Transceiver, Controller, Flight, FrequencyMatch as FrequencyMatchModel
from ..utils.error_handling import handle_service_errors, log_operation
from ..utils.exceptions import ServiceError
from ..config_package.service import ServiceConfig


@dataclass
class FrequencyMatch:
    """Individual frequency matching event"""
    id: Optional[int] = None
    pilot_callsign: str = ""
    controller_callsign: str = ""
    frequency: int = 0  # Frequency in Hz
    pilot_lat: Optional[float] = None
    pilot_lon: Optional[float] = None
    controller_lat: Optional[float] = None
    controller_lon: Optional[float] = None
    distance_nm: Optional[float] = None  # Distance between pilot and controller
    match_timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_seconds: Optional[int] = None
    is_active: bool = True
    match_confidence: float = 1.0  # Confidence score for the match
    communication_type: str = "unknown"  # 'approach', 'departure', 'enroute', 'ground', 'tower'
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FrequencyMatchSummary:
    """Aggregated frequency matching statistics"""
    total_matches: int = 0
    active_matches: int = 0
    unique_pilots: int = 0
    unique_controllers: int = 0
    unique_frequencies: int = 0
    avg_match_duration: float = 0.0
    most_common_frequency: Optional[int] = None
    busiest_controller: Optional[str] = None
    busiest_pilot: Optional[str] = None
    communication_patterns: Dict[str, int] = field(default_factory=dict)
    geographic_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class CommunicationPattern:
    """Pattern analysis of frequency usage"""
    frequency: int
    total_communications: int = 0
    unique_pilots: int = 0
    unique_controllers: int = 0
    avg_duration: float = 0.0
    peak_hours: Dict[int, int] = field(default_factory=dict)  # Hour -> count
    communication_types: Dict[str, int] = field(default_factory=dict)
    geographic_centers: List[Tuple[float, float]] = field(default_factory=list)


class FrequencyMatchingService:
    """
    Service for detecting and analyzing frequency matches between pilots and ATC
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = ServiceConfig.load_from_env()
        
        # Configuration for frequency matching
        self.max_distance_nm = 100.0  # Maximum distance for meaningful frequency match
        self.min_match_duration_seconds = 30  # Minimum duration to consider a match
        self.frequency_tolerance_hz = 100  # Tolerance for frequency matching (Hz)
        self.update_interval_seconds = 10  # How often to check for new matches
        
        # Cache for active matches
        self.active_matches: Dict[str, FrequencyMatch] = {}
        self.match_history: List[FrequencyMatch] = []
        
        # Statistics tracking
        self.stats = {
            'total_matches_detected': 0,
            'active_matches': 0,
            'last_update': datetime.utcnow()
        }
    
    @handle_service_errors
    @log_operation("detect_frequency_matches")
    async def detect_frequency_matches(self) -> List[FrequencyMatch]:
        """
        Detect frequency matches between pilots and ATC controllers
        
        Returns:
            List of FrequencyMatch objects representing current matches
        """
        try:
            db = SessionLocal()
            try:
                # Get current transceiver data
                current_time = datetime.utcnow()
                cutoff_time = current_time - timedelta(minutes=5)  # Only recent data
                
                # Get all active transceivers
                transceivers = db.query(Transceiver).filter(
                    Transceiver.timestamp >= cutoff_time
                ).all()
                
                # Separate pilots and controllers
                pilot_transceivers = [t for t in transceivers if t.entity_type == 'flight']
                controller_transceivers = [t for t in transceivers if t.entity_type == 'atc']
                
                # Find frequency matches
                matches = []
                for pilot_tx in pilot_transceivers:
                    for controller_tx in controller_transceivers:
                        if self._is_frequency_match(pilot_tx.frequency, controller_tx.frequency):
                            match = self._create_frequency_match(pilot_tx, controller_tx)
                            if match:
                                matches.append(match)
                
                # Update active matches
                await self._update_active_matches(matches)
                
                self.logger.info(f"Detected {len(matches)} frequency matches")
                return matches
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error detecting frequency matches: {e}")
            raise ServiceError(f"Failed to detect frequency matches: {e}")
    
    def _is_frequency_match(self, freq1: int, freq2: int) -> bool:
        """
        Check if two frequencies match within tolerance
        
        Args:
            freq1: First frequency in Hz
            freq2: Second frequency in Hz
            
        Returns:
            True if frequencies match within tolerance
        """
        if not freq1 or not freq2:
            return False
        
        return abs(freq1 - freq2) <= self.frequency_tolerance_hz
    
    def _create_frequency_match(self, pilot_tx: Transceiver, controller_tx: Transceiver) -> Optional[FrequencyMatch]:
        """
        Create a frequency match object from two transceivers
        
        Args:
            pilot_tx: Pilot transceiver data
            controller_tx: Controller transceiver data
            
        Returns:
            FrequencyMatch object or None if invalid
        """
        try:
            # Calculate distance if both have positions
            distance_nm = None
            if (pilot_tx.position_lat and pilot_tx.position_lon and 
                controller_tx.position_lat and controller_tx.position_lon):
                distance_nm = self._calculate_distance_nm(
                    pilot_tx.position_lat, pilot_tx.position_lon,
                    controller_tx.position_lat, controller_tx.position_lon
                )
            
            # Skip if distance is too far for meaningful communication
            if distance_nm and distance_nm > self.max_distance_nm:
                return None
            
            # Determine communication type based on frequency
            communication_type = self._determine_communication_type(controller_tx.frequency)
            
            # Create match object
            match = FrequencyMatch(
                pilot_callsign=pilot_tx.callsign,
                controller_callsign=controller_tx.callsign,
                frequency=pilot_tx.frequency,
                pilot_lat=pilot_tx.position_lat,
                pilot_lon=pilot_tx.position_lon,
                controller_lat=controller_tx.position_lat,
                controller_lon=controller_tx.position_lon,
                distance_nm=distance_nm,
                match_timestamp=datetime.utcnow(),
                communication_type=communication_type,
                match_confidence=self._calculate_match_confidence(pilot_tx, controller_tx, distance_nm)
            )
            
            return match
            
        except Exception as e:
            self.logger.warning(f"Error creating frequency match: {e}")
            return None
    
    def _calculate_distance_nm(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points in nautical miles using Haversine formula
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Distance in nautical miles
        """
        import math
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in nautical miles
        earth_radius_nm = 3440.065  # Nautical miles
        
        return earth_radius_nm * c
    
    def _determine_communication_type(self, frequency: int) -> str:
        """
        Determine communication type based on frequency
        
        Args:
            frequency: Frequency in Hz
            
        Returns:
            Communication type string
        """
        # Common VATSIM frequency ranges (in Hz)
        if 118000000 <= frequency <= 136000000:  # VHF COM
            if 118000000 <= frequency <= 121000000:
                return "approach"
            elif 121000000 <= frequency <= 123000000:
                return "departure"
            elif 123000000 <= frequency <= 125000000:
                return "tower"
            elif 125000000 <= frequency <= 127000000:
                return "ground"
            else:
                return "enroute"
        elif 20000000 <= frequency <= 30000000:  # HF COM
            return "hf_enroute"
        else:
            return "unknown"
    
    def _calculate_match_confidence(self, pilot_tx: Transceiver, controller_tx: Transceiver, distance_nm: Optional[float]) -> float:
        """
        Calculate confidence score for frequency match
        
        Args:
            pilot_tx: Pilot transceiver data
            controller_tx: Controller transceiver data
            distance_nm: Distance between pilot and controller
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 1.0
        
        # Reduce confidence if no position data
        if not pilot_tx.position_lat or not controller_tx.position_lat:
            confidence *= 0.8
        
        # Reduce confidence if distance is too far
        if distance_nm and distance_nm > 50:
            confidence *= 0.6
        
        # Reduce confidence if frequency tolerance is high
        freq_diff = abs(pilot_tx.frequency - controller_tx.frequency)
        if freq_diff > 50:
            confidence *= 0.9
        
        return max(0.0, min(1.0, confidence))
    
    async def _update_active_matches(self, current_matches: List[FrequencyMatch]) -> None:
        """
        Update active matches tracking
        
        Args:
            current_matches: List of current frequency matches
        """
        current_time = datetime.utcnow()
        
        # Create lookup for current matches
        current_match_keys = set()
        for match in current_matches:
            key = f"{match.pilot_callsign}_{match.controller_callsign}_{match.frequency}"
            current_match_keys.add(key)
            
            # Update existing match or create new one
            if key in self.active_matches:
                # Update duration for existing match
                existing_match = self.active_matches[key]
                duration = (current_time - existing_match.match_timestamp).total_seconds()
                existing_match.duration_seconds = int(duration)
            else:
                # New match
                self.active_matches[key] = match
                self.stats['total_matches_detected'] += 1
        
        # Remove inactive matches
        inactive_keys = []
        for key, match in self.active_matches.items():
            if key not in current_match_keys:
                # Mark as inactive and add to history
                match.is_active = False
                self.match_history.append(match)
                inactive_keys.append(key)
        
        for key in inactive_keys:
            del self.active_matches[key]
        
        # Update statistics
        self.stats['active_matches'] = len(self.active_matches)
        self.stats['last_update'] = current_time
    
    @handle_service_errors
    @log_operation("store_frequency_matches")
    async def store_frequency_matches(self, matches: List[FrequencyMatch]) -> int:
        """
        Store frequency matches in database
        
        Args:
            matches: List of FrequencyMatch objects to store
            
        Returns:
            Number of matches stored
        """
        try:
            db = SessionLocal()
            try:
                stored_count = 0
                for match in matches:
                    # Convert to database model
                    db_match = FrequencyMatchModel(
                        pilot_callsign=match.pilot_callsign,
                        controller_callsign=match.controller_callsign,
                        frequency=match.frequency,
                        pilot_lat=match.pilot_lat,
                        pilot_lon=match.pilot_lon,
                        controller_lat=match.controller_lat,
                        controller_lon=match.controller_lon,
                        distance_nm=match.distance_nm,
                        match_timestamp=match.match_timestamp,
                        duration_seconds=match.duration_seconds,
                        is_active=match.is_active,
                        match_confidence=match.match_confidence,
                        communication_type=match.communication_type
                    )
                    db.add(db_match)
                    stored_count += 1
                
                db.commit()
                self.logger.info(f"Stored {stored_count} frequency matches in database")
                return stored_count
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error storing frequency matches: {e}")
            raise ServiceError(f"Failed to store frequency matches: {e}")
    
    @handle_service_errors
    @log_operation("get_historical_frequency_matches")
    async def get_historical_frequency_matches(
        self, 
        pilot_callsign: Optional[str] = None,
        controller_callsign: Optional[str] = None,
        frequency: Optional[int] = None,
        hours: int = 24
    ) -> List[FrequencyMatch]:
        """
        Get historical frequency matches from database
        
        Args:
            pilot_callsign: Optional pilot callsign filter
            controller_callsign: Optional controller callsign filter
            frequency: Optional frequency filter (in Hz)
            hours: Number of hours to look back
            
        Returns:
            List of FrequencyMatch objects
        """
        try:
            db = SessionLocal()
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                
                query = db.query(FrequencyMatchModel).filter(
                    FrequencyMatchModel.match_timestamp >= cutoff_time
                )
                
                if pilot_callsign:
                    query = query.filter(FrequencyMatchModel.pilot_callsign.ilike(f"%{pilot_callsign}%"))
                
                if controller_callsign:
                    query = query.filter(FrequencyMatchModel.controller_callsign.ilike(f"%{controller_callsign}%"))
                
                if frequency:
                    tolerance = 100  # Hz tolerance
                    query = query.filter(
                        and_(
                            FrequencyMatchModel.frequency >= frequency - tolerance,
                            FrequencyMatchModel.frequency <= frequency + tolerance
                        )
                    )
                
                db_matches = query.order_by(FrequencyMatchModel.match_timestamp.desc()).all()
                
                # Convert to service objects
                matches = []
                for db_match in db_matches:
                    match = FrequencyMatch(
                        id=db_match.id,
                        pilot_callsign=db_match.pilot_callsign,
                        controller_callsign=db_match.controller_callsign,
                        frequency=db_match.frequency,
                        pilot_lat=db_match.pilot_lat,
                        pilot_lon=db_match.pilot_lon,
                        controller_lat=db_match.controller_lat,
                        controller_lon=db_match.controller_lon,
                        distance_nm=db_match.distance_nm,
                        match_timestamp=db_match.match_timestamp,
                        duration_seconds=db_match.duration_seconds,
                        is_active=db_match.is_active,
                        match_confidence=db_match.match_confidence,
                        communication_type=db_match.communication_type,
                        created_at=db_match.created_at
                    )
                    matches.append(match)
                
                return matches
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting historical frequency matches: {e}")
            raise ServiceError(f"Failed to get historical frequency matches: {e}")
    
    @handle_service_errors
    @log_operation("update_frequency_match_duration")
    async def update_frequency_match_duration(self, match_id: int, duration_seconds: int) -> bool:
        """
        Update duration for a frequency match
        
        Args:
            match_id: Database ID of the frequency match
            duration_seconds: New duration in seconds
            
        Returns:
            True if updated successfully
        """
        try:
            db = SessionLocal()
            try:
                db_match = db.query(FrequencyMatchModel).filter(FrequencyMatchModel.id == match_id).first()
                if db_match:
                    db_match.duration_seconds = duration_seconds
                    db.commit()
                    return True
                return False
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error updating frequency match duration: {e}")
            raise ServiceError(f"Failed to update frequency match duration: {e}")
    
    @handle_service_errors
    @log_operation("mark_frequency_match_inactive")
    async def mark_frequency_match_inactive(self, match_id: int) -> bool:
        """
        Mark a frequency match as inactive
        
        Args:
            match_id: Database ID of the frequency match
            
        Returns:
            True if updated successfully
        """
        try:
            db = SessionLocal()
            try:
                db_match = db.query(FrequencyMatchModel).filter(FrequencyMatchModel.id == match_id).first()
                if db_match:
                    db_match.is_active = False
                    db.commit()
                    return True
                return False
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error marking frequency match inactive: {e}")
            raise ServiceError(f"Failed to mark frequency match inactive: {e}")
    
    @handle_service_errors
    @log_operation("get_frequency_match_summary")
    async def get_frequency_match_summary(self) -> FrequencyMatchSummary:
        """
        Get summary statistics for frequency matching
        
        Returns:
            FrequencyMatchSummary object with aggregated statistics
        """
        try:
            db = SessionLocal()
            try:
                # Get current active matches
                active_matches = list(self.active_matches.values())
                
                # Calculate summary statistics
                unique_pilots = len(set(match.pilot_callsign for match in active_matches))
                unique_controllers = len(set(match.controller_callsign for match in active_matches))
                unique_frequencies = len(set(match.frequency for match in active_matches))
                
                # Calculate average duration
                durations = [match.duration_seconds or 0 for match in active_matches]
                avg_duration = sum(durations) / len(durations) if durations else 0.0
                
                # Find most common frequency
                frequency_counts = {}
                for match in active_matches:
                    frequency_counts[match.frequency] = frequency_counts.get(match.frequency, 0) + 1
                
                most_common_frequency = max(frequency_counts.items(), key=lambda x: x[1])[0] if frequency_counts else None
                
                # Find busiest controller and pilot
                controller_counts = {}
                pilot_counts = {}
                for match in active_matches:
                    controller_counts[match.controller_callsign] = controller_counts.get(match.controller_callsign, 0) + 1
                    pilot_counts[match.pilot_callsign] = pilot_counts.get(match.pilot_callsign, 0) + 1
                
                busiest_controller = max(controller_counts.items(), key=lambda x: x[1])[0] if controller_counts else None
                busiest_pilot = max(pilot_counts.items(), key=lambda x: x[1])[0] if pilot_counts else None
                
                # Communication patterns
                communication_patterns = {}
                for match in active_matches:
                    comm_type = match.communication_type
                    communication_patterns[comm_type] = communication_patterns.get(comm_type, 0) + 1
                
                # Geographic distribution (simplified by frequency type)
                geographic_distribution = {}
                for match in active_matches:
                    if match.distance_nm:
                        if match.distance_nm <= 10:
                            region = "local"
                        elif match.distance_nm <= 50:
                            region = "regional"
                        else:
                            region = "long_range"
                        geographic_distribution[region] = geographic_distribution.get(region, 0) + 1
                
                summary = FrequencyMatchSummary(
                    total_matches=self.stats['total_matches_detected'],
                    active_matches=len(active_matches),
                    unique_pilots=unique_pilots,
                    unique_controllers=unique_controllers,
                    unique_frequencies=unique_frequencies,
                    avg_match_duration=avg_duration,
                    most_common_frequency=most_common_frequency,
                    busiest_controller=busiest_controller,
                    busiest_pilot=busiest_pilot,
                    communication_patterns=communication_patterns,
                    geographic_distribution=geographic_distribution
                )
                
                return summary
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting frequency match summary: {e}")
            raise ServiceError(f"Failed to get frequency match summary: {e}")
    
    @handle_service_errors
    @log_operation("get_communication_patterns")
    async def get_communication_patterns(self, frequency: Optional[int] = None) -> List[CommunicationPattern]:
        """
        Get communication patterns for specific frequency or all frequencies
        
        Args:
            frequency: Optional specific frequency to analyze
            
        Returns:
            List of CommunicationPattern objects
        """
        try:
            db = SessionLocal()
            try:
                # Get historical matches for pattern analysis
                cutoff_time = datetime.utcnow() - timedelta(hours=24)  # Last 24 hours
                
                # Query historical matches (this would need to be stored in database)
                # For now, use current active matches
                matches = list(self.active_matches.values())
                
                if frequency:
                    matches = [m for m in matches if m.frequency == frequency]
                
                # Group by frequency
                frequency_groups = {}
                for match in matches:
                    if match.frequency not in frequency_groups:
                        frequency_groups[match.frequency] = []
                    frequency_groups[match.frequency].append(match)
                
                patterns = []
                for freq, freq_matches in frequency_groups.items():
                    pattern = CommunicationPattern(frequency=freq)
                    
                    # Calculate statistics
                    pattern.total_communications = len(freq_matches)
                    pattern.unique_pilots = len(set(m.pilot_callsign for m in freq_matches))
                    pattern.unique_controllers = len(set(m.controller_callsign for m in freq_matches))
                    
                    # Average duration
                    durations = [m.duration_seconds or 0 for m in freq_matches]
                    pattern.avg_duration = sum(durations) / len(durations) if durations else 0.0
                    
                    # Communication types
                    for match in freq_matches:
                        comm_type = match.communication_type
                        pattern.communication_types[comm_type] = pattern.communication_types.get(comm_type, 0) + 1
                    
                    # Geographic centers (simplified)
                    for match in freq_matches:
                        if match.pilot_lat and match.pilot_lon:
                            pattern.geographic_centers.append((match.pilot_lat, match.pilot_lon))
                    
                    patterns.append(pattern)
                
                return patterns
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error getting communication patterns: {e}")
            raise ServiceError(f"Failed to get communication patterns: {e}")
    
    @handle_service_errors
    @log_operation("health_check")
    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for frequency matching service
        
        Returns:
            Health status dictionary
        """
        try:
            current_time = datetime.utcnow()
            time_since_update = (current_time - self.stats['last_update']).total_seconds()
            
            health_status = {
                "status": "healthy" if time_since_update < 60 else "stale",
                "active_matches": self.stats['active_matches'],
                "total_matches_detected": self.stats['total_matches_detected'],
                "last_update_seconds_ago": int(time_since_update),
                "cache_size": len(self.active_matches),
                "history_size": len(self.match_history)
            }
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error in health check: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

def get_frequency_matching_service() -> FrequencyMatchingService:
    """
    Get the frequency matching service instance.
    
    Returns:
        FrequencyMatchingService: The frequency matching service instance
    """
    from app.services.service_manager import ServiceManager
    return ServiceManager().get_service('frequency_matching_service')
