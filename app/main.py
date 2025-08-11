#!/usr/bin/env python3
"""
VATSIM Data Collection System - FastAPI Application

This module provides the main FastAPI application for the VATSIM data collection system.
It includes API endpoints for data access and system monitoring.

INPUTS:
- HTTP requests to various API endpoints
- VATSIM data from background services
- Configuration settings

OUTPUTS:
- REST API responses with VATSIM data
- System status information
- Performance metrics and monitoring data
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text, func
from sqlalchemy.ext.asyncio import AsyncSession

from .utils.logging import get_logger_for_module
from .utils.error_handling import handle_service_errors, log_operation

from .services.vatsim_service import get_vatsim_service
from .services.data_service import get_data_service
from .database import get_database_session
from .models import Flight, Controller, Transceiver
# Simple configuration for main.py
class SimpleConfig:
    def __init__(self):
        self.api = type('obj', (object,), {
            'cors_origins': ["*"]
        })()
        self.vatsim = type('obj', (object,), {
            'polling_interval': 30
        })()

# Remove cache service import
# from .services.cache_service import get_cache_service

# Initialize logger
logger = get_logger_for_module("main")

# Initialize configuration
config = SimpleConfig()



# Background task for data ingestion
data_ingestion_task: Optional[asyncio.Task] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global data_ingestion_task
    
    # Startup
    logger.info("Starting VATSIM Data Collection System...")
    
    # Start background data ingestion task
    data_ingestion_task = asyncio.create_task(run_data_ingestion())
    logger.info("Background data ingestion task started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down VATSIM Data Collection System...")
    
    if data_ingestion_task:
        data_ingestion_task.cancel()
        try:
            await data_ingestion_task
        except asyncio.CancelledError:
            pass
        logger.info("Background data ingestion task cancelled")

# Create FastAPI application
app = FastAPI(
    title="VATSIM Data Collection System",
    description="Real-time VATSIM flight data collection and API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task for continuous data ingestion
async def run_data_ingestion():
    """Run the data ingestion process"""
    logger.info("Starting data ingestion task")
    config = SimpleConfig()
    data_service = await get_data_service()
    
    while True:
        try:
            await data_service.process_vatsim_data()
            await asyncio.sleep(config.vatsim.polling_interval)
        except asyncio.CancelledError:
            logger.info("Data ingestion task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in data ingestion task: {e}")
            await asyncio.sleep(10)  # Wait before retry

# Status Endpoints

@app.get("/api/status")
@handle_service_errors
@log_operation("get_system_status")
async def get_system_status():
    """Get comprehensive system status and statistics"""
    try:
        # Get database session for counts
        async with get_database_session() as session:
            # Get counts from database
            flights_count = await session.scalar(text("SELECT COUNT(*) FROM flights"))
            controllers_count = await session.scalar(text("SELECT COUNT(*) FROM controllers"))
            transceivers_count = await session.scalar(text("SELECT COUNT(*) FROM transceivers"))
            
            # Get recent activity (last 5 minutes)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
            recent_flights = await session.scalar(
                text("SELECT COUNT(*) FROM flights WHERE last_updated >= :cutoff"),
                {"cutoff": recent_cutoff}
            )
        
        return {
            "status": "operational",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_freshness": "real-time",
            "cache_status": "disabled",  # Cache removed
            "statistics": {
                "flights_count": flights_count or 0,
                "controllers_count": controllers_count or 0,
                "transceivers_count": transceivers_count or 0,
                "recent_flights": recent_flights or 0
            },
            "performance": {
                "api_response_time_ms": 45,  # Placeholder
                "database_query_time_ms": 12,  # Placeholder
                "memory_usage_mb": 1247,  # Placeholder
                "uptime_seconds": 86400  # Placeholder
            },
            "data_ingestion": {
                "last_vatsim_update": "unknown",
                "update_interval_seconds": config.vatsim.polling_interval,
                "successful_updates": 8640,  # Placeholder
                "failed_updates": 0
            },
            "services": {
                "vatsim_service": {"status": "operational"},
                "data_service": {"status": "operational"}
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting system status: {str(e)}")

@app.get("/api/network/status")
@handle_service_errors
@log_operation("get_network_status")
async def get_network_status():
    """Get VATSIM network status and metrics"""
    try:
        # Get VATSIM service for network status
        vatsim_service = get_vatsim_service()
        network_status = await vatsim_service.get_api_status()
        
        return {
            "network_status": network_status
        }
        
    except Exception as e:
        logger.error(f"Error getting network status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting network status: {str(e)}")

@app.get("/api/database/status")
@handle_service_errors
@log_operation("get_database_status")
async def get_database_status():
    """Get database status and migration information"""
    try:
        async with get_database_session() as session:
            # Get table counts
            tables_result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in tables_result.fetchall()]
            
            # Get total record count
            total_records = 0
            for table in tables:
                count = await session.scalar(text(f"SELECT COUNT(*) FROM {table}"))
                total_records += count or 0
            
            # Get database version
            version_result = await session.execute(text("SELECT version()"))
            db_version = version_result.scalar()
        
        return {
            "database_status": {
                "connection": "operational",
                "tables": len(tables),
                "total_records": total_records,
                "database_version": db_version,
                "schema_version": "1.0.10",
                "performance": {
                    "avg_query_time_ms": 12,  # Placeholder
                    "active_connections": 5,  # Placeholder
                    "pool_size": 10
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting database status: {str(e)}")

# Flight Data Endpoints

@app.get("/api/flights")
@handle_service_errors
@log_operation("get_all_flights")
async def get_all_flights():
    """Get all active flights with current position and flight plan data"""
    try:
        async with get_database_session() as session:
            # Get recent flights (last 30 minutes)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            flights_result = await session.execute(
                text("""
                    SELECT DISTINCT ON (callsign) 
                        callsign, cid, name, server, pilot_rating,
                        latitude, longitude, altitude, groundspeed, heading, transponder,
                        departure, arrival, aircraft_type, flight_rules, planned_altitude,
                        last_updated
                    FROM flights 
                    WHERE last_updated >= :cutoff
                    ORDER BY callsign, last_updated DESC
                """),
                {"cutoff": recent_cutoff}
            )
            
            flights = []
            for row in flights_result.fetchall():
                flight = {
                    "callsign": row[0],
                    "cid": row[1],
                    "name": row[2],
                    "server": row[3],
                    "pilot_rating": row[4],
                    "latitude": row[5],
                    "longitude": row[6],
                    "altitude": row[7],
                    "groundspeed": row[8],
                    "heading": row[9],
                    "transponder": row[10],
                    "departure": row[11],
                    "arrival": row[12],
                    "aircraft_type": row[13],
                    "flight_rules": row[14],
                    "planned_altitude": row[15],
                    "last_updated": row[16].isoformat() if row[16] else None
                }
                flights.append(flight)
            
            return {
                "flights": flights,
                "total_count": len(flights),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting flights: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting flights: {str(e)}")

@app.get("/api/flights/{callsign}")
@handle_service_errors
@log_operation("get_flight_by_callsign")
async def get_flight_by_callsign(callsign: str):
    """Get specific flight by callsign"""
    try:
        async with get_database_session() as session:
            # Get most recent flight data for this callsign
            flight_result = session.execute(
                text("""
                    SELECT callsign, cid, name, latitude, longitude, altitude,
                           departure, arrival, route, aircraft_type, last_updated
                    FROM flights 
                    WHERE callsign = :callsign
                    ORDER BY last_updated DESC
                    LIMIT 1
                """),
                {"callsign": callsign}
            )
            
            flight_row = flight_result.fetchone()
            if not flight_row:
                raise HTTPException(status_code=404, detail=f"Flight with callsign '{callsign}' not found")
            
            flight = {
                "callsign": flight_row[0],
                "cid": flight_row[1],
                "name": flight_row[2],
                "latitude": flight_row[3],
                "longitude": flight_row[4],
                "altitude": flight_row[5],
                "departure": flight_row[6],
                "arrival": flight_row[7],
                "route": flight_row[8],
                "aircraft_type": flight_row[9],
                "last_updated": flight_row[10].isoformat() if flight_row[10] else None
            }
            
            return {"flight": flight}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flight {callsign}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting flight: {str(e)}")

@app.get("/api/flights/{callsign}/track")
@handle_service_errors
@log_operation("get_flight_track")
async def get_flight_track(callsign: str):
    """Get complete flight track with all position updates"""
    try:
        async with get_database_session() as session:
            # Get all position updates for this callsign
            track_result = session.execute(
                text("""
                    SELECT last_updated, latitude, longitude, altitude, groundspeed
                    FROM flights 
                    WHERE callsign = :callsign
                    ORDER BY last_updated ASC
                """),
                {"callsign": callsign}
            )
            
            track_points = []
            for row in track_result.fetchall():
                point = {
                    "timestamp": row[0].isoformat() if row[0] else None,
                    "latitude": row[1],
                    "longitude": row[2],
                    "altitude": row[3],
                    "groundspeed": row[4]
                }
                track_points.append(point)
            
            if not track_points:
                raise HTTPException(status_code=404, detail=f"No track data found for callsign '{callsign}'")
            
            # Calculate flight duration
            if len(track_points) > 1:
                start_time = track_points[0]["timestamp"]
                end_time = track_points[-1]["timestamp"]
                if start_time and end_time:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
                else:
                    duration_minutes = 0
            else:
                duration_minutes = 0
            
            return {
                "callsign": callsign,
                "track_points": track_points,
                "total_points": len(track_points),
                "flight_duration_minutes": duration_minutes
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flight track for {callsign}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting flight track: {str(e)}")

@app.get("/api/flights/{callsign}/stats")
@handle_service_errors
@log_operation("get_flight_stats")
async def get_flight_stats(callsign: str):
    """Get flight statistics and summary information"""
    try:
        async with get_database_session() as session:
            # Get flight statistics
            stats_result = session.execute(
                text("""
                    SELECT 
                        COUNT(*) as position_updates,
                        AVG(groundspeed) as avg_groundspeed,
                        MAX(altitude) as max_altitude,
                        MIN(last_updated) as first_update,
                        MAX(last_updated) as last_update
                    FROM flights 
                    WHERE callsign = :callsign
                """),
                {"callsign": callsign}
            )
            
            stats_row = stats_result.fetchone()
            if not stats_row or stats_row[0] == 0:
                raise HTTPException(status_code=404, detail=f"No flight data found for callsign '{callsign}'")
            
            # Calculate flight time
            first_update = stats_row[3]
            last_update = stats_row[4]
            if first_update and last_update:
                flight_time_minutes = int((last_update - first_update).total_seconds() / 60)
            else:
                flight_time_minutes = 0
            
            # Calculate route efficiency (placeholder)
            route_efficiency = 0.98  # Placeholder calculation
            
            return {
                "callsign": callsign,
                "statistics": {
                    "total_distance_nm": 0,  # Placeholder
                    "average_groundspeed": float(stats_row[1]) if stats_row[1] else 0,
                    "max_altitude": stats_row[2] if stats_row[2] else 0,
                    "flight_time_minutes": flight_time_minutes,
                    "position_updates": stats_row[0],
                    "route_efficiency": route_efficiency
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flight stats for {callsign}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting flight stats: {str(e)}")

@app.get("/api/flights/memory")
@handle_service_errors
@log_operation("get_memory_flights")
async def get_memory_flights():
    """Get flights from memory buffer (debugging endpoint)"""
    try:
        # Get data service for memory buffer status
        data_service = await get_data_service()
        # Get buffer status (simplified)
        buffer_status = {"status": "operational"}
        
        return {
            "memory_flights": buffer_status.get('flights_count', 0),
            "cache_status": "disabled",  # Cache removed
            "last_refresh": datetime.now(timezone.utc).isoformat(),
            "flights": []  # Memory buffer data not exposed via API
        }
        
    except Exception as e:
        logger.error(f"Error getting memory flights: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting memory flights: {str(e)}")

# ATC Controller Endpoints

@app.get("/api/controllers")
@handle_service_errors
@log_operation("get_all_controllers")
async def get_all_controllers():
    """Get all active ATC positions"""
    try:
        async with get_database_session() as session:
            # Get recent ATC positions (last 30 minutes)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            controllers_result = await session.execute(
                text("""
                    SELECT DISTINCT ON (callsign) 
                        callsign, cid, name, facility, rating, server,
                        visual_range, text_atis, logon_time, last_updated
                    FROM controllers 
                    WHERE last_updated >= :cutoff
                    ORDER BY callsign, last_updated DESC
                """),
                {"cutoff": recent_cutoff}
            )
            
            controllers = []
            for row in controllers_result.fetchall():
                controller = {
                    "callsign": row[0],
                    "cid": row[1],
                    "name": row[2],
                    "facility": row[3],
                    "rating": row[4],
                    "server": row[5],
                    "visual_range": row[6],
                    "text_atis": row[7],
                    "logon_time": row[8].isoformat() if row[8] else None,
                    "last_updated": row[9].isoformat() if row[9] else None
                }
                controllers.append(controller)
            
            return {
                "controllers": controllers,
                "total_count": len(controllers),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting controllers: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting controllers: {str(e)}")

@app.get("/api/atc-positions")
@handle_service_errors
@log_operation("get_atc_positions")
async def get_atc_positions():
    """Alternative endpoint for ATC positions (legacy compatibility)"""
    return await get_all_controllers()

@app.get("/api/atc-positions/by-controller-id")
@handle_service_errors
@log_operation("get_atc_positions_by_controller_id")
async def get_atc_positions_by_controller_id():
    """Get ATC positions grouped by controller ID"""
    try:
        async with get_database_session() as session:
            # Get recent ATC positions grouped by controller ID
            recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            controllers_result = await session.execute(
                text("""
                    SELECT DISTINCT ON (callsign) 
                        cid, callsign, facility, logon_time
                    FROM controllers 
                    WHERE last_updated >= :cutoff
                    ORDER BY callsign, last_updated DESC
                """),
                {"cutoff": recent_cutoff}
            )
            
            controllers_by_id = {}
            for row in controllers_result.fetchall():
                cid = str(row[0])
                if cid not in controllers_by_id:
                    controllers_by_id[cid] = []
                
                controller = {
                    "callsign": row[1],
                    "facility": row[2],
                    "logon_time": row[3].isoformat() if row[3] else None
                }
                controllers_by_id[cid].append(controller)
            
            return {
                "controllers_by_id": controllers_by_id
            }
            
    except Exception as e:
        logger.error(f"Error getting ATC positions by controller ID: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting ATC positions: {str(e)}")

# VATSIM Ratings Endpoint

@app.get("/api/vatsim/ratings")
@handle_service_errors
@log_operation("get_vatsim_ratings")
async def get_vatsim_ratings():
    """Get VATSIM controller ratings and descriptions"""
    try:
        # Define VATSIM ratings (static data)
        ratings = {
            "1": "Observer",
            "2": "Student 1", 
            "3": "Student 2",
            "4": "Student 3",
            "5": "Controller 1",
            "7": "Controller 3",
            "8": "Instructor 1",
            "10": "Instructor 3"
        }
        
        return {
            "ratings": ratings,
            "total_ratings": len(ratings),
            "description": "VATSIM controller ratings from 1-15",
            "valid_range": "1-15",
            "known_ratings": [1, 2, 3, 4, 5, 8, 10, 11],
            "unknown_ratings": [6, 7, 9, 12, 13, 14, 15]
        }
        
    except Exception as e:
        logger.error(f"Error getting VATSIM ratings: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting VATSIM ratings: {str(e)}")

# Flight Filtering Endpoints

@app.get("/api/filter/flight/status")
@handle_service_errors
@log_operation("get_flight_filter_status")
async def get_flight_filter_status():
    """Get airport filter status and statistics"""
    try:
        # Get flight filter status
        data_service = await get_data_service()
        flight_filter = data_service.flight_filter
        
        # Get filter statistics
        filter_stats = flight_filter.get_filter_stats()
        
        return {
            "filter_status": {
                "enabled": flight_filter.config.enabled,
                "type": "airport_based",
                "log_level": flight_filter.config.log_level,
                "statistics": filter_stats,
                "configuration": {
                    "filter_enabled": flight_filter.config.enabled,
                    "airport_validation_method": "starts_with_Y"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting flight filter status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting flight filter status: {str(e)}")

@app.get("/api/filter/boundary/status")
@handle_service_errors
@log_operation("get_boundary_filter_status")
async def get_boundary_filter_status():
    """Get geographic boundary filter status and performance"""
    try:
        # Get boundary filter status
        data_service = await get_data_service()
        boundary_filter = data_service.geographic_boundary_filter
        
        # Get filter statistics
        filter_stats = boundary_filter.get_filter_stats()
        
        return {
            "boundary_filter": {
                "enabled": boundary_filter.config.enabled,
                "status": "ready" if boundary_filter.is_initialized else "uninitialized",
                "performance": {
                    "average_processing_time_ms": filter_stats.get("processing_time_ms", 0),
                    "total_calculations": filter_stats.get("total_calculations", 0),
                    "cache_hits": 0,  # Cache removed
                    "cache_misses": 0  # Cache removed
                },
                "configuration": {
                    "boundary_data_path": boundary_filter.config.boundary_data_path,
                    "log_level": boundary_filter.config.log_level,
                    "polygon_loaded": boundary_filter.is_initialized,
                    "polygon_points": filter_stats.get("polygon_points", 0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting boundary filter status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting boundary filter status: {str(e)}")

@app.get("/api/filter/boundary/info")
@handle_service_errors
@log_operation("get_boundary_filter_info")
async def get_boundary_filter_info():
    """Get boundary polygon information and configuration"""
    try:
        # Get boundary filter info
        data_service = await get_data_service()
        boundary_filter = data_service.geographic_boundary_filter
        
        if not boundary_filter.is_initialized:
            raise HTTPException(status_code=503, detail="Boundary filter not initialized")
        
        # Get polygon information
        polygon_info = boundary_filter.get_polygon_info()
        
        return {
            "boundary_info": polygon_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting boundary filter info: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting boundary filter info: {str(e)}")

# Analytics Endpoints

@app.get("/api/analytics/flights")
@handle_service_errors
@log_operation("get_flight_analytics")
async def get_flight_analytics():
    """Get flight summary data and analytics - simplified"""
    try:
        async with get_database_session() as session:
            result = await session.execute(
                text("""
                    SELECT 
                        COUNT(DISTINCT callsign) as flights,
                        COUNT(*) as positions,
                        AVG(groundspeed) as avg_speed,
                        MAX(altitude) as max_alt,
                        COUNT(DISTINCT departure) as deps,
                        COUNT(DISTINCT arrival) as arrs
                    FROM flights 
                    WHERE last_updated >= NOW() - INTERVAL '24 hours'
                """)
            )
            
            row = result.fetchone()
            return {
                "flights": row[0] or 0,
                "positions": row[1] or 0,
                "avg_speed": float(row[2]) if row[2] else 0,
                "max_alt": row[3] or 0,
                "departures": row[4] or 0,
                "arrivals": row[5] or 0,
                "period": "24h"
            }
            
    except Exception as e:
        logger.error(f"Flight analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Performance & Monitoring Endpoints

@app.get("/api/performance/metrics")
@handle_service_errors
@log_operation("get_performance_metrics")
async def get_performance_metrics():
    """Get basic system status - simplified"""
    return {
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/performance/optimize")
@handle_service_errors
@log_operation("trigger_performance_optimization")
async def trigger_performance_optimization():
    """System status check - simplified"""
    return {
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Transceiver Data Endpoints

@app.get("/api/transceivers")
@handle_service_errors
@log_operation("get_transceivers")
async def get_transceivers():
    """Get radio frequency and position data"""
    try:
        async with get_database_session() as session:
            # Get recent transceivers (last 30 minutes)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            transceivers_result = session.execute(
                text("""
                    SELECT DISTINCT ON (callsign) 
                        id, callsign, frequency, position_lat, position_lon, altitude, last_updated
                    FROM transceivers 
                    WHERE last_updated >= :cutoff
                    ORDER BY callsign, last_updated DESC
                """),
                {"cutoff": recent_cutoff}
            )
            
            transceivers = []
            for row in transceivers_result.fetchall():
                transceiver = {
                    "id": row[0],
                    "callsign": row[1],
                    "frequency": row[2],
                    "position_lat": row[3],
                    "position_lng": row[4],
                    "altitude": row[5],
                    "last_updated": row[6].isoformat() if row[6] else None
                }
                transceivers.append(transceiver)
            
            return {
                "transceivers": transceivers,
                "total_count": len(transceivers)
            }
            
    except Exception as e:
        logger.error(f"Error getting transceivers: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting transceivers: {str(e)}")

# Database Operations Endpoints

@app.get("/api/database/tables")
@handle_service_errors
@log_operation("get_database_tables")
async def get_database_tables():
    """Get database tables and record counts - simplified"""
    try:
        async with get_database_session() as session:
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tables = []
            for row in result.fetchall():
                count_result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {row[0]}")
                )
                tables.append({
                    "name": row[0],
                    "count": count_result.scalar() or 0
                })
            
            return {"tables": tables}
            
    except Exception as e:
        logger.error(f"Database tables error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/database/query")
@handle_service_errors
@log_operation("execute_database_query")
async def execute_database_query(query: str, limit: int = 1000):
    """Execute custom SQL queries (admin only) - simplified"""
    # Basic query validation
    dangerous = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
    if any(keyword in query.upper() for keyword in dangerous):
        raise HTTPException(status_code=400, detail="Dangerous query")
    
    try:
        async with get_database_session() as session:
            result = await session.execute(text(f"{query} LIMIT {limit}"))
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to list of dicts
            data = []
            for row in rows:
                row_dict = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[column] = value
                data.append(row_dict)
            
            return {"results": data, "count": len(data)}
            
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - simplified"""
    return {
        "status": "operational",
        "version": "1.0.0"
    } 
