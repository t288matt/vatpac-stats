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
- /api/traffic/* - Traffic analysis endpoints

DEPENDENCIES:
- PostgreSQL database
- Redis cache
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
from datetime import datetime, timezone, timedelta, timezone, timezone
from sqlalchemy import and_, desc, text

from .config import get_config, validate_config
from .database import get_db, init_db, get_database_info, SessionLocal
from .models import Controller, Sector, Flight, TrafficMovement, AirportConfig, Transceiver
from .utils.logging import get_logger_for_module
from .utils.rating_utils import get_rating_name, get_rating_level, get_all_ratings, validate_rating
from .services.vatsim_service import get_vatsim_service
from .services.data_service import get_data_service
from .services.traffic_analysis_service import get_traffic_analysis_service
from .services.cache_service import get_cache_service
from .services.query_optimizer import get_query_optimizer
from .services.resource_manager import get_resource_manager
from .utils.airport_utils import get_airports_by_region, get_region_statistics, get_airport_coordinates
from .utils.error_monitoring import start_error_monitoring
from .api.error_monitoring import router as error_monitoring_router
from .utils.error_handling import handle_service_errors, log_operation, create_error_handler
from .utils.exceptions import APIError, DatabaseError, CacheError
from .utils.health_monitor import health_monitor
from .utils.schema_validator import ensure_database_schema
from .filters.flight_filter import FlightFilter

# Configure logging
logger = get_logger_for_module(__name__)

# Initialize centralized error handler
error_handler = create_error_handler("main_api")

# Background task for data ingestion
background_task = None

@handle_service_errors
@log_operation("background_data_ingestion")
async def background_data_ingestion():
    """Background task for continuous data ingestion"""
    global background_task
    while True:
        try:
            data_service = get_data_service()
            await data_service.start_data_ingestion()
            # Sleep interval is now handled inside the data service
        except Exception as e:
            logger.error(f"Background data ingestion error: {e}")
            await asyncio.sleep(30)  # Fallback sleep on error

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global background_task
    
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
        
        # Initialize cache service
        cache_service = await get_cache_service()
        
        # Initialize resource manager
        resource_manager = get_resource_manager()
        
        # Start error monitoring
        await start_error_monitoring()
        
        # Start background task
        background_task = asyncio.create_task(background_data_ingestion())
        
        yield
        
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise
    finally:
        # Cleanup
        if background_task:
            background_task.cancel()
            try:
                await background_task
            except asyncio.CancelledError:
                pass

# Create FastAPI app
app = FastAPI(
    title="VATSIM Data Collector",
    description="Real-time VATSIM data collection and traffic analysis system",
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
            flights_count = db.query(Flight).filter(Flight.status == "active").count()
        except Exception as e:
            logger.error(f"Error querying flights: {e}")
            # Check if the issue is with the controller_id column
            try:
                # Try a simpler query without relationships
                flights_count = db.query(Flight.id).filter(Flight.status == "active").count()
            except Exception as e2:
                logger.error(f"Error with simplified flight query: {e2}")
                flights_count = 0
        
        try:
            airports_count = db.query(AirportConfig).count()
        except Exception as e:
            logger.error(f"Error querying airports: {e}")
            airports_count = 0
        
        try:
            movements_count = db.query(TrafficMovement).filter(
                TrafficMovement.timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).count()
        except Exception as e:
            logger.error(f"Error querying movements: {e}")
            movements_count = 0
        
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
    flight_count = db.query(Flight).filter(Flight.status == "active").count()
    sector_count = db.query(Sector).count()
    
    status = {
        "total_controllers": atc_count,
        "total_flights": flight_count,
        "total_sectors": sector_count,
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
        # Count active flights from cached data
        active_count = len([flight for flight in cached_flights['data'] if flight.get("status") == "active"])
        return {
            "flights": cached_flights['data'],
            "total": len(cached_flights['data']),
            "active": active_count,
            "cached": True
        }
    
    # If not cached, get from database using direct SQL to avoid session isolation issues
    result = db.execute(text("SELECT * FROM flights WHERE status = 'active'"))
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
            "speed": row.speed,
            "heading": row.heading,
            "ground_speed": row.ground_speed,
            "vertical_speed": row.vertical_speed,
            "squawk": row.squawk,
            "position_lat": row.position_lat,
            "position_lng": row.position_lng,
            "controller_id": row.controller_id,
            "last_updated": row.last_updated.isoformat() if row.last_updated else None
        }
        
        # Debug: Log flights with controller_id
        if row.controller_id is not None:
            logger.info(f"Flight {row.callsign} has controller_id: {row.controller_id}")
        
        flights_data.append(flight_data)
    
    # Debug: Check if any flights have controller_id
    flights_with_controller = [f for f in flights_data if f['controller_id'] is not None]
    logger.info(f"Found {len(flights_with_controller)} flights with controller_id out of {len(flights_data)} total flights")
    
    # Cache the result
    await cache_service.set_flights_cache(flights_data)
    
    # Count active flights
    active_count = len([flight for flight in flights_data if flight.get("status") == "active"])
    
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
                    "speed": pos.speed,
                    "heading": pos.heading,
                    "ground_speed": pos.ground_speed,
                    "vertical_speed": pos.vertical_speed,
                    "squawk": pos.squawk
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
        
        # Find max altitude and speed
        max_altitude = max(pos.altitude or 0 for pos in positions)
        max_speed = max(pos.speed or 0 for pos in positions)
        
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
            "max_speed": max_speed,
            "route": first_pos.route
        }
    except Exception as e:
        logger.error(f"Error getting flight stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving flight statistics")

@app.get("/api/traffic/movements/{airport_icao}")
@handle_service_errors
@log_operation("get_airport_movements")
async def get_airport_movements(
    airport_icao: str, 
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get traffic movements for specific airport with caching"""
    # Try to get from cache first
    cache_service = await get_cache_service()
    cached_movements = await cache_service.get_traffic_movements_cache(airport_icao)
    
    if cached_movements:
        logger.info(f"Returning cached movements for {airport_icao}")
        return {"movements": cached_movements, "cached": True}
    
    # If not cached, get from database
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    movements = db.query(TrafficMovement).filter(
        and_(
            TrafficMovement.airport_icao == airport_icao.upper(),
            TrafficMovement.timestamp >= cutoff_time
        )
    ).order_by(desc(TrafficMovement.timestamp)).all()
    
    movements_data = []
    for movement in movements:
        movements_data.append({
            "id": movement.id,
            "airport_icao": movement.airport_icao,
            "flight_callsign": movement.flight_callsign,
            "movement_type": movement.movement_type,
            "timestamp": movement.timestamp.isoformat(),
            "confidence": movement.confidence,
            "altitude": movement.altitude,
            "speed": movement.speed
        })
    
    # Cache the result
    await cache_service.set_traffic_movements_cache(airport_icao, movements_data)
    
    return {"movements": movements_data, "cached": False}

@app.get("/api/traffic/summary")
@handle_service_errors
@log_operation("get_traffic_summary")
async def get_traffic_summary(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get traffic summary for all airports with caching"""
    # Try to get from cache first
    cache_service = await get_cache_service()
    cache_key = f'traffic:summary:all:{hours}h'
    cached_summary = await cache_service.get_cached_data(cache_key)
    
    if cached_summary:
        return cached_summary
    
    # If not cached, calculate from database
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Get all movements in the time period
    movements = db.query(TrafficMovement).filter(
        TrafficMovement.timestamp >= cutoff_time
    ).all()
    
    # Calculate summary statistics
    total_movements = len(movements)
    arrivals = len([m for m in movements if m.movement_type == "arrival"])
    departures = len([m for m in movements if m.movement_type == "departure"])
    
    # Group by airport
    airport_stats = {}
    for movement in movements:
        airport = movement.airport_code
        if airport not in airport_stats:
            airport_stats[airport] = {"arrivals": 0, "departures": 0}
        
        if movement.movement_type == "arrival":
            airport_stats[airport]["arrivals"] += 1
        else:
            airport_stats[airport]["departures"] += 1
    
    summary = {
        "period_hours": hours,
        "total_movements": total_movements,
        "arrivals": arrivals,
        "departures": departures,
        "airport_breakdown": airport_stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Cache the result
    await cache_service.set_cached_data(cache_key, summary, 300)
    
    return summary

@app.get("/api/traffic/trends/{airport_icao}")
@handle_service_errors
@log_operation("get_traffic_trends")
async def get_traffic_trends(
    airport_icao: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get traffic trends for airport with caching"""
    # Try to get from cache first
    cache_service = await get_cache_service()
    cache_key = f'traffic:trends:{airport_icao}:{days}d'
    cached_trends = await cache_service.get_cached_data(cache_key)
    
    if cached_trends:
        return cached_trends
    
    # If not cached, calculate from database
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
    
    movements = db.query(TrafficMovement).filter(
        and_(
            TrafficMovement.airport_icao == airport_icao.upper(),
            TrafficMovement.timestamp >= cutoff_time
        )
    ).order_by(TrafficMovement.timestamp).all()
    
    # Group by day
    daily_stats = {}
    for movement in movements:
        date_key = movement.timestamp.date().isoformat()
        if date_key not in daily_stats:
            daily_stats[date_key] = {"arrivals": 0, "departures": 0}
        
        if movement.movement_type == "arrival":
            daily_stats[date_key]["arrivals"] += 1
        else:
            daily_stats[date_key]["departures"] += 1
    
    trends = {
        "airport_icao": airport_icao,
        "period_days": days,
        "daily_stats": daily_stats,
        "total_movements": len(movements),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Cache the result
    await cache_service.set_cached_data(cache_key, trends, 3600)
    
    return trends

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
    logger.info(f"Memory cache has {len(data_service.cache['flights'])} flights")
    flights_data = []
    
    for callsign, flight_data in data_service.cache['flights'].items():
        flights_data.append({
            "callsign": flight_data.get('callsign', ''),
            "aircraft_type": flight_data.get('aircraft_type', ''),
            "departure": flight_data.get('departure', ''),
            "arrival": flight_data.get('arrival', ''),
            "altitude": flight_data.get('altitude', 0),
            "speed": flight_data.get('speed', 0),
            "position_lat": flight_data.get('position_lat', 0.0),
            "position_lng": flight_data.get('position_lng', 0.0),
            "heading": flight_data.get('heading', 0),
            "ground_speed": flight_data.get('ground_speed', 0),
            "vertical_speed": flight_data.get('vertical_speed', 0),
            "squawk": flight_data.get('squawk', ''),
            "controller_id": flight_data.get('controller_id'),
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
    query_optimizer = get_query_optimizer()
    
    # Optimize memory usage
    memory_optimization = await resource_manager.optimize_memory_usage()
    
    # Optimize database queries
    db_optimization = await query_optimizer.optimize_database_queries(db)
    
    return {
        "memory_optimization": memory_optimization,
        "database_optimization": db_optimization,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/traffic-dashboard")
@handle_service_errors
@log_operation("get_traffic_dashboard")
async def get_traffic_dashboard():
    """Get traffic dashboard HTML"""
    traffic_service = get_traffic_analysis_service()
    dashboard_data = await traffic_service.generate_dashboard_data()
    
    return dashboard_data

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

@app.get("/api/filter/flight/status")
@handle_service_errors
@log_operation("get_flight_filter_status")
async def get_flight_filter_status():
    """Get flight filter status and configuration"""
    flight_filter = FlightFilter()
    return flight_filter.get_filter_stats()

@app.get("/api/diagnostic/data-ingestion")
@handle_service_errors
@log_operation("get_data_ingestion_diagnostic")
async def get_data_ingestion_diagnostic(db: Session = Depends(get_db)):
    """Get detailed diagnostic information about data ingestion status"""
    try:
        # Check database state
        total_flights = db.query(Flight).count()
        total_controllers = db.query(Controller).count()
        total_airports = db.query(AirportConfig).count()
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
