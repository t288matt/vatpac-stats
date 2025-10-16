#!/usr/bin/env python3
"""
ATC Detection Service

Provides ATC interaction detection for flights by analyzing transceiver data
and calculating controller contact percentages. Implements the planned 4-step
CTE logic for accurate ATC interaction tracking.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from decimal import Decimal
from app.services.config_loader import load_frequency_owners, get_frequency_owner
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database import get_database_session
from app.utils.geographic_utils import is_within_proximity
from app.services.controller_type_detector import ControllerTypeDetector
from app.services.detection_common import compute_detection_window

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
        from app.services.detection_common import compute_detection_window
        
        # Load from environment variables with defaults and prefer centralized config
        self.time_window_seconds = time_window_seconds or int(os.getenv("FLIGHT_DETECTION_TIME_WINDOW_SECONDS", "180"))
        
        # Load VATSIM polling intervals for accurate time calculations
        # flights_polling_interval_seconds: cadence for flights + controllers
        # transceivers_polling_interval_seconds: cadence for transceivers
        self.flights_polling_interval_seconds = int(os.getenv("VATSIM_POLLING_INTERVAL", "60"))
        self.transceivers_polling_interval_seconds = int(os.getenv("VATSIM_TRANSCEIVERS_POLLING_INTERVAL", "120"))
        
        # Initialize controller type detector for dynamic proximity ranges
        self.controller_type_detector = ControllerTypeDetector()
        # Load frequency ownership mapping used as a tie-breaker
        try:
            self.frequency_owners = load_frequency_owners()
        except Exception:
            self.frequency_owners = {}
        # Frequency tolerance used elsewhere in the code (MHz)
        self.freq_tolerance_mhz = Decimal("0.005")

        # Gap tolerance multiplier for merging adjacent samples into contiguous segments
        # Increase default to tolerate API glitches
        try:
            self.enroute_gap_tolerance_multiplier = float(os.getenv("ENROUTE_GAP_TOLERANCE_MULTIPLIER", "2.5"))
        except Exception:
            self.enroute_gap_tolerance_multiplier = 2.5

        self.logger = logging.getLogger(__name__)
        self.logger.info(
            f"ATC Detection Service initialized: time_window={self.time_window_seconds}s, "
            f"flights_poll={self.flights_polling_interval_seconds}s, transceivers_poll={self.transceivers_polling_interval_seconds}s, "
            f"gap_multiplier={self.enroute_gap_tolerance_multiplier}, dynamic proximity ranges enabled"
        )
        
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
            import asyncio
            
            # Wrap the entire ATC detection process with a timeout
            return await asyncio.wait_for(
                self._detect_flight_atc_interactions_internal(flight_callsign, departure, arrival, logon_time),
                timeout=45.0  # 45 second timeout for entire ATC detection process
            )
            
        except asyncio.TimeoutError:
            self.logger.error(f"ATC detection process timed out after 45 seconds for flight {flight_callsign}")
            return self._create_empty_atc_data()
        except Exception as e:
            self.logger.error(f"Error detecting ATC interactions for flight {flight_callsign}: {e}")
            return self._create_empty_atc_data()
    
    async def _detect_flight_atc_interactions_internal(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> Dict[str, Any]:
        """Internal method for ATC detection (called with timeout wrapper)."""
        try:
            self.logger.debug(f"Detecting ATC interactions for flight {flight_callsign}")
            
            # Get flight transceivers
            flight_transceivers = await self._get_flight_transceivers(flight_callsign, departure, arrival, logon_time)
            self.logger.debug(f"Flight {flight_callsign} transceivers loaded: {len(flight_transceivers)} records")
            if flight_transceivers:
                try:
                    self.logger.debug(f"Flight sample for {flight_callsign}: {flight_transceivers[0:3]}")
                except Exception:
                    self.logger.exception("Failed to log flight transceiver sample")
            else:
                self.logger.debug(f"No transceiver data found for flight {flight_callsign}")
                return self._create_empty_atc_data()
            
            # Get ATC transceivers. Prefer loading ATC transceivers over the full
            # flight time window we just loaded so we don't miss controllers that
            # only appear later in the flight. Fall back to canonical prefilter
            # window when flight transceivers are unavailable.
            # Unified DB-only loader for ATC transceivers within the window
            from app.services.transceiver_loader import load_transceivers_window
            if flight_transceivers:
                atc_start = flight_transceivers[0]["timestamp"]
                atc_end = flight_transceivers[-1]["timestamp"]
            else:
                from app.services.detection_common import compute_prefilter_windows
                win = compute_prefilter_windows(logon_time, self.time_window_seconds)
                atc_start = win["atc_start_time"]
                atc_end = win["atc_end_time"]

            atc_transceivers = await load_transceivers_window(atc_start, atc_end, entity_type='atc')
            self.logger.debug(f"DB loader returned {len(atc_transceivers)} ATC transceivers for {flight_callsign} in window {atc_start} - {atc_end}")
            if not atc_transceivers:
                self.logger.debug(f"No ATC transceiver data found for flight {flight_callsign} after DB fallback")
                return self._create_empty_atc_data()
            
            # Find frequency matches with proximity and time constraints using SQL JOIN
            frequency_matches = await self._find_frequency_matches(flight_transceivers, atc_transceivers, departure, arrival, logon_time)
            self.logger.debug(f"Frequency matching for {flight_callsign} returned {len(frequency_matches)} matches")
            try:
                self.logger.debug(f"Frequency matches sample: {frequency_matches[:5]}")
            except Exception:
                self.logger.exception("Failed to log frequency matches sample")
            
            # Determine completion_time (canonical flight end) and pass it into metrics
            completion_time = await self._get_flight_completion_time(flight_callsign, departure, arrival, logon_time)
            if not completion_time:
                self.logger.info(f"Completion time not found for {flight_callsign}; cannot calculate ATC metrics")
                return self._create_empty_atc_data()

            # Calculate ATC interaction metrics (pass completion_time for accurate enroute counts)
            atc_data = await self._calculate_atc_metrics(flight_callsign, departure, arrival, logon_time, frequency_matches, completion_time)
            
            self.logger.debug(f"ATC detection completed for {flight_callsign}: {len(atc_data.get('controller_callsigns', {}))} controllers")
            # persist a debug artifact to disk for in-depth analysis
            try:
                import json
                debug_path = f"/tmp/atc_debug_{flight_callsign}.json"
                with open(debug_path, 'w') as df:
                    json.dump({
                        'flight_callsign': flight_callsign,
                        'flight_transceivers_count': len(flight_transceivers),
                        'atc_transceivers_count': len(atc_transceivers),
                        'frequency_matches_count': len(frequency_matches),
                        'atc_data_summary': atc_data.get('controller_callsigns')
                    }, df, default=str, indent=2)
                self.logger.debug(f"Wrote ATC debug file: {debug_path}")
            except Exception:
                self.logger.exception("Failed to write ATC debug file")
            return atc_data
            
        except Exception as e:
            self.logger.error(f"Error in internal ATC detection for flight {flight_callsign}: {e}")
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
        """Get transceiver data for a specific flight across ALL sessions using unified loader."""
        try:
            flight_start = logon_time
            completion_time = await self._get_flight_completion_time(flight_callsign, departure, arrival, logon_time)
            if not completion_time:
                self.logger.info(f"Completion time not found for {flight_callsign}; skipping flight transceiver load")
                return []
            flight_end = completion_time
            from app.services.transceiver_loader import load_transceivers_for_callsign
            return await load_transceivers_for_callsign(flight_start, flight_end, 'flight', flight_callsign)
        except Exception as e:
            self.logger.error(f"Error getting flight transceivers: {e}")
            return []
    
    async def _get_atc_transceivers_for_flight(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> List[Dict[str, Any]]:
        """Get ATC transceiver data for a specific flight's time period only."""
        try:
            # Use exact window from flight_summaries only (no fallback to current time)
            flight_start = logon_time
            completion_time = await self._get_flight_completion_time(flight_callsign, departure, arrival, logon_time)
            if not completion_time:
                self.logger.info(f"Completion time not found for {flight_callsign}; skipping ATC transceiver load")
                return []
            atc_end = completion_time
            self.logger.info(f"Loading ATC transceivers for flight {flight_callsign}: {flight_start} to {atc_end}")
            
            # Single query with flight-specific time window and geographic pre-filtering
            query = """
                SELECT t.callsign, t.frequency, t.timestamp, t.position_lat, t.position_lon
                FROM transceivers t
                WHERE t.entity_type = 'atc'
                AND t.callsign IN (  -- 🚀 Pre-filter controllers first
                    SELECT DISTINCT callsign FROM controllers 
                    WHERE facility != 0
                    AND last_updated >= :flight_logon_time  -- Only controllers active since flight came online
                )
                AND t.timestamp >= :atc_start
                AND t.timestamp <= :atc_end
                ORDER BY t.callsign, t.timestamp
            """
            
            # Single database session, single query
            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "flight_logon_time": logon_time,
                    "atc_start": flight_start,
                    "atc_end": atc_end
                })
                
                # Process results
                atc_transceivers = []
                for row in result.fetchall():
                    atc_transceivers.append({
                        "callsign": row.callsign,
                        "frequency": row.frequency,
                        "frequency_mhz": row.frequency / 1000000.0,  # Convert Hz to MHz
                        "timestamp": row.timestamp,
                        "position_lat": row.position_lat,
                        "position_lon": row.position_lon
                    })
                
                self.logger.info(f"Loaded {len(atc_transceivers)} ATC transceivers for flight {flight_callsign}")
                return atc_transceivers
                
        except Exception as e:
            self.logger.error(f"Error getting ATC transceivers for flight {flight_callsign}: {e}")
            return []
    
    async def _get_flight_completion_time(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> Optional[datetime]:
        """Get completion time for completed flights from flight_summaries table."""
        try:
            query = """
                SELECT completion_time 
                FROM flight_summaries 
                WHERE callsign = :callsign 
                AND departure = :departure 
                AND arrival = :arrival 
                AND logon_time = :logon_time
                AND completion_time IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 1
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "callsign": flight_callsign,
                    "departure": departure,
                    "arrival": arrival,
                    "logon_time": logon_time
                })
                
                row = result.fetchone()
                return row.completion_time if row else None
                
        except Exception as e:
            self.logger.warning(f"Could not get completion time for flight {flight_callsign}: {e}")
            return None
    
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

            # 3. Apply frequency ownership deduplication: ensure only one controller
            #    is associated with any single flight transceiver record
            deduped = self._apply_frequency_owner_deduplication(all_matches)
            self.logger.info(f"Frequency ownership deduplication completed: {len(deduped)} matches after deduplication")
            return deduped
            
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
                    SELECT ft.callsign as flight_callsign,
                           ft.frequency_mhz,
                           ft.timestamp as flight_time,
                           at.callsign as atc_callsign,
                           at.timestamp as atc_time,
                           at.position_lat as atc_lat,
                           at.position_lon as atc_lon,
                           ft.position_lat as flight_lat,
                           ft.position_lon as flight_lon,
                           ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) as time_diff_seconds,
                           (3440.065 * ACOS(
                                LEAST(1, GREATEST(-1,
                                    SIN(RADIANS(ft.position_lat)) * SIN(RADIANS(at.position_lat)) +
                                    COS(RADIANS(ft.position_lat)) * COS(RADIANS(at.position_lat)) *
                                    COS(RADIANS(ft.position_lon - at.position_lon))
                                ))
                           )) AS distance_nm
                    FROM time_filtered_flights ft 
                    JOIN time_filtered_atc at
                      ON ABS(ft.frequency_mhz - at.frequency_mhz) <= 0.005  -- ~5 kHz tolerance
                    WHERE ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= :time_window
                      AND (
                        (3440.065 * ACOS(
                            LEAST(1, GREATEST(-1, 
                                SIN(RADIANS(ft.position_lat)) * SIN(RADIANS(at.position_lat)) +
                                COS(RADIANS(ft.position_lat)) * COS(RADIANS(at.position_lat)) * 
                                COS(RADIANS(ft.position_lon - at.position_lon))
                            ))
                        )) <= :proximity_threshold_nm
                      )
                ),
                ranked_matches AS (
                    SELECT fm.*, ROW_NUMBER() OVER (PARTITION BY fm.flight_time, fm.atc_callsign ORDER BY fm.distance_nm ASC NULLS LAST) AS rn
                    FROM frequency_matches fm
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
                    time_diff_seconds
                FROM ranked_matches
                WHERE rn = 1
                ORDER BY flight_time, atc_time
            """
            
            # Execute with controller-specific proximity and time window pre-filtering
            async with get_database_session() as session:
                # Calculate time windows for pre-filtering.
                # Use the actual loaded transceivers bounds when available so we don't
                # accidentally limit matching to a narrow window around the flight
                # logon time (which previously caused matches later in the flight to be
                # missed). Fall back to the canonical prefilter window if transceiver
                # lists are empty.
                if flight_transceivers:
                    flight_start_time = flight_transceivers[0]["timestamp"]
                    flight_end_time = flight_transceivers[-1]["timestamp"]
                else:
                    from app.services.detection_common import build_prefilter_and_loader, compute_prefilter_windows
                    win = compute_prefilter_windows(logon_time, self.time_window_seconds)
                    pre = build_prefilter_and_loader(win["flight_start_time"], win["flight_end_time"], win["atc_start_time"], win["atc_end_time"], last_cache_fetch=None, ttl_seconds=120, default_page_size=10000)
                    flight_start_time = pre["flight_start_time"]
                    flight_end_time = pre["flight_end_time"]

                if controller_transceivers:
                    atc_start_time = controller_transceivers[0]["timestamp"]
                    atc_end_time = controller_transceivers[-1]["timestamp"]
                else:
                    # If we don't have controller transceivers (unlikely), use same prefilter
                    from app.services.detection_common import build_prefilter_and_loader, compute_prefilter_windows
                    win = compute_prefilter_windows(logon_time, self.time_window_seconds)
                    pre = build_prefilter_and_loader(win["flight_start_time"], win["flight_end_time"], win["atc_start_time"], win["atc_end_time"], last_cache_fetch=None, ttl_seconds=120, default_page_size=10000)
                    atc_start_time = pre["atc_start_time"]
                    atc_end_time = pre["atc_end_time"]
                
                result = await session.execute(text(query), {
                    "flight_callsign": flight_transceivers[0]["callsign"] if flight_transceivers else "",
                    "controller_callsign": controller_transceivers[0]["callsign"] if controller_transceivers else "",
                    "time_window": self.time_window_seconds,
                    "proximity_threshold_nm": proximity_threshold_nm,
                    "flight_start_time": flight_start_time,
                    "flight_end_time": flight_end_time,
                    "atc_start_time": atc_start_time,
                    "atc_end_time": atc_end_time
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

    def _apply_frequency_owner_deduplication(self, matches: List[Dict]) -> List[Dict]:
        """
        Deduplicate matches so that for any single flight_time + frequency_mhz only
        a single controller is kept. Preference rules:
          1) If a frequency owner exists (within tolerance) and is present -> select it
          2) Else select the match with smallest distance_nm
          3) Else select by controller type priority -> stable callsign order
        """
        if not matches:
            return []

        from collections import defaultdict
        grouped = defaultdict(list)
        for m in matches:
            key = (m.get("flight_time"), float(m.get("frequency_mhz")))
            grouped[key].append(m)

        deduped = []
        for (flight_time, frequency_mhz), group in grouped.items():
            if len(group) == 1:
                deduped.append(group[0])
                continue

            # tolerance-aware owner lookup
            try:
                owner = get_frequency_owner(Decimal(str(frequency_mhz)), self.frequency_owners, self.freq_tolerance_mhz)
            except Exception:
                owner = None

            if owner:
                # pick owner if present in group
                owner_match = next((g for g in group if g.get("atc_callsign") == owner), None)
                if owner_match:
                    deduped.append(owner_match)
                    continue

            # else pick nearest by distance
            closest = min(group, key=lambda x: x.get("distance_nm", float("inf")))
            deduped.append(closest)

        return deduped
    
    async def _calculate_atc_metrics(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime, frequency_matches: List[Dict], completion_time: datetime) -> Dict[str, Any]:
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
                # Convert transceivers polling interval from seconds to minutes for accurate time calculation
                controller["time_minutes"] = controller["contact_count"] * (self.transceivers_polling_interval_seconds / 60.0)
            
            # Calculate total controller time percentage
            total_controller_time = sum(ctrl["time_minutes"] for ctrl in controller_data.values())
            
            # Calculate percentage based on actual time, not record count
            # This represents the percentage of flight time that had ATC contact
            controller_time_percentage = min(100.0, (total_controller_time / total_records) * 100) if total_records > 0 else 0.0
            
            # Calculate airborne controller time percentage using transceiver heights (>1500 ft)
            # Use transceiver height_msl (meters) converted to feet for the threshold
            AIRBORNE_ALT_FT = 1500
            AIRBORNE_ALT_M = AIRBORNE_ALT_FT / 3.28084

            # Calculate total enroute (airborne) time using preferred time-series source
            total_enroute_time_minutes = await self._get_airborne_time_from_flights(
                flight_callsign, departure, arrival, logon_time, completion_time
            )

            # Count airborne controller contacts using altitude at contact times
            airborne_contact_count = await self._count_airborne_controller_contacts(
                flight_callsign, frequency_matches, completion_time
            )

            # Convert contact count to minutes using transceivers polling interval
            poll_min = (self.transceivers_polling_interval_seconds / 60.0)
            total_airborne_controller_time_minutes = airborne_contact_count * poll_min

            if total_enroute_time_minutes <= 0:
                airborne_controller_time_percentage = 0.0
            else:
                airborne_controller_time_percentage = min(100.0, (total_airborne_controller_time_minutes / total_enroute_time_minutes) * 100.0)
            
            # Convert the controller_data dictionary to an array of values for consistent structure
            controller_array = list(controller_data.values()) if controller_data else []
            
            return {
                "controller_callsigns": controller_array,  # Store as array instead of dictionary
                "controller_time_percentage": round(controller_time_percentage, 1),
                "airborne_controller_time_percentage": round(airborne_controller_time_percentage, 1),
                "total_controller_time_minutes": total_controller_time,
                "total_flight_records": total_records,
                "interactions_detected": len(frequency_matches)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating ATC metrics: {e}")
            return self._create_empty_atc_data()
    
    async def _get_flight_record_count(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> int:
        """Get total flight record count from flight-based sources only.
        
        Preference order:
        1. `flights` (live records)
        2. `flights_archive` (time-series snapshots)
        """
        try:
            # Determine the exact end time from flight_summaries; if absent, no records (ongoing not supported here)
            completion_time = await self._get_flight_completion_time(flight_callsign, departure, arrival, logon_time)
            if not completion_time:
                return 0

            # 1) Try flights table first
            async with get_database_session() as session:
                q = text("""
                    SELECT COUNT(*) as record_count
                    FROM flights
                    WHERE callsign = :callsign
                      AND last_updated >= :start
                      AND last_updated <= :end
                      AND altitude IS NOT NULL
                """)
                res = await session.execute(q, {
                    "callsign": flight_callsign,
                    "start": logon_time,
                    "end": completion_time
                })
                row = res.fetchone()
                self.logger.info(f"_get_flight_record_count: flights table returned {row.record_count if row else 0} records for {flight_callsign}")
                if row and row.record_count > 0:
                    return row.record_count

            # 2) Fallback: flights_archive
            async with get_database_session() as session:
                q = text("""
                    SELECT COUNT(*) as record_count
                    FROM flights_archive
                    WHERE callsign = :callsign
                      AND last_updated >= :start
                      AND last_updated <= :end
                      AND altitude IS NOT NULL
                """)
                res = await session.execute(q, {
                    "callsign": flight_callsign,
                    "start": logon_time,
                    "end": completion_time
                })
                row = res.fetchone()
                if row and row.record_count > 0:
                    return row.record_count

            # If no records found in either table, return 0
            self.logger.warning(f"No flight records found in flights or flights_archive for {flight_callsign}")
            return 0
                
        except Exception as e:
            self.logger.error(f"Error getting flight record count: {e}")
            return 0

    async def _get_airborne_time_from_flights(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime, completion_time: datetime) -> float:
        """Get total airborne time (minutes) using flight-based time-series sources.

        Preference order:
        1. `flights` (live records)
        2. `flights_archive` (time-series snapshots)
        """
        try:
            # 1) Attempt flights (live records) first
            async with get_database_session() as session:
                q = text("""
                    SELECT last_updated AS ts
                    FROM flights
                    WHERE callsign = :callsign
                      AND last_updated >= :start
                      AND last_updated <= :end
                      AND altitude IS NOT NULL
                      AND altitude > :alt_threshold
                    ORDER BY last_updated
                """)
                res = await session.execute(q, {
                    "callsign": flight_callsign,
                    "start": logon_time,
                    "end": completion_time,
                    "alt_threshold": 1500
                })
                rows = res.fetchall()
                logger.debug(f"_get_airborne_time_from_flights: flights rows={len(rows)} for {flight_callsign} [{logon_time}..{completion_time}]")

            def _sum_from_timestamps(ts_list, poll_interval, multiplier):
                if not ts_list:
                    return 0.0
                gap_tolerance = poll_interval * multiplier
                total = 0.0
                seg_start = ts_list[0]
                prev = ts_list[0]
                for t in ts_list[1:]:
                    d = (t - prev).total_seconds()
                    if d <= gap_tolerance:
                        prev = t
                        continue
                    total += max((prev - seg_start).total_seconds(), poll_interval)
                    seg_start = t
                    prev = t
                total += max((prev - seg_start).total_seconds(), poll_interval)
                return total

            if rows:
                # flights table provided timestamped records
                timestamps = [r.ts for r in rows]
                secs = _sum_from_timestamps(timestamps, self.flights_polling_interval_seconds, self.enroute_gap_tolerance_multiplier)
                minutes = round(secs / 60.0)
                return float(minutes)

            # 2) Fallback: flights_archive (time-series snapshots)
            async with get_database_session() as session:
                q = text("""
                    SELECT last_updated AS ts
                    FROM flights_archive
                    WHERE callsign = :callsign
                      AND last_updated >= :start
                      AND last_updated <= :end
                      AND altitude IS NOT NULL
                      AND altitude > :alt_threshold
                    ORDER BY last_updated
                """)
                res = await session.execute(q, {
                    "callsign": flight_callsign,
                    "start": logon_time,
                    "end": completion_time,
                    "alt_threshold": 1500
                })
                rows = res.fetchall()
                logger.debug(f"_get_airborne_time_from_flights: flights_archive rows={len(rows)} for {flight_callsign} [{logon_time}..{completion_time}]")

            if rows:
                timestamps = [r.ts for r in rows]
                secs = _sum_from_timestamps(timestamps, self.flights_polling_interval_seconds, self.enroute_gap_tolerance_multiplier)
                minutes = round(secs / 60.0)
                return float(minutes)

            # If no data found in flight-based sources, return 0
            self.logger.warning(f"No airborne data found in flights or flights_archive for {flight_callsign}")
            return 0.0
        except Exception as e:
            self.logger.error(f"Error in _get_airborne_time_from_flights: {e}")
            return 0.0

    async def _count_airborne_controller_contacts(self, flight_callsign: str, frequency_matches: List[Dict], completion_time: datetime) -> int:
        """Count controller contacts that occurred while aircraft was airborne using flight-based altitude data.
        Returns count of matches that occurred while aircraft altitude > 1500ft.
        """
        try:
            count = 0
            async with get_database_session() as session:
                for match in frequency_matches:
                    match_time = match.get("flight_time")
                    alt_ft = None
                    # 1) Prefer flights (live snapshot) at or before match_time
                    q_live = text("""
                        SELECT altitude FROM flights
                        WHERE callsign = :callsign
                          AND last_updated <= :t
                          AND altitude IS NOT NULL
                        ORDER BY last_updated DESC
                        LIMIT 1
                    """)
                    res_live = await session.execute(q_live, {"callsign": flight_callsign, "t": match_time})
                    r_live = res_live.fetchone()
                    if r_live:
                        alt_ft = r_live[0]
                    else:
                        # 2) Fallback: flights_archive
                        q_archive = text("""
                            SELECT altitude FROM flights_archive
                            WHERE callsign = :callsign
                              AND last_updated <= :t
                              AND altitude IS NOT NULL
                            ORDER BY last_updated DESC
                            LIMIT 1
                        """)
                        res_arc = await session.execute(q_archive, {"callsign": flight_callsign, "t": match_time})
                        r_arc = res_arc.fetchone()
                        if r_arc:
                            alt_ft = r_arc[0]
                    
                    # Get groundspeed at contact time for airborne detection
                    from app.utils.airborne_detection import is_airborne
                    
                    # Query for groundspeed at match time
                    q_speed = text("""
                        SELECT groundspeed FROM flights
                        WHERE callsign = :callsign
                          AND last_updated <= :t
                          AND groundspeed IS NOT NULL
                        ORDER BY last_updated DESC
                        LIMIT 1
                    """)
                    res_speed = await session.execute(q_speed, {"callsign": flight_callsign, "t": match_time})
                    r_speed = res_speed.fetchone()
                    
                    if not r_speed:
                        # Fallback to archive
                        q_speed_arc = text("""
                            SELECT groundspeed FROM flights_archive
                            WHERE callsign = :callsign
                              AND last_updated <= :t
                              AND groundspeed IS NOT NULL
                            ORDER BY last_updated DESC
                            LIMIT 1
                        """)
                        res_speed_arc = await session.execute(q_speed_arc, {"callsign": flight_callsign, "t": match_time})
                        r_speed_arc = res_speed_arc.fetchone()
                        groundspeed = r_speed_arc[0] if r_speed_arc else None
                    else:
                        groundspeed = r_speed[0]
                    
                    # Only count if aircraft was airborne (≥60 knots) at contact time
                    if is_airborne(groundspeed):
                        # check controller type
                        atc_callsign = match.get("atc_callsign")
                        controller_type = self._detect_controller_type(atc_callsign)
                        if controller_type in ["TMA", "CTR", "FSS"]:
                            count += 1
            return count
        except Exception as e:
            self.logger.error(f"Error in _count_airborne_controller_contacts: {e}")
            return 0

    async def recalculate_airborne_for_summaries(self, days: int = 30, batch_size: int = 50, timeout_seconds: float = 30.0):
        """Recalculate airborne percentages and enroute time for recent flight summaries.

        - Select summaries in the last `days` where airborne percentage is 0 or enroute time is null
        - Process in batches and update `flight_summaries`
        """
        try:
            from types import SimpleNamespace
            # Compute cutoff timestamp in Python to avoid INTERVAL parameterization issues
            from datetime import datetime, timezone, timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
            select_q = text("""
                SELECT id, callsign, departure, arrival, logon_time, completion_time
                FROM flight_summaries
                WHERE completion_time >= :cutoff
                AND (airborne_controller_time_percentage = 0.0 OR total_enroute_time_minutes IS NULL)
                ORDER BY completion_time DESC
                LIMIT :limit
            """)

            # Use a simple batching loop
            processed = 0
            async with get_database_session() as session:
                # Fetch affected summaries with cutoff timestamp and limit
                result = await session.execute(select_q, {"cutoff": cutoff, "limit": batch_size})
                rows = result.fetchall()

            # If none, nothing to do
            if not rows:
                self.logger.info("No flight summaries require airborne recalculation")
                return 0

            for row in rows:
                sid = row.id
                callsign = row.callsign
                departure = row.departure
                arrival = row.arrival
                logon_time = row.logon_time
                completion_time = row.completion_time

                try:
                    # Re-run ATC detection for this flight (with timeout protection)
                    atc_data = await self.detect_flight_atc_interactions_with_timeout(callsign, departure, arrival, logon_time, timeout_seconds=timeout_seconds)

                    # Compute total enroute time from flights/archive
                    total_enroute = await self._get_airborne_time_from_flights(callsign, departure, arrival, logon_time, completion_time)

                    # Update flight_summaries row
                    async with get_database_session() as session:
                        await session.execute(text("""
                            UPDATE flight_summaries
                            SET airborne_controller_time_percentage = :pct,
                                total_enroute_time_minutes = :enroute,
                                updated_at = NOW()
                            WHERE id = :id
                        """), {"pct": float(atc_data.get("airborne_controller_time_percentage", 0.0)), "enroute": int(total_enroute), "id": sid})
                        await session.commit()

                    processed += 1
                    self.logger.info(f"Recalculated airborne for summary id={sid} callsign={callsign}")

                except Exception as e:
                    self.logger.error(f"Failed to recalc summary id={sid} callsign={callsign}: {e}")
                    continue

            return processed

        except Exception as e:
            self.logger.error(f"Error in recalculate_airborne_for_summaries: {e}")
            return 0
    
    def _detect_controller_type(self, callsign: str) -> str:
        """Detect controller type from callsign."""
        callsign_upper = callsign.upper()
        
        if "CTR" in callsign_upper:
            return "CTR"
        elif "APP" in callsign_upper or "DEP" in callsign_upper or "TMA" in callsign_upper:
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
            "controller_callsigns": [],  # Changed from {} to [] to ensure consistent array structure
            "controller_time_percentage": 0.0,
            "airborne_controller_time_percentage": 0.0,
            "total_controller_time_minutes": 0,
            "total_flight_records": 0,
            "interactions_detected": 0
        }
