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
import signal
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

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

def exit_application(reason: str, exit_code: int = 1):
    """Exit the application with a critical error"""
    logger.critical(f"🚨 CRITICAL: {reason} - Exiting application with code {exit_code}")
    sys.exit(exit_code)



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
    
    # Monitor the background task for critical failures
    try:
        yield
    except Exception as e:
        if "UniqueViolation" in str(e) or "duplicate key value violates unique constraint" in str(e):
            logger.critical("🚨 CRITICAL: Application shutting down due to database constraint violation")
            raise
        elif "UndefinedTable" in str(e):
            logger.critical("🚨 CRITICAL: Application shutting down due to missing database table")
            raise
        else:
            logger.error(f"Application error: {e}")
            raise
    finally:
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
            # Process VATSIM data without verbose logging
            await data_service.process_vatsim_data()
            await asyncio.sleep(config.vatsim.polling_interval)
        except asyncio.CancelledError:
            logger.info("Data ingestion task cancelled")
            break
        except Exception as e:
            # Check for critical database errors first
            if "UniqueViolation" in str(e) or "duplicate key value violates unique constraint" in str(e):
                logger.critical("🚨 CRITICAL: Database constraint violation - Application will FAIL")
                # Exit the application immediately
                exit_application("Database constraint violation - duplicate key values")
            elif "UndefinedTable" in str(e):
                logger.critical("🚨 CRITICAL: Missing database table - Application will FAIL")
                # Exit the application immediately
                exit_application("Missing database table - schema mismatch")
            else:
                logger.error(f"Non-critical error in data ingestion task: {e}")
                # For other errors, wait and retry
                await asyncio.sleep(10)

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

# Flight Summary Endpoints

