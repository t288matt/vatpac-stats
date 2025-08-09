#!/usr/bin/env python3
"""
VATSIM Data Collection System - Main Application

This module provides the FastAPI application with REST API endpoints for the VATSIM
data collection and analysis system. It handles real-time data ingestion, API requests,
and serves the web dashboard.

INPUTS:
- Environment variables for configuration
- VATSIM API data (via background service)
- Database queries and updates
- HTTP requests from clients

OUTPUTS:
- REST API responses (JSON)
- Real-time data updates
- Background data ingestion to database

ENDPOINTS:
- /api/status - System health and status
- /api/atc-positions - ATC position data
- /api/flights - Flight data
# REMOVED: /api/traffic/* - Traffic analysis endpoints

DEPENDENCIES:
- PostgreSQL database
- In-memory cache
- VATSIM API
- Background data ingestion service
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_, desc, text

# Config imports removed as they were unused
from .database import get_db, init_db, get_database_info, SessionLocal
from .models import Controller, Flight, Transceiver, Airports
from .utils.logging import get_logger_for_module
from .utils.rating_utils import get_all_ratings, validate_rating
from .services.vatsim_service import get_vatsim_service
from .services.data_service import get_data_service
# REMOVED: Traffic Analysis Service - Phase 2
from .services.cache_service import get_cache_service

from .services.resource_manager import get_resource_manager
from .utils.airport_utils import get_airports_by_region, get_region_statistics, get_airport_coordinates
from .utils.error_monitoring import start_error_monitoring
from .api.error_monitoring import router as error_monitoring_router
from .utils.error_handling import handle_service_errors, log_operation, create_error_handler
from .utils.exceptions import APIError, DatabaseError, CacheError
from .utils.health_monitor import health_monitor
from .utils.schema_validator import ensure_database_schema
from .filters.flight_filter import FlightFilter
from .utils.error_manager import get_error_analytics, get_circuit_breaker_status
from .services.database_service import get_database_service

# Import new service management components
from .services.service_manager import ServiceManager
from .services.event_bus import get_event_bus, publish_event
from .services.interfaces.event_bus_interface import EventType

# Import Phase 3 services
from .services.monitoring_service import get_monitoring_service
from .services.performance_monitor import get_performance_monitor
from .services.frequency_matching_service import FrequencyMatchingService, FrequencyMatch, FrequencyMatchSummary, CommunicationPattern

# Configure logging
logger = get_logger_for_module(__name__)

# Initialize centralized error handler
error_handler = create_error_handler("main_api")

# Global service manager
service_manager: Optional[ServiceManager] = None

# Background task for data ingestion
background_task = None

# Initialize frequency matching service
frequency_matching_service = FrequencyMatchingService()

@handle_service_errors
@log_operation("background_data_ingestion")
async def background_data_ingestion():
    """Background task for continuous data ingestion"""
    import os
    global background_task
    
    # Get polling interval from environment variable
    # Note: The 60s fallback is only used if VATSIM_POLLING_INTERVAL env var is not set
    # The actual value should be configured in docker-compose.yml (currently set to 10s)
    polling_interval = int(os.getenv('VATSIM_POLLING_INTERVAL', 60))
    
    # Log the configured interval
    logger.info(f"Main background data ingestion configured with polling interval: {polling_interval}s")
    
    while True:
        try:
            data_service = get_data_service()
            await data_service.start_data_ingestion()
            # Sleep interval is now handled inside the data service
        except Exception as e:
            logger.error(f"Background data ingestion error: {e}")
            await asyncio.sleep(polling_interval)  # Fallback sleep based on environment variable

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with new service management"""
    global service_manager, background_task
    
    try:
        # Initialize database
        init_db()
        
        # Validate and ensure database schema is correct
        db = SessionLocal()
        try:
            if not ensure_database_schema(db):
                logger.error("Database schema validation failed. Application may not function correctly.")
                # Continue anyway - the app might still work with some features disabled
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
        finally:
            db.close()
        
        # Initialize service manager
        service_manager = ServiceManager()
        
        # Create a database session for service initialization
        service_db = SessionLocal()
        
        # Register services with the service manager
        services = {
            'cache_service': await get_cache_service(),
            'vatsim_service': get_vatsim_service(),
            'data_service': get_data_service(),
            # REMOVED: Traffic Analysis Service - Phase 2

            'resource_manager': get_resource_manager(),
            # Phase 3 services
            'monitoring_service': get_monitoring_service(),
            'performance_monitor': get_performance_monitor(),
        }
        
        # Close the service database session
        service_db.close()
        
        await service_manager.register_services(services)
        
        # Start all services
        start_results = await service_manager.start_all_services()
        logger.info(f"Service startup results: {start_results}")
        
        # Initialize cache service
        cache_service = await get_cache_service()
        
        # Initialize resource manager
        resource_manager = get_resource_manager()
        
        # Start error monitoring
        await start_error_monitoring()
        
        # Start background task
        background_task = asyncio.create_task(background_data_ingestion())
        
        # Publish service started event
        try:
            event_bus = await get_event_bus()
            await publish_event(EventType.SERVICE_STARTED, {
                "service": "main_application",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.warning(f"Could not publish service started event: {e}")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise
    finally:
        # Cleanup
        if 'background_task' in globals() and background_task:
            background_task.cancel()
            try:
                await background_task
            except asyncio.CancelledError:
                pass
        
        # Graceful shutdown of services
        if service_manager:
            await service_manager.graceful_shutdown()
        
        # Publish service stopped event
        try:
            event_bus = await get_event_bus()
            await publish_event(EventType.SERVICE_STOPPED, {
                "service": "main_application",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Error publishing service stopped event: {e}")

# Create FastAPI app
app = FastAPI(
    title="VATSIM Data Collector",
    description="Real-time VATSIM data collection system",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware with explicit configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include error monitoring router
app.include_router(error_monitoring_router)

@app.get("/api/status")
@handle_service_errors
@log_operation("get_status")
async def get_status(db: Session = Depends(get_db)):
    """Get system status with caching and improved error handling"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_stats = await cache_service.get_network_stats_cache()
        
        if cached_stats:
            logger.info("Returning cached network stats")
            return cached_stats
        
        # If not cached, get from database with improved error handling
        try:
            atc_positions_count = db.query(Controller).filter(Controller.status == "online").count()
        except Exception as e:
            logger.error(f"Error querying ATC positions: {e}")
            atc_positions_count = 0
        
        try:
            flights_count = db.query(Flight).count()
        except Exception as e:
            logger.error(f"Error querying flights: {e}")
            # Check if the issue is with the controller_id column
            try:
                # Try a simpler query without relationships
                flights_count = db.query(Flight.id).count()
            except Exception as e2:
                logger.error(f"Error with simplified flight query: {e2}")
                flights_count = 0
        
        try:
            airports_count = db.query(Airports).count()
        except Exception as e:
            logger.error(f"Error querying airports: {e}")
            airports_count = 0
        
        # DISABLED: Traffic Analysis Service Removal - Phase 1
        # try:
        #     movements_count = db.query(TrafficMovement).filter(
        #         TrafficMovement.timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)
        #     ).count()
        # except Exception as e:
        #     logger.error(f"Error querying movements: {e}")
        #     movements_count = 0
        movements_count = 0  # Temporarily disabled
        
        # Check if database is empty and provide diagnostic info
        total_flights = db.query(Flight).count()
        total_controllers = db.query(Controller).count()
        
        if total_flights == 0 and total_controllers == 0:
            logger.warning("Database appears to be empty - data ingestion may not be working")
            stats = {
                "status": "operational",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "atc_positions_count": atc_positions_count,
                "flights_count": flights_count,
                "airports_count": airports_count,
                "movements_count": movements_count,
                "data_freshness": "no_data",
                "cache_status": "enabled",
                "diagnostic": {
                    "total_flights_in_db": total_flights,
                    "total_controllers_in_db": total_controllers,
                    "data_ingestion_status": "no_data_detected",
                    "recommendation": "check_data_ingestion_service"
                }
            }
        else:
            stats = {
                "status": "operational",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "atc_positions_count": atc_positions_count,
                "flights_count": flights_count,
                "airports_count": airports_count,
                "movements_count": movements_count,
                "data_freshness": "real-time",
                "cache_status": "enabled",
                "diagnostic": {
                    "total_flights_in_db": total_flights,
                    "total_controllers_in_db": total_controllers,
                    "data_ingestion_status": "data_present"
                }
            }
        
        # Cache the result
        await cache_service.set_network_stats_cache(stats)
        
        return stats
        
    except Exception as e:
        logger.error(f"Unexpected error in get_status: {e}")
        # Return a basic status even if there are errors
        return {
            "status": "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "atc_positions_count": 0,
            "flights_count": 0,
            "airports_count": 0,
            "movements_count": 0,
            "data_freshness": "unknown",
            "cache_status": "disabled",
            "error": str(e),
            "diagnostic": {
                "error_type": type(e).__name__,
                "recommendation": "check_application_logs"
            }
        }

# Add new service management endpoints
@app.get("/api/services/status")
@handle_service_errors
@log_operation("get_services_status")
async def get_services_status():
    """Get status of all services"""
    global service_manager
    if service_manager is None:
        return {
            "status": "error",
            "message": "Service manager not initialized",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    try:
        return {
            "manager_status": service_manager.get_manager_status(),
            "services_status": service_manager.get_all_service_status(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting services status: {e}")
        return {
            "status": "error",
            "message": f"Error getting services status: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/api/services/{service_name}/status")
@handle_service_errors
@log_operation("get_service_status")
async def get_service_status(service_name: str):
    """Get status of a specific service"""
    global service_manager
    if service_manager is None:
        raise HTTPException(status_code=503, detail="Service manager not initialized")
    
    try:
        status = service_manager.get_service_status(service_name)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service status for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")

@app.post("/api/services/{service_name}/restart")
@handle_service_errors
@log_operation("restart_service")
async def restart_service(service_name: str):
    """Restart a specific service"""
    global service_manager
    if service_manager is None:
        raise HTTPException(status_code=503, detail="Service manager not initialized")
    
    try:
        success = await service_manager.restart_service(service_name)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to restart service {service_name}")
        
        return {
            "status": "success",
            "message": f"Service {service_name} restarted successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error restarting service: {str(e)}")

@app.get("/api/services/health")
@handle_service_errors
@log_operation("get_services_health")
async def get_services_health():
    """Get health status of all services"""
    global service_manager
    if service_manager is None:
        return {
            "status": "error",
            "message": "Service manager not initialized",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    try:
        return await service_manager.health_check_all()
    except Exception as e:
        logger.error(f"Error getting services health: {e}")
        return {
            "status": "error",
            "message": f"Error getting services health: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/api/events/status")
@handle_service_errors
@log_operation("get_events_status")
async def get_events_status():
    """Get event bus status and statistics"""
    try:
        event_bus = await get_event_bus()
        return {
            "event_bus_status": await event_bus.health_check(),
            "statistics": event_bus.get_statistics(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting events status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/api/network/status")
@handle_service_errors
@log_operation("get_network_status")
async def get_network_status(db: Session = Depends(get_db)):
    """Get network status with caching"""
    # Try to get from cache first
    cache_service = await get_cache_service()
    cached_data = await cache_service.get_cached_data('network:detailed_status')
    
    if cached_data:
        return cached_data
    
    # Get network data from database
    atc_count = db.query(Controller).filter(Controller.status == "online").count()
    flight_count = db.query(Flight).count()
    # Sectors removed - VATSIM API v3 doesn't provide sectors data
    
    status = {
        "total_controllers": atc_count,
        "total_flights": flight_count,
        "last_update": datetime.now(timezone.utc).isoformat()
    }
    
    # Cache the result
    await cache_service.set_cached_data('network:detailed_status', status, 60)
    
    return status

@app.get("/api/atc-positions")
@handle_service_errors
@log_operation("get_atc_positions")
async def get_atc_positions(db: Session = Depends(get_db)):
    """Get active ATC positions with caching"""
    # Try to get from cache first
    cache_service = await get_cache_service()
    cached_data = await cache_service.get_cached_data('atc_positions:active')
    
    if cached_data:
        return {
            **cached_data,
            "cached": True
        }
    
    # Get from database if not cached
    atc_positions = db.query(Controller).all()
    
    atc_positions_data = []
    for atc_position in atc_positions:
        # Validate rating with error handling
        rating_validation = validate_rating(atc_position.controller_rating) if atc_position.controller_rating else {"is_valid": False, "rating_name": None, "rating_level": None, "error": "No rating provided"}
        
        atc_positions_data.append({
            "id": atc_position.id,
            "callsign": atc_position.callsign,
            "facility": atc_position.facility,
            "position": atc_position.position,
            "status": atc_position.status,
            "frequency": atc_position.frequency,
            "controller_id": atc_position.controller_id,
            "controller_name": atc_position.controller_name,
            "controller_rating": atc_position.controller_rating,
            "controller_rating_name": rating_validation.get("rating_name"),
            "controller_rating_level": rating_validation.get("rating_level"),
            "rating_validation": {
                "is_valid": rating_validation.get("is_valid", False),
                "error": rating_validation.get("error")
            },
            "last_seen": atc_position.last_seen.isoformat() if atc_position.last_seen else None,
            "workload_score": atc_position.workload_score
        })
    
    # Count online positions
    online_count = len([pos for pos in atc_positions_data if pos["status"] == "online"])
    
    result = {
        "positions": atc_positions_data,
        "total": len(atc_positions_data),
        "online": online_count,
        "cached": False
    }
    
    # Cache the result for 30 seconds
    await cache_service.set_cached_data('atc_positions:active', result, 30)
    
    return result

@app.get("/api/atc-positions/by-controller-id")
@handle_service_errors
@log_operation("get_atc_positions_by_controller_id")
async def get_atc_positions_by_controller_id(db: Session = Depends(get_db)):
    """Get ATC positions grouped by controller ID (showing multiple positions per controller)"""
    # Try to get from cache first
    cache_service = await get_cache_service()
    cached_data = await cache_service.get_cached_data('atc_positions:by_controller_id')
    
    if cached_data:
        return {
            **cached_data,
            "cached": True
        }
    
    # Get all ATC positions
    atc_positions = db.query(Controller).all()
    
    # Group by controller ID
    atc_positions_by_controller_id = {}
    for atc_position in atc_positions:
        controller_id = atc_position.controller_id or "unknown"
        if controller_id not in atc_positions_by_controller_id:
            # Validate rating with error handling
            rating_validation = validate_rating(atc_position.controller_rating) if atc_position.controller_rating else {"is_valid": False, "rating_name": None, "rating_level": None, "error": "No rating provided"}
            
            atc_positions_by_controller_id[controller_id] = {
                "controller_id": controller_id,
                "controller_name": atc_position.controller_name,
                "controller_rating": atc_position.controller_rating,
                "controller_rating_name": rating_validation.get("rating_name"),
                "controller_rating_level": rating_validation.get("rating_level"),
                "rating_validation": {
                    "is_valid": rating_validation.get("is_valid", False),
                    "error": rating_validation.get("error")
                },
                "positions": [],
                "total_positions": 0,
                "facilities": set(),
                "frequencies": []
            }
        
        atc_positions_by_controller_id[controller_id]["positions"].append({
            "callsign": atc_position.callsign,
            "facility": atc_position.facility,
            "position": atc_position.position,
            "frequency": atc_position.frequency,
            "status": atc_position.status,
            "last_seen": atc_position.last_seen.isoformat() if atc_position.last_seen else None,
            "workload_score": atc_position.workload_score
        })
        atc_positions_by_controller_id[controller_id]["total_positions"] += 1
        atc_positions_by_controller_id[controller_id]["facilities"].add(atc_position.facility)
        if atc_position.frequency:
            atc_positions_by_controller_id[controller_id]["frequencies"].append(atc_position.frequency)
    
    # Convert sets to lists for JSON serialization
    for controller_id, data in atc_positions_by_controller_id.items():
        data["facilities"] = list(data["facilities"])
    
    result = {
        "atc_positions_by_controller_id": list(atc_positions_by_controller_id.values()),
        "total_unique_controllers": len(atc_positions_by_controller_id),
        "total_positions": sum(data["total_positions"] for data in atc_positions_by_controller_id.values())
    }
    
    # Cache the result for 30 seconds
    await cache_service.set_cached_data('atc_positions:by_controller_id', result, 30)
    
    return result

@app.get("/api/vatsim/ratings")
@handle_service_errors
@log_operation("get_vatsim_ratings")
async def get_vatsim_ratings():
    """Get all available VATSIM controller ratings"""
    # Try to get from cache first (static data, long cache)
    cache_service = await get_cache_service()
    cached_data = await cache_service.get_cached_data('vatsim:ratings')
    
    if cached_data:
        return {
            **cached_data,
            "cached": True
        }
    
    ratings = get_all_ratings()
    result = {
        "ratings": ratings,
        "total_ratings": len(ratings),
        "description": "VATSIM controller ratings from 1-15",
        "valid_range": "1-15",
        "known_ratings": [1, 2, 3, 4, 5, 8, 10, 11],
        "unknown_ratings": [6, 7, 9, 12, 13, 14, 15]
    }
    
    # Cache the result for 1 hour (static data)
    await cache_service.set_cached_data('vatsim:ratings', result, 3600)
    
    return result

@app.get("/api/flights")
@handle_service_errors
@log_operation("get_flights")
async def get_flights(db: Session = Depends(get_db)):
    """Get active flights with caching"""
    # Try to get from cache first
    cache_service = await get_cache_service()
    cached_flights = await cache_service.get_flights_cache()
    
    if cached_flights:
        logger.info("Returning cached flights data")
        # Count all flights (no status column exists)
        active_count = len(cached_flights['data'])
        return {
            "flights": cached_flights['data'],
            "total": len(cached_flights['data']),
            "active": active_count,
            "cached": True
        }
    
    # If not cached, get from database using direct SQL to avoid session isolation issues
    # Limit to recent flights to avoid performance issues
    result = db.execute(text("SELECT id, callsign, aircraft_type, departure, arrival, route, altitude, heading, groundspeed, cruise_tas, transponder, position_lat, position_lng, latitude, longitude, cid, name, pilot_rating, military_rating, server, last_updated FROM flights ORDER BY last_updated DESC LIMIT 1000"))
    flights_data = []
    
    for row in result:
        flight_data = {
            "id": row.id,
            "callsign": row.callsign,
            "aircraft_type": row.aircraft_type,
            "departure": row.departure,
            "arrival": row.arrival,
            "route": row.route,
            "altitude": row.altitude,
            "heading": row.heading,
            "groundspeed": row.groundspeed,
            "cruise_tas": row.cruise_tas,
            "squawk": row.transponder,
            "position_lat": row.position_lat,
            "position_lng": row.position_lng,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "cid": row.cid,
            "name": row.name,
            "pilot_rating": row.pilot_rating,
            "military_rating": row.military_rating,
            "server": row.server,
            "last_updated": row.last_updated.isoformat() if row.last_updated else None
        }
        
        flights_data.append(flight_data)
    
    # Cache the result
    await cache_service.set_flights_cache(flights_data)
    
    # Count all flights (no status column exists)
    active_count = len(flights_data)
    
    return {
        "flights": flights_data,
        "total": len(flights_data),
        "active": active_count,
        "cached": False
    }

@app.get("/api/flights/{callsign}/track")
@handle_service_errors
@log_operation("get_flight_track")
async def get_flight_track(
    callsign: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get complete flight track with all position updates"""
    try:
        # Build query for flight positions
        query = db.query(Flight).filter(Flight.callsign == callsign)
        
        if start_time:
            query = query.filter(Flight.last_updated >= start_time)
        if end_time:
            query = query.filter(Flight.last_updated <= end_time)
        
        # Get all position updates ordered by time
        flight_positions = query.order_by(Flight.last_updated).all()
        
        return {
            "callsign": callsign,
            "positions": [
                {
                    "timestamp": pos.last_updated.isoformat(),
                    "latitude": pos.position_lat,
                    "longitude": pos.position_lng,
                    "altitude": pos.altitude,
                    "heading": pos.heading,
                    "groundspeed": pos.groundspeed,
                    "cruise_tas": pos.cruise_tas,
                    "squawk": pos.transponder
                } for pos in flight_positions
            ],
            "total_positions": len(flight_positions),
            "first_position": flight_positions[0].last_updated.isoformat() if flight_positions else None,
            "last_position": flight_positions[-1].last_updated.isoformat() if flight_positions else None
        }
    except Exception as e:
        logger.error(f"Error getting flight track: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving flight track")

@app.get("/api/flights/{callsign}/stats")
@handle_service_errors
@log_operation("get_flight_stats")
async def get_flight_stats(callsign: str, db: Session = Depends(get_db)):
    """Get flight statistics and summary"""
    try:
        # Get all positions for this flight
        positions = db.query(Flight).filter(
            Flight.callsign == callsign
        ).order_by(Flight.last_updated).all()
        
        if not positions:
            raise HTTPException(status_code=404, detail="Flight not found")
        
        # Calculate statistics
        first_pos = positions[0]
        last_pos = positions[-1]
        
        # Calculate flight duration
        duration_minutes = int((last_pos.last_updated - first_pos.last_updated).total_seconds() / 60)
        
        # Find max altitude and groundspeed
        max_altitude = max(pos.altitude or 0 for pos in positions)
        max_groundspeed = max(pos.groundspeed or 0 for pos in positions)
        
        return {
            "callsign": callsign,
            "total_positions": len(positions),
            "duration_minutes": duration_minutes,
            "first_seen": first_pos.last_updated.isoformat(),
            "last_seen": last_pos.last_updated.isoformat(),
            "departure": first_pos.departure,
            "arrival": first_pos.arrival,
            "aircraft_type": first_pos.aircraft_type,
            "max_altitude": max_altitude,
            "max_groundspeed": max_groundspeed,
            "route": first_pos.route
        }
    except Exception as e:
        logger.error(f"Error getting flight stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving flight statistics")

# DISABLED: Traffic Analysis Service Removal - Phase 1
# @app.get("/api/traffic/movements/{airport_icao}")
# @handle_service_errors
# @log_operation("get_airport_movements")
# async def get_airport_movements(
#     airport_icao: str, 
#     hours: int = 24,
#     db: Session = Depends(get_db)
# ):
#     """Get traffic movements for specific airport with caching"""
#     # Try to get from cache first
#     cache_service = await get_cache_service()
#     cached_movements = await cache_service.get_traffic_movements_cache(airport_icao)
#     
#     if cached_movements:
#         logger.info(f"Returning cached movements for {airport_icao}")
#         return {"movements": cached_movements, "cached": True}
#     
#     # If not cached, get from database
#     cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
#     
#     movements = db.query(TrafficMovement).filter(
#         and_(
#             TrafficMovement.airport_icao == airport_icao.upper(),
#             TrafficMovement.timestamp >= cutoff_time
#         )
#     ).order_by(desc(TrafficMovement.timestamp)).all()
#     
#     movements_data = []
#     for movement in movements:
#         movements_data.append({
#             "id": movement.id,
#             "airport_icao": movement.airport_icao,
#             "flight_callsign": movement.flight_callsign,
#             "movement_type": movement.movement_type,
#             "timestamp": movement.timestamp.isoformat(),
#             "confidence": movement.confidence,
#             "altitude": movement.altitude
#         })
#     
#     # Cache the result
#     await cache_service.set_traffic_movements_cache(airport_icao, movements_data)
#     
#     return {"movements": movements_data, "cached": False}

# DISABLED: Traffic Analysis Service Removal - Phase 1
# @app.get("/api/traffic/summary")
# @handle_service_errors
# @log_operation("get_traffic_summary")
# async def get_traffic_summary(
#     hours: int = 24,
#     db: Session = Depends(get_db)
# ):
#     """Get traffic summary for all airports with caching"""
#     # Try to get from cache first
#     cache_service = await get_cache_service()
#     cache_key = f'traffic:summary:all:{hours}h'
#     cached_summary = await cache_service.get_cached_data(cache_key)
#     
#     if cached_summary:
#         return cached_summary
#     
#     # If not cached, calculate from database
#     cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
#     
#     # Get all movements in the time period
#     movements = db.query(TrafficMovement).filter(
#         TrafficMovement.timestamp >= cutoff_time
#     ).all()
#     
#     # Calculate summary statistics
#     total_movements = len(movements)
#     arrivals = len([m for m in movements if m.movement_type == "arrival"])
#     departures = len([m for m in movements if m.movement_type == "departure"])
#     
#     # Group by airport
#     airport_stats = {}
#     for movement in movements:
#         airport = movement.airport_code
#         if airport not in airport_stats:
#             airport_stats[airport] = {"arrivals": 0, "departures": 0}
#         
#         if movement.movement_type == "arrival":
#             airport_stats[airport]["arrivals"] += 1
#         else:
#             airport_stats[airport]["departures"] += 1
#     
#     summary = {
#         "period_hours": hours,
#         "total_movements": total_movements,
#         "arrivals": arrivals,
#         "departures": departures,
#         "airport_breakdown": airport_stats,
#         "timestamp": datetime.now(timezone.utc).isoformat()
#     }
#     
#     # Cache the result
#     await cache_service.set_cached_data(cache_key, summary, 300)
#     
#     return summary

# DISABLED: Traffic Analysis Service Removal - Phase 1
# @app.get("/api/traffic/trends/{airport_icao}")
# @handle_service_errors
# @log_operation("get_traffic_trends")
# async def get_traffic_trends(
#     airport_icao: str,
#     days: int = 7,
#     db: Session = Depends(get_db)
# ):
#     """Get traffic trends for airport with caching"""
#     # Try to get from cache first
#     cache_service = await get_cache_service()
#     cache_key = f'traffic:trends:{airport_icao}:{days}d'
#     cached_trends = await cache_service.get_cached_data(cache_key)
#     
#     if cached_trends:
#         return cached_trends
#     
#     # If not cached, calculate from database
#     cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
#     
#     movements = db.query(TrafficMovement).filter(
#         and_(
#             TrafficMovement.airport_icao == airport_icao.upper(),
#             TrafficMovement.timestamp >= cutoff_time
#         )
#     ).order_by(TrafficMovement.timestamp).all()
#     
#     # Group by day
#     daily_stats = {}
#     for movement in movements:
#         date_key = movement.timestamp.date().isoformat()
#         if date_key not in daily_stats:
#             daily_stats[date_key] = {"arrivals": 0, "departures": 0}
#         
#         if movement.movement_type == "arrival":
#             daily_stats[date_key]["arrivals"] += 1
#         else:
#             daily_stats[date_key]["departures"] += 1
#     
#     trends = {
#         "airport_icao": airport_icao,
#         "period_days": days,
#         "daily_stats": daily_stats,
#         "total_movements": len(movements),
#         "timestamp": datetime.now(timezone.utc).isoformat()
#     }
#     
#     # Cache the result
#     await cache_service.set_cached_data(cache_key, trends, 3600)
#     
#     return trends

@app.get("/api/database/status")
@handle_service_errors
@log_operation("get_database_status")
async def get_database_status():
    """Get database status and migration information"""
    db_info = await get_database_info()
    cache_service = await get_cache_service()
    cache_stats = await cache_service.get_cache_stats()
    
    return {
        "database": db_info,
        "cache": cache_stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/performance/metrics")
@handle_service_errors
@log_operation("get_performance_metrics")
async def get_performance_metrics():
    """Get system performance metrics"""
    resource_manager = get_resource_manager()
    performance_metrics = await resource_manager.get_performance_metrics()
    
    return performance_metrics

@app.get("/api/flights/memory")
@handle_service_errors
@log_operation("get_flights_from_memory")
async def get_flights_from_memory():
    """Get flights directly from memory cache (for debugging)"""
    data_service = get_data_service()
    # Get cache size safely
    try:
        cache_size = len(data_service.cache['flights'].data) if hasattr(data_service.cache['flights'], 'data') else "unknown"
        logger.info(f"Memory cache has {cache_size} flights")
    except Exception as e:
        logger.warning(f"Could not get cache size: {e}")
        cache_size = "unknown"
    flights_data = []
    
    for callsign, flight_data in data_service.cache['flights'].items():
        flights_data.append({
            "callsign": flight_data.get('callsign', ''),
            "aircraft_type": flight_data.get('aircraft_type', ''),
            "departure": flight_data.get('departure', ''),
            "arrival": flight_data.get('arrival', ''),
            "altitude": flight_data.get('altitude', 0),
            "position_lat": flight_data.get('position_lat', 0.0),
            "position_lng": flight_data.get('position_lng', 0.0),
            "heading": flight_data.get('heading', 0),
            "groundspeed": flight_data.get('groundspeed', 0),
            "cruise_tas": flight_data.get('cruise_tas', 0),
            "squawk": flight_data.get('transponder', ''),

            "last_updated": flight_data.get('last_updated', '').isoformat() if hasattr(flight_data.get('last_updated', ''), 'isoformat') else str(flight_data.get('last_updated', ''))
        })
    
    return {"flights": flights_data, "total": len(flights_data), "cached": True}

@app.options("/api/performance/metrics")
async def options_performance_metrics():
    """Handle OPTIONS request for performance metrics"""
    return {"message": "OK"}

@app.get("/api/performance/optimize")
@handle_service_errors
@log_operation("optimize_performance")
async def optimize_performance(db: Session = Depends(get_db)):
    """Trigger performance optimization"""
    resource_manager = get_resource_manager()
    
    # Optimize memory usage
    memory_optimization = await resource_manager.optimize_memory_usage()
    
    # Optimize database queries with direct ANALYZE commands
    try:
        # Analyze table statistics for better query planning
        db.execute(text("ANALYZE"))
        
        # Update statistics for main tables
        tables = ["atc_positions", "flights"]
        for table in tables:
            try:
                db.execute(text(f"ANALYZE {table}"))
            except Exception as e:
                logger.warning(f"Could not analyze table {table}: {e}")
        
        db_optimization = {
            "status": "optimized",
            "tables_analyzed": len(tables),
            "optimization_timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        db_optimization = {
            "status": "error",
            "error": str(e),
            "optimization_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    return {
        "status": "optimized",
        "memory_optimization": memory_optimization,
        "database_optimization": db_optimization,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# REMOVED: Traffic Analysis Service - Phase 2
# @app.get("/traffic-dashboard")
# @handle_service_errors
# @log_operation("get_traffic_dashboard")
# async def get_traffic_dashboard():
#     """Get traffic dashboard HTML"""
#     # Traffic analysis service temporarily disabled
#     # traffic_service = get_traffic_analysis_service()
#     # dashboard_data = await traffic_service.generate_dashboard_data()
#     dashboard_data = {"message": "Traffic analysis temporarily disabled during database cleanup"}
#     
#     return dashboard_data

from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

@app.post("/api/database/query")
@handle_service_errors
@log_operation("execute_database_query")
async def execute_database_query(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """Execute custom SQL query and return results"""
    query = request.query
    
    # Security: Only allow SELECT queries
    if not query.strip().upper().startswith('SELECT'):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    
    # Execute query
    result = db.execute(text(query))
    rows = result.fetchall()
    
    # Convert to JSON-serializable format
    columns = result.keys()
    data = []
    for row in rows:
        row_dict = {}
        for i, column in enumerate(columns):
            value = row[i]
            # Handle datetime objects
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            row_dict[column] = value
        data.append(row_dict)
    
    return {
        "success": True,
        "data": data,
        "row_count": len(data),
        "columns": list(columns),
        "query": query,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/airports/region/{region}")
@handle_service_errors
@log_operation("get_airports_by_region_api")
async def get_airports_by_region_api(region: str = "Australia"):
    """Get airports for a specific region"""
    # Try to get from cache first (static data, long cache)
    cache_service = await get_cache_service()
    cache_key = f'airports:region:{region}'
    cached_data = await cache_service.get_cached_data(cache_key)
    
    if cached_data:
        return {
            **cached_data,
            "cached": True
        }
    
    stats = get_region_statistics(region)
    result = {
        "region": region,
        "total_airports": stats["total_airports"],
        "airports": stats["airports"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Cache the result for 10 minutes (static data)
    await cache_service.set_cached_data(cache_key, result, 600)
    
    return result

@app.get("/api/airports/{airport_code}/coordinates")
@handle_service_errors
@log_operation("get_airport_coordinates_api")
async def get_airport_coordinates_api(airport_code: str):
    """Get coordinates for a specific airport"""
    # Try to get from cache first (static data, long cache)
    cache_service = await get_cache_service()
    cache_key = f'airport:coords:{airport_code.upper()}'
    cached_data = await cache_service.get_cached_data(cache_key)
    
    if cached_data:
        return {
            **cached_data,
            "cached": True
        }
    
    coords = get_airport_coordinates(airport_code.upper())
    if coords is None:
        raise HTTPException(status_code=404, detail=f"Airport {airport_code} not found")
    
    result = {
        "airport_code": airport_code.upper(),
        "latitude": coords[0],
        "longitude": coords[1],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Cache the result for 1 hour (static data)
    await cache_service.set_cached_data(cache_key, result, 3600)
    
    return result

@app.get("/api/database/tables")
@handle_service_errors
@log_operation("get_database_tables")
async def get_database_tables(db: Session = Depends(get_db)):
    """Get list of database tables and their record counts"""
    # Get table information
    result = db.execute(text("""
        SELECT 
            table_name,
            (SELECT COUNT(*) FROM information_schema.tables t2 
             WHERE t2.table_name = t1.table_name) as record_count
        FROM information_schema.tables t1
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """))
    
    tables = []
    for row in result:
        # Get actual record count for each table
        try:
            count_result = db.execute(text(f"SELECT COUNT(*) FROM {row[0]}"))
            count = count_result.scalar()
            tables.append({
                "name": row[0],
                "record_count": count
            })
        except:
            tables.append({
                "name": row[0],
                "record_count": 0
            })
    
    return {
        "tables": tables,
        "total_tables": len(tables),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/health/comprehensive")
@handle_service_errors
@log_operation("get_comprehensive_health")
async def get_comprehensive_health():
    """Get comprehensive health report for all system components"""
    return await health_monitor.get_comprehensive_health_report()

@app.get("/api/health/endpoints")
@handle_service_errors
@log_operation("get_endpoint_health")
async def get_endpoint_health():
    """Get health status of all API endpoints"""
    return await health_monitor.check_api_endpoints()

@app.get("/api/health/database")
@handle_service_errors
@log_operation("get_database_health")
async def get_database_health():
    """Get database health status"""
    return await health_monitor.check_database_health()

@app.get("/api/health/system")
@handle_service_errors
@log_operation("get_system_health")
async def get_system_health():
    """Get system resource health status"""
    return await health_monitor.check_system_resources()

@app.get("/api/health/data-freshness")
@handle_service_errors
@log_operation("get_data_freshness")
async def get_data_freshness():
    """Get data freshness status"""
    return await health_monitor.check_data_freshness()



@app.get("/api/diagnostic/data-ingestion")
@handle_service_errors
@log_operation("get_data_ingestion_diagnostic")
async def get_data_ingestion_diagnostic(db: Session = Depends(get_db)):
    """Get detailed diagnostic information about data ingestion status"""
    try:
        # Check database state
        total_flights = db.query(Flight).count()
        total_controllers = db.query(Controller).count()
        total_airports = db.query(Airports).count()
        total_transceivers = db.query(Transceiver).count() if 'Transceiver' in globals() else 0
        
        # Check recent data
        recent_flights = db.query(Flight).filter(
            Flight.last_updated >= datetime.now(timezone.utc) - timedelta(hours=1)
        ).count()
        
        recent_controllers = db.query(Controller).filter(
            Controller.last_seen >= datetime.now(timezone.utc) - timedelta(hours=1)
        ).count()
        
        # Check VATSIM service status
        try:
            vatsim_service = get_vatsim_service()
            vatsim_status = await vatsim_service.get_api_status()
        except Exception as e:
            vatsim_status = {"error": str(e)}
        
        # Check data service status
        try:
            data_service = get_data_service()
            data_service_status = await data_service._perform_health_check()
        except Exception as e:
            data_service_status = {"error": str(e)}
        
        diagnostic = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_state": {
                "total_flights": total_flights,
                "total_controllers": total_controllers,
                "total_airports": total_airports,
                "total_transceivers": total_transceivers,
                "recent_flights_1h": recent_flights,
                "recent_controllers_1h": recent_controllers
            },
            "vatsim_service": vatsim_status,
            "data_service": data_service_status,
            "recommendations": []
        }
        
        # Generate recommendations based on diagnostic data
        if total_flights == 0 and total_controllers == 0:
            diagnostic["recommendations"].append("Database is empty - check if data ingestion is running")
            diagnostic["recommendations"].append("Verify VATSIM API connectivity")
            diagnostic["recommendations"].append("Check application logs for data ingestion errors")
        
        if recent_flights == 0 and total_flights > 0:
            diagnostic["recommendations"].append("No recent flight data - data ingestion may be stale")
        
        if recent_controllers == 0 and total_controllers > 0:
            diagnostic["recommendations"].append("No recent controller data - ATC data may be stale")
        
        return diagnostic
        
    except Exception as e:
        logger.error(f"Error in data ingestion diagnostic: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "error_type": type(e).__name__,
            "recommendations": ["Check application logs for detailed error information"]
        }


# Phase 2 API Endpoints

@app.get("/api/errors/analytics")
@handle_service_errors
@log_operation("get_error_analytics")
async def get_error_analytics_endpoint(hours: int = 24):
    """Get error analytics for the specified time period."""
    return get_error_analytics(hours)


@app.get("/api/errors/circuit-breakers")
@handle_service_errors
@log_operation("get_circuit_breaker_status")
async def get_circuit_breaker_status():
    """Get circuit breaker status for all services."""
    return get_circuit_breaker_status()


@app.get("/api/database/service/stats")
@handle_service_errors
@log_operation("get_database_service_stats")
async def get_database_service_stats():
    """Get database service statistics."""
    db_service = get_database_service()
    return await db_service.get_database_stats()


@app.get("/api/database/service/health")
@handle_service_errors
@log_operation("get_database_service_health")
async def get_database_service_health():
    """Get database service health status."""
    db_service = get_database_service()
    return await db_service.health_check()


@app.get("/api/events/analytics")
@handle_service_errors
@log_operation("get_event_analytics")
async def get_event_analytics():
    """Get event bus analytics and metrics."""
    event_bus = await get_event_bus()
    return event_bus.get_statistics()


# Phase 3 API Endpoints

@app.get("/api/monitoring/metrics")
@handle_service_errors
@log_operation("get_monitoring_metrics")
async def get_monitoring_metrics():
    """Get monitoring service metrics."""
    from .services.monitoring_service import get_monitoring_service
    monitoring_service = get_monitoring_service()
    return {
        "metrics_count": len(monitoring_service.metrics_collector.metrics),
        "active_alerts": len(monitoring_service.alert_manager.get_active_alerts()),
        "health_checks": len(monitoring_service.health_checker.health_status)
    }


@app.get("/api/monitoring/alerts")
@handle_service_errors
@log_operation("get_monitoring_alerts")
async def get_monitoring_alerts():
    """Get active monitoring alerts."""
    from .services.monitoring_service import get_monitoring_service
    monitoring_service = get_monitoring_service()
    alerts = monitoring_service.get_active_alerts()
    return [{
        "id": alert.id,
        "type": alert.type.value,
        "severity": alert.severity.value,
        "message": alert.message,
        "service": alert.service,
        "timestamp": alert.timestamp.isoformat(),
        "metadata": alert.metadata
    } for alert in alerts]


@app.get("/api/monitoring/health/{service_name}")
@handle_service_errors
@log_operation("get_service_health")
async def get_service_health(service_name: str):
    """Get health status for a specific service."""
    from .services.monitoring_service import get_monitoring_service
    monitoring_service = get_monitoring_service()
    health_status = await monitoring_service.get_health_status(service_name)
    if health_status:
        return {
            "service": health_status.service,
            "status": health_status.status,
            "timestamp": health_status.timestamp.isoformat(),
            "response_time": health_status.response_time,
            "error_count": health_status.error_count,
            "details": health_status.details
        }
    return {"error": f"Health status not found for service: {service_name}"}


@app.get("/api/performance/metrics/{operation}")
@handle_service_errors
@log_operation("get_performance_metrics")
async def get_performance_metrics(operation: str, service: str = "system", hours: int = 24):
    """Get performance metrics for a specific operation."""
    from .services.performance_monitor import get_performance_monitor, PerformanceMetric
    monitor = get_performance_monitor()
    
    # Get response time metrics
    response_time_summary = monitor.get_performance_summary(
        operation, service, PerformanceMetric.RESPONSE_TIME, hours
    )
    
    # Get memory usage metrics
    memory_summary = monitor.get_performance_summary(
        operation, service, PerformanceMetric.MEMORY_USAGE, hours
    )
    
    # Get CPU usage metrics
    cpu_summary = monitor.get_performance_summary(
        operation, service, PerformanceMetric.CPU_USAGE, hours
    )
    
    return {
        "operation": operation,
        "service": service,
        "hours": hours,
        "response_time": response_time_summary,
        "memory_usage": memory_summary,
        "cpu_usage": cpu_summary
    }


@app.get("/api/performance/recommendations")
@handle_service_errors
@log_operation("get_performance_recommendations")
async def get_performance_recommendations(service: Optional[str] = None, priority: Optional[str] = None):
    """Get performance optimization recommendations."""
    from .services.performance_monitor import get_performance_monitor
    monitor = get_performance_monitor()
    recommendations = monitor.get_optimization_recommendations(service, priority)
    
    return [{
        "id": rec.id,
        "operation": rec.operation,
        "service": rec.service,
        "recommendation_type": rec.recommendation_type,
        "description": rec.description,
        "expected_improvement": rec.expected_improvement,
        "implementation_difficulty": rec.implementation_difficulty,
        "priority": rec.priority,
        "timestamp": rec.timestamp.isoformat()
    } for rec in recommendations]


@app.get("/api/performance/alerts")
@handle_service_errors
@log_operation("get_performance_alerts")
async def get_performance_alerts():
    """Get active performance alerts."""
    from .services.performance_monitor import get_performance_monitor
    monitor = get_performance_monitor()
    alerts = monitor.get_performance_alerts()
    
    return [{
        "id": alert.id,
        "operation": alert.operation,
        "service": alert.service,
        "metric_type": alert.metric_type.value,
        "threshold": alert.threshold,
        "current_value": alert.current_value,
        "severity": alert.severity,
        "message": alert.message,
        "timestamp": alert.timestamp.isoformat()
    } for alert in alerts]


@app.get("/api/logging/analytics")
@handle_service_errors
@log_operation("get_logging_analytics")
async def get_logging_analytics(service_name: str = "global", hours: int = 24):
    """Get logging analytics for a service."""
    from .utils.structured_logging import get_structured_logger
    logger = get_structured_logger(service_name)
    analytics = logger.get_log_analytics(hours)
    
    return {
        "service": service_name,
        "hours": hours,
        **analytics
    }













@app.get("/api/frequency-matching/matches")
async def get_frequency_matches():
    """
    Get current frequency matches between pilots and ATC
    
    Returns:
        List of active frequency matches
    """
    try:
        matches = await frequency_matching_service.detect_frequency_matches()
        
        # Convert to JSON-serializable format
        matches_data = []
        for match in matches:
            match_data = {
                "pilot_callsign": match.pilot_callsign,
                "controller_callsign": match.controller_callsign,
                "frequency": match.frequency,
                "pilot_lat": match.pilot_lat,
                "pilot_lon": match.pilot_lon,
                "controller_lat": match.controller_lat,
                "controller_lon": match.controller_lon,
                "distance_nm": match.distance_nm,
                "match_timestamp": match.match_timestamp.isoformat(),
                "duration_seconds": match.duration_seconds,
                "is_active": match.is_active,
                "match_confidence": match.match_confidence,
                "communication_type": match.communication_type
            }
            matches_data.append(match_data)
        
        return {
            "status": "success",
            "matches": matches_data,
            "total_matches": len(matches_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting frequency matches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get frequency matches: {e}")


@app.get("/api/frequency-matching/summary")
async def get_frequency_match_summary():
    """
    Get summary statistics for frequency matching
    
    Returns:
        Frequency matching summary statistics
    """
    try:
        summary = await frequency_matching_service.get_frequency_match_summary()
        
        return {
            "status": "success",
            "summary": {
                "total_matches": summary.total_matches,
                "active_matches": summary.active_matches,
                "unique_pilots": summary.unique_pilots,
                "unique_controllers": summary.unique_controllers,
                "unique_frequencies": summary.unique_frequencies,
                "avg_match_duration": summary.avg_match_duration,
                "most_common_frequency": summary.most_common_frequency,
                "busiest_controller": summary.busiest_controller,
                "busiest_pilot": summary.busiest_pilot,
                "communication_patterns": summary.communication_patterns,
                "geographic_distribution": summary.geographic_distribution
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting frequency match summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get frequency match summary: {e}")


@app.get("/api/frequency-matching/patterns")
async def get_communication_patterns(frequency: Optional[int] = None):
    """
    Get communication patterns for frequency usage
    
    Args:
        frequency: Optional specific frequency to analyze (in Hz)
    
    Returns:
        Communication pattern analysis
    """
    try:
        patterns = await frequency_matching_service.get_communication_patterns(frequency)
        
        # Convert to JSON-serializable format
        patterns_data = []
        for pattern in patterns:
            pattern_data = {
                "frequency": pattern.frequency,
                "total_communications": pattern.total_communications,
                "unique_pilots": pattern.unique_pilots,
                "unique_controllers": pattern.unique_controllers,
                "avg_duration": pattern.avg_duration,
                "peak_hours": pattern.peak_hours,
                "communication_types": pattern.communication_types,
                "geographic_centers": pattern.geographic_centers
            }
            patterns_data.append(pattern_data)
        
        return {
            "status": "success",
            "patterns": patterns_data,
            "total_patterns": len(patterns_data),
            "frequency_filter": frequency,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting communication patterns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get communication patterns: {e}")


@app.get("/api/frequency-matching/health")
async def get_frequency_matching_health():
    """
    Get health status of frequency matching service
    
    Returns:
        Health status information
    """
    try:
        health = await frequency_matching_service.health_check()
        
        return {
            "status": "success",
            "health": health,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting frequency matching health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get frequency matching health: {e}")


@app.get("/api/frequency-matching/pilot/{callsign}")
async def get_pilot_frequency_matches(callsign: str):
    """
    Get frequency matches for a specific pilot
    
    Args:
        callsign: Pilot callsign to search for
    
    Returns:
        Frequency matches for the specified pilot
    """
    try:
        matches = await frequency_matching_service.detect_frequency_matches()
        
        # Filter for specific pilot
        pilot_matches = [m for m in matches if m.pilot_callsign.upper() == callsign.upper()]
        
        # Convert to JSON-serializable format
        matches_data = []
        for match in pilot_matches:
            match_data = {
                "pilot_callsign": match.pilot_callsign,
                "controller_callsign": match.controller_callsign,
                "frequency": match.frequency,
                "pilot_lat": match.pilot_lat,
                "pilot_lon": match.pilot_lon,
                "controller_lat": match.controller_lat,
                "controller_lon": match.controller_lon,
                "distance_nm": match.distance_nm,
                "match_timestamp": match.match_timestamp.isoformat(),
                "duration_seconds": match.duration_seconds,
                "is_active": match.is_active,
                "match_confidence": match.match_confidence,
                "communication_type": match.communication_type
            }
            matches_data.append(match_data)
        
        return {
            "status": "success",
            "pilot_callsign": callsign,
            "matches": matches_data,
            "total_matches": len(matches_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting pilot frequency matches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pilot frequency matches: {e}")


@app.get("/api/frequency-matching/controller/{callsign}")
async def get_controller_frequency_matches(callsign: str):
    """
    Get frequency matches for a specific controller
    
    Args:
        callsign: Controller callsign to search for
    
    Returns:
        Frequency matches for the specified controller
    """
    try:
        matches = await frequency_matching_service.detect_frequency_matches()
        
        # Filter for specific controller
        controller_matches = [m for m in matches if m.controller_callsign.upper() == callsign.upper()]
        
        # Convert to JSON-serializable format
        matches_data = []
        for match in controller_matches:
            match_data = {
                "pilot_callsign": match.pilot_callsign,
                "controller_callsign": match.controller_callsign,
                "frequency": match.frequency,
                "pilot_lat": match.pilot_lat,
                "pilot_lon": match.pilot_lon,
                "controller_lat": match.controller_lat,
                "controller_lon": match.controller_lon,
                "distance_nm": match.distance_nm,
                "match_timestamp": match.match_timestamp.isoformat(),
                "duration_seconds": match.duration_seconds,
                "is_active": match.is_active,
                "match_confidence": match.match_confidence,
                "communication_type": match.communication_type
            }
            matches_data.append(match_data)
        
        return {
            "status": "success",
            "controller_callsign": callsign,
            "matches": matches_data,
            "total_matches": len(matches_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting controller frequency matches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get controller frequency matches: {e}")


@app.get("/api/frequency-matching/frequency/{frequency_hz}")
async def get_frequency_matches_by_frequency(frequency_hz: int):
    """
    Get frequency matches for a specific frequency
    
    Args:
        frequency_hz: Frequency in Hz to search for
    
    Returns:
        Frequency matches for the specified frequency
    """
    try:
        matches = await frequency_matching_service.detect_frequency_matches()
        
        # Filter for specific frequency (with tolerance)
        tolerance = 100  # Hz tolerance
        frequency_matches = [m for m in matches if abs(m.frequency - frequency_hz) <= tolerance]
        
        # Convert to JSON-serializable format
        matches_data = []
        for match in frequency_matches:
            match_data = {
                "pilot_callsign": match.pilot_callsign,
                "controller_callsign": match.controller_callsign,
                "frequency": match.frequency,
                "pilot_lat": match.pilot_lat,
                "pilot_lon": match.pilot_lon,
                "controller_lat": match.controller_lat,
                "controller_lon": match.controller_lon,
                "distance_nm": match.distance_nm,
                "match_timestamp": match.match_timestamp.isoformat(),
                "duration_seconds": match.duration_seconds,
                "is_active": match.is_active,
                "match_confidence": match.match_confidence,
                "communication_type": match.communication_type
            }
            matches_data.append(match_data)
        
        return {
            "status": "success",
            "frequency_hz": frequency_hz,
            "tolerance_hz": tolerance,
            "matches": matches_data,
            "total_matches": len(matches_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting frequency matches by frequency: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get frequency matches by frequency: {e}")


@app.get("/api/frequency-matching/history")
async def get_historical_frequency_matches(
    pilot_callsign: Optional[str] = None,
    controller_callsign: Optional[str] = None,
    frequency: Optional[int] = None,
    hours: int = 24
):
    """
    Get historical frequency matches from database
    
    Args:
        pilot_callsign: Optional pilot callsign filter
        controller_callsign: Optional controller callsign filter
        frequency: Optional frequency filter (in Hz)
        hours: Number of hours to look back (default: 24)
    
    Returns:
        Historical frequency matches
    """
    try:
        matches = await frequency_matching_service.get_historical_frequency_matches(
            pilot_callsign=pilot_callsign,
            controller_callsign=controller_callsign,
            frequency=frequency,
            hours=hours
        )
        
        # Convert to JSON-serializable format
        matches_data = []
        for match in matches:
            match_data = {
                "id": match.id,
                "pilot_callsign": match.pilot_callsign,
                "controller_callsign": match.controller_callsign,
                "frequency": match.frequency,
                "pilot_lat": match.pilot_lat,
                "pilot_lon": match.pilot_lon,
                "controller_lat": match.controller_lat,
                "controller_lon": match.controller_lon,
                "distance_nm": match.distance_nm,
                "match_timestamp": match.match_timestamp.isoformat(),
                "duration_seconds": match.duration_seconds,
                "is_active": match.is_active,
                "match_confidence": match.match_confidence,
                "communication_type": match.communication_type,
                "created_at": match.created_at.isoformat() if match.created_at else None
            }
            matches_data.append(match_data)
        
        return {
            "status": "success",
            "matches": matches_data,
            "total_matches": len(matches_data),
            "filters": {
                "pilot_callsign": pilot_callsign,
                "controller_callsign": controller_callsign,
                "frequency": frequency,
                "hours": hours
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting historical frequency matches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get historical frequency matches: {e}")


@app.get("/api/frequency-matching/statistics")
async def get_frequency_matching_statistics(hours: int = 24):
    """
    Get comprehensive statistics for frequency matching
    
    Args:
        hours: Number of hours to analyze (default: 24)
    
    Returns:
        Frequency matching statistics
    """
    try:
        # Get historical data
        matches = await frequency_matching_service.get_historical_frequency_matches(hours=hours)
        
        if not matches:
            return {
                "status": "success",
                "statistics": {
                    "total_matches": 0,
                    "active_matches": 0,
                    "unique_pilots": 0,
                    "unique_controllers": 0,
                    "unique_frequencies": 0,
                    "avg_duration": 0.0,
                    "most_common_frequency": None,
                    "busiest_controller": None,
                    "busiest_pilot": None,
                    "communication_patterns": {},
                    "geographic_distribution": {},
                    "frequency_distribution": {},
                    "hourly_distribution": {}
                },
                "hours_analyzed": hours,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Calculate statistics
        unique_pilots = len(set(m.pilot_callsign for m in matches))
        unique_controllers = len(set(m.controller_callsign for m in matches))
        unique_frequencies = len(set(m.frequency for m in matches))
        
        # Average duration
        durations = [m.duration_seconds or 0 for m in matches if m.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        # Most common frequency
        frequency_counts = {}
        for match in matches:
            frequency_counts[match.frequency] = frequency_counts.get(match.frequency, 0) + 1
        most_common_frequency = max(frequency_counts.items(), key=lambda x: x[1])[0] if frequency_counts else None
        
        # Busiest controller and pilot
        controller_counts = {}
        pilot_counts = {}
        for match in matches:
            controller_counts[match.controller_callsign] = controller_counts.get(match.controller_callsign, 0) + 1
            pilot_counts[match.pilot_callsign] = pilot_counts.get(match.pilot_callsign, 0) + 1
        
        busiest_controller = max(controller_counts.items(), key=lambda x: x[1])[0] if controller_counts else None
        busiest_pilot = max(pilot_counts.items(), key=lambda x: x[1])[0] if pilot_counts else None
        
        # Communication patterns
        communication_patterns = {}
        for match in matches:
            comm_type = match.communication_type
            communication_patterns[comm_type] = communication_patterns.get(comm_type, 0) + 1
        
        # Geographic distribution
        geographic_distribution = {}
        for match in matches:
            if match.distance_nm:
                if match.distance_nm <= 10:
                    region = "local"
                elif match.distance_nm <= 50:
                    region = "regional"
                else:
                    region = "long_range"
                geographic_distribution[region] = geographic_distribution.get(region, 0) + 1
        
        # Frequency distribution
        frequency_distribution = {}
        for match in matches:
            freq_range = f"{match.frequency // 1000000}MHz"
            frequency_distribution[freq_range] = frequency_distribution.get(freq_range, 0) + 1
        
        # Hourly distribution
        hourly_distribution = {}
        for match in matches:
            hour = match.match_timestamp.hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
        
        statistics = {
            "total_matches": len(matches),
            "active_matches": len([m for m in matches if m.is_active]),
            "unique_pilots": unique_pilots,
            "unique_controllers": unique_controllers,
            "unique_frequencies": unique_frequencies,
            "avg_duration": avg_duration,
            "most_common_frequency": most_common_frequency,
            "busiest_controller": busiest_controller,
            "busiest_pilot": busiest_pilot,
            "communication_patterns": communication_patterns,
            "geographic_distribution": geographic_distribution,
            "frequency_distribution": frequency_distribution,
            "hourly_distribution": hourly_distribution
        }
        
        return {
            "status": "success",
            "statistics": statistics,
            "hours_analyzed": hours,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting frequency matching statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get frequency matching statistics: {e}")


@app.post("/api/frequency-matching/store")
async def store_current_frequency_matches():
    """
    Store current frequency matches in database
    
    Returns:
        Storage operation result
    """
    try:
        # Get current matches
        matches = await frequency_matching_service.detect_frequency_matches()
        
        # Store in database
        stored_count = await frequency_matching_service.store_frequency_matches(matches)
        
        return {
            "status": "success",
            "stored_count": stored_count,
            "total_matches": len(matches),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error storing frequency matches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store frequency matches: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
