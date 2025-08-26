#!/usr/bin/env python3
"""
ATC Detection Service

Provides ATC interaction detection for flights by analyzing transceiver data
and calculating controller contact percentages. Implements the planned 4-step
CTE logic for accurate ATC interaction tracking.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database import get_database_session
from app.utils.geographic_utils import is_within_proximity
from app.services.controller_type_detector import ControllerTypeDetector

# Configure logging
logger = logging.getLogger(__name__)

class ATCDetectionService:
    """Service for detecting ATC interactions with flights."""
    
    def __init__(self, time_window_seconds: int = None):
        """
        Initialize ATC detection service.
        
        Args:
            time_window_seconds: Time window for frequency matching (default: from environment or 180s)
        """
        import os
        
        # Load from environment variables with defaults
        self.time_window_seconds = time_window_seconds or int(os.getenv("FLIGHT_DETECTION_TIME_WINDOW_SECONDS", "180"))
        
        # Load VATSIM polling interval for accurate time calculations
        self.vatsim_polling_interval_seconds = int(os.getenv("VATSIM_POLLING_INTERVAL", "60"))
        
        # Initialize controller type detector for dynamic proximity ranges
        self.controller_type_detector = ControllerTypeDetector()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"ATC Detection Service initialized: time_window={self.time_window_seconds}s, VATSIM_polling={self.vatsim_polling_interval_seconds}s, dynamic proximity ranges enabled")
        
    async def detect_flight_atc_interactions(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> Dict[str, Any]:
        """
        Detect ATC interactions for a specific flight.
        
        Args:
            flight_callsign: Aircraft callsign
            departure: Departure airport code
            arrival: Arrival airport code
            logon_time: Flight logon time
            
        Returns:
            Dict containing ATC interaction data
        """
        try:
            self.logger.debug(f"Detecting ATC interactions for flight {flight_callsign}")
            
            # Get flight transceivers
            flight_transceivers = await self._get_flight_transceivers(flight_callsign, departure, arrival, logon_time)
            if not flight_transceivers:
                self.logger.debug(f"No transceiver data found for flight {flight_callsign}")
                return self._create_empty_atc_data()
            
            # Get ATC transceivers
            atc_transceivers = await self._get_atc_transceivers()
            if not atc_transceivers:
                self.logger.debug(f"No ATC transceiver data found")
                return self._create_empty_atc_data()
            
            # Find frequency matches with proximity and time constraints using SQL JOIN
            frequency_matches = await self._find_frequency_matches(flight_transceivers, atc_transceivers, departure, arrival, logon_time)
            
            # Calculate ATC interaction metrics
            atc_data = await self._calculate_atc_metrics(flight_callsign, departure, arrival, logon_time, frequency_matches)
            
            self.logger.debug(f"ATC detection completed for {flight_callsign}: {len(atc_data.get('controller_callsigns', {}))} controllers")
            return atc_data
            
        except Exception as e:
            self.logger.error(f"Error detecting ATC interactions for flight {flight_callsign}: {e}")
            return self._create_empty_atc_data()
    
    async def detect_flight_atc_interactions_with_timeout(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime, timeout_seconds: float = 30.0) -> Dict[str, Any]:
        """
        Detect ATC interactions for a specific flight with timeout protection.
        
        Args:
            flight_callsign: Aircraft callsign
            departure: Departure airport code
            arrival: Arrival airport code
            logon_time: Flight logon time
            timeout_seconds: Maximum time to wait for detection
            
        Returns:
            Dict containing ATC interaction data
        """
        try:
            import asyncio
            return await asyncio.wait_for(
                self.detect_flight_atc_interactions(flight_callsign, departure, arrival, logon_time),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            self.logger.error(f"ATC detection timed out after {timeout_seconds} seconds for flight {flight_callsign}")
            return self._create_empty_atc_data()
        except Exception as e:
            self.logger.error(f"Error in ATC detection with timeout for flight {flight_callsign}: {e}")
            return self._create_empty_atc_data()
    
    async def _get_flight_transceivers(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> List[Dict[str, Any]]:
        """Get transceiver data for a specific flight."""
        try:
            # Optimized query with better JOIN strategy
            query = """
                SELECT t.callsign, t.frequency, t.timestamp, t.position_lat, t.position_lon
                FROM transceivers t
                WHERE t.entity_type = 'flight' 
                AND t.callsign = :flight_callsign
                AND EXISTS (
                    SELECT 1 FROM flights f 
                    WHERE f.callsign = t.callsign 
                    AND f.departure = :departure 
                    AND f.arrival = :arrival 
                    AND f.logon_time = :logon_time
                )
                ORDER BY t.timestamp
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "flight_callsign": flight_callsign,
                    "departure": departure,
                    "arrival": arrival,
                    "logon_time": logon_time
                })
                
                transceivers = []
                for row in result.fetchall():
                    transceivers.append({
                        "callsign": row.callsign,
                        "frequency": row.frequency,
                        "frequency_mhz": row.frequency / 1000000.0,  # Convert Hz to MHz
                        "timestamp": row.timestamp,
                        "position_lat": row.position_lat,
                        "position_lon": row.position_lon
                    })
                
                return transceivers
                
        except Exception as e:
            self.logger.error(f"Error getting flight transceivers: {e}")
            return []
    
    async def _get_atc_transceivers(self) -> List[Dict[str, Any]]:
        """Get transceiver data for ATC positions."""
        try:
            # Load ALL controllers - no artificial limits
            query = """
                SELECT t.callsign, t.frequency, t.timestamp, t.position_lat, t.position_lon
                FROM transceivers t
                INNER JOIN controllers c ON t.callsign = c.callsign
                WHERE t.entity_type = 'atc' 
                AND c.facility != 0  -- Exclude observer positions
                AND t.timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY t.callsign, t.timestamp
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query))
                
                transceivers = []
                for row in result.fetchall():
                    transceivers.append({
                        "callsign": row.callsign,
                        "frequency": row.frequency,
                        "frequency_mhz": row.frequency / 1000000.0,  # Convert Hz to MHz
                        "timestamp": row.timestamp,
                        "position_lat": row.position_lat,
                        "position_lon": row.position_lon
                    })
                
                self.logger.info(f"Loaded {len(transceivers)} ATC transceiver records")
                return transceivers
                
        except Exception as e:
            self.logger.error(f"Error getting ATC transceivers: {e}")
            return []
    
    async def _find_frequency_matches(self, flight_transceivers: List[Dict], atc_transceivers: List[Dict], departure: str, arrival: str, logon_time: datetime) -> List[Dict[str, Any]]:
        """Find frequency matches using controller-specific proximity ranges."""
        try:
            # 1. Group ATC transceivers by controller callsign
            atc_by_callsign = self._group_atc_by_callsign(atc_transceivers)
            
            # 2. Process each controller with its specific proximity range
            all_matches = []
            for controller_callsign, controllers in atc_by_callsign.items():
                # Get controller type and proximity range
                controller_info = self.controller_type_detector.get_controller_info(controller_callsign)
                proximity_range = controller_info["proximity_threshold"]
                
                self.logger.debug(f"Processing controller {controller_callsign} as {controller_info['type']} with {proximity_range}nm proximity")
                
                # 3. Run proximity query for this specific controller
                controller_matches = await self._find_matches_for_controller(
                    flight_transceivers, controllers, proximity_range, departure, arrival, logon_time
                )
                all_matches.extend(controller_matches)
            
            self.logger.info(f"Controller-specific proximity processing completed: {len(all_matches)} total matches found")
            return all_matches
            
        except Exception as e:
            self.logger.error(f"Error in controller-specific frequency matching: {e}")
            return []
    
    def _group_atc_by_callsign(self, atc_transceivers: List[Dict]) -> Dict[str, List[Dict]]:
        """Group ATC transceivers by controller callsign."""
        grouped = {}
        for transceiver in atc_transceivers:
            callsign = transceiver["callsign"]
            if callsign not in grouped:
                grouped[callsign] = []
            grouped[callsign].append(transceiver)
        return grouped
    
    async def _find_matches_for_controller(self, flight_transceivers: List[Dict], controller_transceivers: List[Dict], proximity_threshold_nm: float, departure: str, arrival: str, logon_time: datetime) -> List[Dict[str, Any]]:
        """Find frequency matches for a specific controller with its proximity range."""
        try:
            # OPTIMIZED: Pre-filter by time window before expensive JOINs
            query = """
                WITH time_filtered_flights AS (
                    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                    FROM transceivers t 
                    WHERE t.entity_type = 'flight' 
                    AND t.callsign = :flight_callsign
                    AND t.timestamp >= :flight_start_time  -- Pre-filter by time
                    AND t.timestamp <= :flight_end_time
                    AND EXISTS (
                        SELECT 1 FROM flights f 
                        WHERE f.callsign = t.callsign 
                        AND f.departure = :departure 
                        AND f.arrival = :arrival 
                        AND f.logon_time = :logon_time
                    )
                ),
                time_filtered_atc AS (
                    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                    FROM transceivers t 
                    WHERE t.entity_type = 'atc' 
                    AND t.callsign = :controller_callsign
                    AND t.timestamp >= :atc_start_time  -- Pre-filter by time
                    AND t.timestamp <= :atc_end_time
                ),
                frequency_matches AS (
                    SELECT ft.callsign as flight_callsign, ft.frequency_mhz, ft.timestamp as flight_time,
                           at.callsign as atc_callsign, at.timestamp as atc_time,
                           at.position_lat as atc_lat, at.position_lon as atc_lon,
                           ft.position_lat as flight_lat, ft.position_lon as flight_lon
                    FROM time_filtered_flights ft 
                    JOIN time_filtered_atc at ON ft.frequency_mhz = at.frequency_mhz
                    WHERE ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= :time_window
                    AND (
                        -- Haversine formula with controller-specific proximity
                        (3440.065 * ACOS(
                            LEAST(1, GREATEST(-1, 
                                SIN(RADIANS(ft.position_lat)) * SIN(RADIANS(at.position_lat)) +
                                COS(RADIANS(ft.position_lat)) * COS(RADIANS(at.position_lat)) * 
                                COS(RADIANS(ft.position_lon - at.position_lon))
                            ))
                        )) <= :proximity_threshold_nm
                    )
                )
                SELECT 
                    flight_callsign,
                    atc_callsign,
                    frequency_mhz,
                    flight_time,
                    atc_time,
                    flight_lat,
                    flight_lon,
                    atc_lat,
                    atc_lon,
                    ABS(EXTRACT(EPOCH FROM (flight_time - atc_time))) as time_diff_seconds
                FROM frequency_matches
                ORDER BY flight_time, atc_time
            """
            
            # Execute with controller-specific proximity and time window pre-filtering
            async with get_database_session() as session:
                # Calculate time windows for pre-filtering (much more efficient than JOIN filtering)
                flight_start_time = logon_time - timedelta(seconds=self.time_window_seconds)
                flight_end_time = logon_time + timedelta(seconds=self.time_window_seconds)
                atc_start_time = flight_start_time - timedelta(seconds=self.time_window_seconds)
                atc_end_time = flight_end_time + timedelta(seconds=self.time_window_seconds)
                
                result = await session.execute(text(query), {
                    "flight_callsign": flight_transceivers[0]["callsign"] if flight_transceivers else "",
                    "departure": departure,
                    "arrival": arrival,
                    "logon_time": logon_time,
                    "controller_callsign": controller_transceivers[0]["callsign"] if controller_transceivers else "",
                    "time_window": self.time_window_seconds,
                    "proximity_threshold_nm": proximity_threshold_nm,  # ✅ Dynamic per controller
                    "flight_start_time": flight_start_time,  # ✅ Pre-filter flights
                    "flight_end_time": flight_end_time,     # ✅ Pre-filter flights
                    "atc_start_time": atc_start_time,       # ✅ Pre-filter ATC
                    "atc_end_time": atc_end_time           # ✅ Pre-filter ATC
                })
                
                matches = []
                for row in result.fetchall():
                    matches.append({
                        "flight_callsign": row.flight_callsign,
                        "atc_callsign": row.atc_callsign,
                        "frequency_mhz": row.frequency_mhz,
                        "flight_time": row.flight_time,
                        "atc_time": row.atc_time,
                        "time_diff_seconds": row.time_diff_seconds,
                        "flight_lat": row.flight_lat,
                        "flight_lon": row.flight_lon,
                        "atc_lat": row.atc_lat,
                        "atc_lon": row.atc_lon
                    })
                
                self.logger.debug(f"Controller {controller_transceivers[0]['callsign'] if controller_transceivers else 'unknown'} query completed: {len(matches)} matches found with {proximity_threshold_nm}nm proximity")
                return matches
                
        except Exception as e:
            self.logger.error(f"Error in controller-specific query: {e}")
            return []
    
    async def _calculate_atc_metrics(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime, frequency_matches: List[Dict]) -> Dict[str, Any]:
        """Calculate ATC interaction metrics for a flight."""
        try:
            if not frequency_matches:
                return self._create_empty_atc_data()
            
            # Get total flight records for percentage calculation
            total_records = await self._get_flight_record_count(flight_callsign, departure, arrival, logon_time)
            if total_records == 0:
                return self._create_empty_atc_data()
            
            # Group matches by ATC callsign and calculate timing
            controller_data = {}
            for match in frequency_matches:
                atc_callsign = match["atc_callsign"]
                
                if atc_callsign not in controller_data:
                    controller_data[atc_callsign] = {
                        "callsign": atc_callsign,
                        "type": self._detect_controller_type(atc_callsign),
                        "time_minutes": 0,
                        "first_contact": match["flight_time"].isoformat() if hasattr(match["flight_time"], 'isoformat') else str(match["flight_time"]),
                        "last_contact": match["flight_time"].isoformat() if hasattr(match["flight_time"], 'isoformat') else str(match["flight_time"]),
                        "contact_count": 0
                    }
                
                # Update timing data
                controller_data[atc_callsign]["last_contact"] = match["flight_time"].isoformat() if hasattr(match["flight_time"], 'isoformat') else str(match["flight_time"])
                controller_data[atc_callsign]["contact_count"] += 1
            
            # Calculate time spent with each controller using actual VATSIM polling interval
            for controller in controller_data.values():
                # Convert polling interval from seconds to minutes for accurate time calculation
                controller["time_minutes"] = controller["contact_count"] * (self.vatsim_polling_interval_seconds / 60.0)
            
            # Calculate total controller time percentage
            total_controller_time = sum(ctrl["time_minutes"] for ctrl in controller_data.values())
            
            # Calculate percentage based on actual time, not record count
            # This represents the percentage of flight time that had ATC contact
            controller_time_percentage = min(100.0, (total_controller_time / total_records) * 100) if total_records > 0 else 0.0
            
            # Calculate airborne controller time percentage (same as total for now, can be enhanced later)
            # This represents the percentage of airborne time that had ATC contact
            airborne_controller_time_percentage = controller_time_percentage
            
            return {
                "controller_callsigns": controller_data,
                "controller_time_percentage": round(controller_time_percentage, 1),
                "airborne_controller_time_percentage": round(airborne_controller_time_percentage, 1),
                "total_controller_time_minutes": total_controller_time,
                "total_flight_records": total_records,
                "atc_contacts_detected": len(frequency_matches)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating ATC metrics: {e}")
            return self._create_empty_atc_data()
    
    async def _get_flight_record_count(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> int:
        """Get total record count for a flight."""
        try:
            query = """
                SELECT COUNT(*) as record_count
                FROM flights 
                WHERE callsign = :callsign 
                AND departure = :departure 
                AND arrival = :arrival 
                AND logon_time = :logon_time
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "callsign": flight_callsign,
                    "departure": departure,
                    "arrival": arrival,
                    "logon_time": logon_time
                })
                
                row = result.fetchone()
                return row.record_count if row else 0
                
        except Exception as e:
            self.logger.error(f"Error getting flight record count: {e}")
            return 0
    
    def _detect_controller_type(self, callsign: str) -> str:
        """Detect controller type from callsign."""
        callsign_upper = callsign.upper()
        
        if "CTR" in callsign_upper:
            return "CTR"
        elif "TMA" in callsign_upper:
            return "TMA"
        elif "TWR" in callsign_upper:
            return "TWR"
        elif "GND" in callsign_upper:
            return "GND"
        elif "DEL" in callsign_upper:
            return "DEL"
        elif "FSS" in callsign_upper:
            return "FSS"
        else:
            return "OTHER"
    
    def _create_empty_atc_data(self) -> Dict[str, Any]:
        """Create empty ATC data structure."""
        return {
            "controller_callsigns": {},
            "controller_time_percentage": 0.0,
            "airborne_controller_time_percentage": 0.0,
            "total_controller_time_minutes": 0,
            "total_flight_records": 0,
            "atc_contacts_detected": 0
        }
