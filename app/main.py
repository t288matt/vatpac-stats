from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from sqlalchemy import and_, desc

from .config import get_config, validate_config
from .database import get_db, init_db, get_database_info
from .models import Controller, Sector, Flight, TrafficMovement, AirportConfig
from .utils.logging import get_logger_for_module
from .services.vatsim_service import get_vatsim_service
from .services.data_service import get_data_service
from .services.traffic_analysis_service import get_traffic_analysis_service
from .services.cache_service import get_cache_service
from .services.query_optimizer import get_query_optimizer
from .services.resource_manager import get_resource_manager

# Configure logging
logger = get_logger_for_module(__name__)

# Background task for data ingestion
background_task = None

async def background_data_ingestion():
    """Background task for continuous data ingestion"""
    global background_task
    while True:
        try:
            data_service = get_data_service()
            await data_service.ingest_current_data()
            await asyncio.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error(f"Background data ingestion error: {e}")
            await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global background_task
    
    # Initialize database
    init_db()
    
    # Initialize cache service
    cache_service = await get_cache_service()
    
    # Initialize resource manager
    resource_manager = get_resource_manager()
    
    # Start background task
    background_task = asyncio.create_task(background_data_ingestion())
    
    yield
    
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VATSIM Data Collector</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-card { background: #ecf0f1; padding: 20px; border-radius: 5px; text-align: center; }
            .stat-number { font-size: 2em; font-weight: bold; color: #2c3e50; }
            .endpoints { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .endpoint { margin: 10px 0; padding: 10px; background: white; border-radius: 3px; }
            .method { font-weight: bold; color: #e74c3c; }
            .url { font-family: monospace; color: #3498db; }
            .database-info { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .migration-status { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚁 VATSIM Data Collector</h1>
                <p>Real-time air traffic control data collection and analysis system</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="controllers-count">-</div>
                    <div>Active Controllers</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="flights-count">-</div>
                    <div>Active Flights</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="airports-count">-</div>
                    <div>Monitored Airports</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="movements-count">-</div>
                    <div>Traffic Movements</div>
                </div>
            </div>
            
            <div class="endpoints">
                <h2>📡 API Endpoints</h2>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/status</span> - System status and statistics
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/controllers</span> - Active controllers data
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/flights</span> - Active flights data
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/traffic/movements/{airport}</span> - Airport traffic movements
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/database/status</span> - Database status and migration info
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/performance/metrics</span> - System performance metrics
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/performance-dashboard</span> - Performance monitoring dashboard
                </div>
            </div>
            
            <div class="database-info">
                <h2>🗄️ Database Status</h2>
                <div id="database-status">Loading...</div>
            </div>
            
            <div class="migration-status">
                <h2>🔄 Migration Status</h2>
                <div id="migration-status">Loading...</div>
            </div>
        </div>
        
        <script>
            async function updateStats() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    document.getElementById('controllers-count').textContent = data.controllers_count || 0;
                    document.getElementById('flights-count').textContent = data.flights_count || 0;
                    document.getElementById('airports-count').textContent = data.airports_count || 0;
                    document.getElementById('movements-count').textContent = data.movements_count || 0;
                } catch (error) {
                    console.error('Failed to update stats:', error);
                }
            }
            
            async function updateDatabaseStatus() {
                try {
                    const response = await fetch('/api/database/status');
                    const data = await response.json();
                    
                    document.getElementById('database-status').innerHTML = `
                        <strong>Status:</strong> ${data.database.database_type}<br>
                        <strong>Tables:</strong> ${data.database.tables_count}<br>
                        <strong>Total Records:</strong> ${data.database.total_records.toLocaleString()}<br>
                        <strong>Cache:</strong> ${data.cache.hits} hits, ${data.cache.misses} misses, ${data.cache.size} items
                    `;
                } catch (error) {
                    console.error('Failed to update database status:', error);
                }
            }
            
            // Update immediately and then every 30 seconds
            updateStats();
            updateDatabaseStatus();
            setInterval(updateStats, 30000);
            setInterval(updateDatabaseStatus, 60000);
        </script>
    </body>
    </html>
    """

@app.get("/api/status")
async def get_status(db: Session = Depends(get_db)):
    """Get system status with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_stats = await cache_service.get_network_stats_cache()
        
        if cached_stats:
            logger.info("Returning cached network stats")
            return cached_stats
        
        # If not cached, get from database
        controllers_count = db.query(Controller).filter(Controller.status == "online").count()
        flights_count = db.query(Flight).filter(Flight.status == "active").count()
        airports_count = db.query(AirportConfig).count()
        movements_count = db.query(TrafficMovement).filter(
            TrafficMovement.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        stats = {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "controllers_count": controllers_count,
            "flights_count": flights_count,
            "airports_count": airports_count,
            "movements_count": movements_count,
            "data_freshness": "real-time",
            "cache_status": "enabled"
        }
        
        # Cache the result
        await cache_service.set_network_stats_cache(stats)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/network/status")
async def get_network_status(db: Session = Depends(get_db)):
    """Get network status with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_data = await cache_service.get_cached_data('network:detailed_status')
        
        if cached_data:
            return cached_data
        
        # Get network data
        vatsim_service = get_vatsim_service()
        network_data = await vatsim_service.fetch_vatsim_data()
        
        if network_data:
            status = {
                "network_status": "connected",
                "controllers_count": len(network_data.get("controllers", [])),
                "flights_count": len(network_data.get("pilots", [])),
                "sectors_count": len(network_data.get("sectors", [])),
                "last_update": datetime.utcnow().isoformat()
            }
        else:
            status = {
                "network_status": "disconnected",
                "controllers_count": 0,
                "flights_count": 0,
                "sectors_count": 0,
                "last_update": datetime.utcnow().isoformat()
            }
        
        # Cache the result
        await cache_service.set_cached_data('network:detailed_status', status, 60)
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting network status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/controllers")
async def get_controllers(db: Session = Depends(get_db)):
    """Get active controllers with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_controllers = await cache_service.get_controllers_cache()
        
        if cached_controllers:
            logger.info("Returning cached controllers data")
            return {"controllers": cached_controllers['data'], "cached": True}
        
        # If not cached, get from database
        controllers = db.query(Controller).filter(Controller.status == "online").all()
        
        controllers_data = []
        for controller in controllers:
            controllers_data.append({
                "id": controller.id,
                "callsign": controller.callsign,
                "facility": controller.facility,
                "position": controller.position,
                "status": controller.status,
                "frequency": controller.frequency,
                "last_seen": controller.last_seen.isoformat() if controller.last_seen else None,
                "workload_score": controller.workload_score
            })
        
        # Cache the result
        await cache_service.set_controllers_cache(controllers_data)
        
        return {"controllers": controllers_data, "cached": False}
        
    except Exception as e:
        logger.error(f"Error getting controllers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/flights")
async def get_flights(db: Session = Depends(get_db)):
    """Get active flights with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_flights = await cache_service.get_flights_cache()
        
        if cached_flights:
            logger.info("Returning cached flights data")
            return {"flights": cached_flights['data'], "cached": False}
        
        # If not cached, get from database
        flights = db.query(Flight).filter(Flight.status == "active").all()
        
        flights_data = []
        for flight in flights:
            flights_data.append({
                "id": flight.id,
                "callsign": flight.callsign,
                "aircraft_type": flight.aircraft_type,
                "departure": flight.departure,
                "arrival": flight.arrival,
                "route": flight.route,
                "altitude": flight.altitude,
                "speed": flight.speed,
                "position": flight.position,
                "last_updated": flight.last_updated.isoformat() if flight.last_updated else None
            })
        
        # Cache the result
        await cache_service.set_flights_cache(flights_data)
        
        return {"flights": flights_data, "cached": False}
        
    except Exception as e:
        logger.error(f"Error getting flights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/traffic/movements/{airport_icao}")
async def get_airport_movements(
    airport_icao: str, 
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get traffic movements for specific airport with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_movements = await cache_service.get_traffic_movements_cache(airport_icao)
        
        if cached_movements:
            logger.info(f"Returning cached movements for {airport_icao}")
            return {"movements": cached_movements, "cached": True}
        
        # If not cached, get from database
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
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
        
    except Exception as e:
        logger.error(f"Error getting traffic movements for {airport_icao}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/traffic/summary/{region}")
async def get_traffic_summary(
    region: str = "Australia",
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get traffic summary for region with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cache_key = f'traffic:summary:{region}:{hours}h'
        cached_summary = await cache_service.get_cached_data(cache_key)
        
        if cached_summary:
            return cached_summary
        
        # If not cached, calculate from database
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get movements for Australian airports
        australian_airports = ["YSSY", "YMML", "YBBN", "YPPH", "YBCG", "YBCS", "YPDN", "YSCB", "YBAF"]
        
        movements = db.query(TrafficMovement).filter(
            and_(
                TrafficMovement.airport_icao.in_(australian_airports),
                TrafficMovement.timestamp >= cutoff_time
            )
        ).all()
        
        # Calculate summary statistics
        total_movements = len(movements)
        arrivals = len([m for m in movements if m.movement_type == "arrival"])
        departures = len([m for m in movements if m.movement_type == "departure"])
        
        # Group by airport
        airport_stats = {}
        for movement in movements:
            airport = movement.airport_icao
            if airport not in airport_stats:
                airport_stats[airport] = {"arrivals": 0, "departures": 0}
            
            if movement.movement_type == "arrival":
                airport_stats[airport]["arrivals"] += 1
            else:
                airport_stats[airport]["departures"] += 1
        
        summary = {
            "region": region,
            "period_hours": hours,
            "total_movements": total_movements,
            "arrivals": arrivals,
            "departures": departures,
            "airport_breakdown": airport_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache the result
        await cache_service.set_cached_data(cache_key, summary, 300)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting traffic summary for {region}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/traffic/trends/{airport_icao}")
async def get_traffic_trends(
    airport_icao: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get traffic trends for airport with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cache_key = f'traffic:trends:{airport_icao}:{days}d'
        cached_trends = await cache_service.get_cached_data(cache_key)
        
        if cached_trends:
            return cached_trends
        
        # If not cached, calculate from database
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
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
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache the result
        await cache_service.set_cached_data(cache_key, trends, 3600)
        
        return trends
        
    except Exception as e:
        logger.error(f"Error getting traffic trends for {airport_icao}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/database/status")
async def get_database_status():
    """Get database status and migration information"""
    try:
        db_info = get_database_info()
        cache_service = await get_cache_service()
        cache_stats = await cache_service.get_cache_stats()
        
        return {
            "database": db_info,
            "cache": cache_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/performance/metrics")
async def get_performance_metrics():
    """Get system performance metrics"""
    try:
        resource_manager = get_resource_manager()
        performance_metrics = await resource_manager.get_performance_metrics()
        
        return performance_metrics
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/performance/optimize")
async def optimize_performance():
    """Trigger performance optimization"""
    try:
        resource_manager = get_resource_manager()
        query_optimizer = get_query_optimizer()
        
        # Optimize memory usage
        memory_optimization = await resource_manager.optimize_memory_usage()
        
        # Optimize database queries
        db_optimization = await query_optimizer.optimize_database_queries(None)
        
        return {
            "memory_optimization": memory_optimization,
            "database_optimization": db_optimization,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/traffic-dashboard")
async def get_traffic_dashboard():
    """Get traffic dashboard HTML"""
    try:
        traffic_service = get_traffic_analysis_service()
        dashboard_data = await traffic_service.generate_dashboard_data()
        
        return HTMLResponse(content=dashboard_data, status_code=200)
    except Exception as e:
        logger.error(f"Error generating traffic dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/performance-dashboard")
async def get_performance_dashboard():
    """Get performance dashboard HTML"""
    try:
        with open("frontend/performance-dashboard.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving performance dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 