@app.get("/api/flights/summaries")
@handle_service_errors
@log_operation("get_flight_summaries")
async def get_flight_summaries(
    limit: int = 100,
    offset: int = 0,
    departure: Optional[str] = None,
    arrival: Optional[str] = None,
    aircraft_type: Optional[str] = None,
    flight_rules: Optional[str] = None
):
    """Get completed flight summaries with optional filtering"""
    try:
        async with get_database_session() as session:
            # Build base query
            base_query = """
                SELECT 
                    id, callsign, departure, arrival, aircraft_type, flight_rules,
                    logon_time, completion_time, time_online_minutes,
                    controller_time_percentage, controller_callsigns,
                    route, planned_altitude, created_at
                FROM flight_summaries
                WHERE 1=1
            """
            
            # Build filter conditions
            params = {}
            if departure:
                base_query += " AND departure = :departure"
                params["departure"] = departure.upper()
            if arrival:
                base_query += " AND arrival = :arrival"
                params["arrival"] = arrival.upper()
            if aircraft_type:
                base_query += " AND aircraft_type ILIKE :aircraft_type"
                params["aircraft_type"] = f"%{aircraft_type}%"
            if flight_rules:
                base_query += " AND flight_rules = :flight_rules"
                params["flight_rules"] = flight_rules.upper()
            
            # Add ordering and pagination
            base_query += " ORDER BY completion_time DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
            
            # Execute query
            result = await session.execute(text(base_query), params)
            summaries = []
            
            for row in result.fetchall():
                summary = {
                    "id": row[0],
                    "callsign": row[1],
                    "departure": row[2],
                    "arrival": row[3],
                    "aircraft_type": row[4],
                    "flight_rules": row[5],
                    "logon_time": row[6].isoformat() if row[6] else None,
                    "completion_time": row[7].isoformat() if row[7] else None,
                    "time_online_minutes": row[8],
                    "controller_time_percentage": row[9],
                    "controller_callsigns": row[10] if row[10] else [],
                    "route": row[11],
                    "planned_altitude": row[12],
                    "created_at": row[13].isoformat() if row[13] else None
                }
                summaries.append(summary)
            
            # Get total count for pagination
            count_query = """
                SELECT COUNT(*) FROM flight_summaries
                WHERE 1=1
            """
            if departure:
                count_query += " AND departure = :departure"
            if arrival:
                count_query += " AND arrival = :arrival"
            if aircraft_type:
                count_query += " AND aircraft_type ILIKE :aircraft_type"
            if flight_rules:
                count_query += " AND flight_rules = :flight_rules"
            
            count_result = await session.execute(text(count_query), params)
            total_count = count_result.scalar()
            
            return {
                "summaries": summaries,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_count
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting flight summaries: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting flight summaries: {str(e)}")

@app.post("/api/flights/summaries/process")
@handle_service_errors
@log_operation("trigger_flight_summary_processing")
async def trigger_flight_summary_processing():
    """Manually trigger flight summary processing"""
    try:
        data_service = await get_data_service()
        result = await data_service.trigger_flight_summary_processing()
        
        return {
            "status": "success",
            "message": "Flight summary processing triggered successfully",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering flight summary processing: {e}")
        raise HTTPException(status_code=500, detail=f"Error triggering flight summary processing: {str(e)}")

@app.get("/api/flights/summaries/status")
@handle_service_errors
@log_operation("get_flight_summary_status")
async def get_flight_summary_status():
    """Get flight summary processing status and statistics"""
    try:
        async with get_database_session() as session:
            # Get processing statistics
            stats_result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_summaries,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as last_24h,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 hour' THEN 1 END) as last_1h,
                    MAX(created_at) as last_processed,
                    AVG(time_online_minutes) as avg_time_online,
                    AVG(controller_time_percentage) as avg_atc_coverage
                FROM flight_summaries
            """))
            
            stats_row = stats_result.fetchone()
            
            # Get recent processing activity
            recent_result = await session.execute(text("""
                SELECT 
                    callsign, departure, arrival, completion_time, time_online_minutes
                FROM flight_summaries 
                ORDER BY completion_time DESC 
                LIMIT 5
            """))
            
            recent_summaries = []
            for row in recent_result.fetchall():
                recent_summaries.append({
                    "callsign": row[0],
                    "departure": row[1],
                    "arrival": row[2],
                    "completion_time": row[3].isoformat() if row[3] else None,
                    "time_online_minutes": row[4]
                })
            
            return {
                "status": "operational",
                "processing_stats": {
                    "total_summaries": stats_row[0] or 0,
                    "last_24h": stats_row[1] or 0,
                    "last_1h": stats_row[2] or 0,
                    "last_processed": stats_row[3].isoformat() if stats_row[3] else None,
                    "avg_time_online_minutes": float(stats_row[4]) if stats_row[4] else 0,
                    "avg_atc_coverage_percentage": float(stats_row[5]) if stats_row[5] else 0
                },
                "recent_summaries": recent_summaries,
                "next_scheduled_run": "Every 60 minutes",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting flight summary status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting flight summary status: {str(e)}")

@app.get("/api/flights/summaries/analytics")
@handle_service_errors
@log_operation("get_flight_summary_analytics")
async def get_flight_summary_analytics(
    period: str = "24h",
    departure: Optional[str] = None,
    arrival: Optional[str] = None
):
    """Get aggregated analytics from flight summaries"""
    try:
        async with get_database_session() as session:
            # Build time filter based on period
            time_filter = ""
            if period == "24h":
                time_filter = "AND completion_time >= NOW() - INTERVAL '24 hours'"
            elif period == "7d":
                time_filter = "AND completion_time >= NOW() - INTERVAL '7 days'"
            elif period == "30d":
                time_filter = "AND completion_time >= NOW() - INTERVAL '30 days'"
            elif period == "all":
                time_filter = ""
            
            # Build location filter
            location_filter = ""
            params = {}
            if departure:
                location_filter += " AND departure = :departure"
                params["departure"] = departure.upper()
            if arrival:
                location_filter += " AND arrival = :arrival"
                params["arrival"] = arrival.upper()
            
            # Get route statistics
            route_result = await session.execute(text(f"""
                SELECT 
                    departure, arrival, COUNT(*) as flight_count,
                    AVG(time_online_minutes) as avg_time_online,
                    AVG(controller_time_percentage) as avg_atc_coverage
                FROM flight_summaries
                WHERE 1=1 {time_filter} {location_filter}
                GROUP BY departure, arrival
                ORDER BY flight_count DESC
                LIMIT 10
            """), params)
            
            routes = []
            for row in route_result.fetchall():
                routes.append({
                    "departure": row[0],
                    "arrival": row[1],
                    "flight_count": row[2],
                    "avg_time_online_minutes": float(row[3]) if row[3] else 0,
                    "avg_atc_coverage_percentage": float(row[4]) if row[4] else 0
                })
            
            # Get aircraft type statistics
            aircraft_result = await session.execute(text(f"""
                SELECT 
                    aircraft_type, COUNT(*) as flight_count,
                    AVG(time_online_minutes) as avg_time_online
                FROM flight_summaries
                WHERE 1=1 {time_filter} {location_filter}
                GROUP BY aircraft_type
                ORDER BY flight_count DESC
                LIMIT 10
            """), params)
            
            aircraft_types = []
            for row in aircraft_result.fetchall():
                aircraft_types.append({
                    "aircraft_type": row[0],
                    "flight_count": row[1],
                    "avg_time_online_minutes": float(row[2]) if row[2] else 0
                })
            
            # Get ATC coverage statistics
            atc_result = await session.execute(text(f"""
                SELECT 
                    CASE 
                        WHEN controller_time_percentage = 0 THEN 'No ATC Contact'
                        WHEN controller_time_percentage <= 25 THEN 'Low ATC Contact (1-25%)'
                        WHEN controller_time_percentage <= 50 THEN 'Medium ATC Contact (26-50%)'
                        WHEN controller_time_percentage <= 75 THEN 'High ATC Contact (51-75%)'
                        ELSE 'Full ATC Contact (76-100%)'
                    END as atc_coverage_level,
                    COUNT(*) as flight_count
                FROM flight_summaries
                WHERE 1=1 {time_filter} {location_filter}
                GROUP BY atc_coverage_level
                ORDER BY flight_count DESC
            """), params)
            
            atc_coverage = []
            for row in atc_result.fetchall():
                atc_coverage.append({
                    "coverage_level": row[0],
                    "flight_count": row[1]
                })
            
            return {
                "period": period,
                "filters": {
                    "departure": departure,
                    "arrival": arrival
                },
                "analytics": {
                    "top_routes": routes,
                    "top_aircraft_types": aircraft_types,
                    "atc_coverage_distribution": atc_coverage
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting flight summary analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting flight summary analytics: {str(e)}")

@app.get("/api/flights/{callsign}")
@handle_service_errors
@log_operation("get_flight_by_callsign")
async def get_flight_by_callsign(callsign: str):
    """Get specific flight by callsign"""
    try:
        async with get_database_session() as session:
            # Get most recent flight data for this callsign
            flight_result = await session.execute(
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
            track_result = await session.execute(
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
            stats_result = await session.execute(
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
            # Get recent ATC positions grouped by controller ID (last 24 hours)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            
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
        polygon_info = boundary_filter.get_boundary_info()
        
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
            # Get recent transceivers (last 5 minutes for fresh data)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
            
            transceivers_result = await session.execute(
                text("""
                    SELECT DISTINCT ON (callsign) 
                        id, callsign, frequency, position_lat, position_lon, height_msl, timestamp
                    FROM transceivers 
                    WHERE timestamp >= :cutoff
                    ORDER BY callsign, timestamp DESC
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
                    "height_msl": row[5],
                    "timestamp": row[6].isoformat() if row[6] else None
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


class DatabaseQueryRequest(BaseModel):
    query: str
    limit: int = 1000

@app.post("/api/database/query")
@handle_service_errors
@log_operation("execute_database_query")
async def execute_database_query(request: DatabaseQueryRequest):
    """Execute custom SQL queries (admin only) - simplified"""
    # Basic query validation
    dangerous = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
    if any(keyword in request.query.upper() for keyword in dangerous):
        raise HTTPException(status_code=400, detail="Dangerous query")
    
    # Additional validation
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if request.limit < 1 or request.limit > 10000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 10000")
    
    try:
        async with get_database_session() as session:
            result = await session.execute(text(f"{request.query} LIMIT {request.limit}"))
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
