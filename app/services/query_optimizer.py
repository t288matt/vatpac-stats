#!/usr/bin/env python3
"""
Query Optimization Service for ATC Position Recommendation Engine

This service provides optimized database queries and connection management
to improve performance and reduce database load.
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, text
from datetime import datetime, timedelta
import asyncio

from ..config import get_config
from ..utils.logging import get_logger_for_module
from ..models import Controller, Flight, Sector, TrafficMovement, AirportConfig

logger = get_logger_for_module(__name__)

class QueryOptimizer:
    """Database query optimization service"""
    
    def __init__(self):
        self.config = get_config()
        self.query_cache = {}
        self.slow_query_threshold = 1.0  # seconds
        
    async def get_active_controllers_optimized(self, db: Session) -> List[Dict[str, Any]]:
        """Get active controllers with optimized query"""
        try:
            # Use eager loading to reduce N+1 queries
            controllers = db.query(Controller).options(
                joinedload(Controller.flights)
            ).filter(
                and_(
                    Controller.status == "online",
                    Controller.last_seen >= datetime.utcnow() - timedelta(minutes=5)
                )
            ).all()
            
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
                    "workload_score": controller.workload_score,
                    "flight_count": len(controller.flights)
                })
            
            return controllers_data
            
        except Exception as e:
            logger.error(f"Error in optimized controllers query: {e}")
            return []
    
    async def get_active_flights_optimized(self, db: Session) -> List[Dict[str, Any]]:
        """Get active flights with optimized query"""
        try:
            # Use eager loading and filtering
            flights = db.query(Flight).options(
                joinedload(Flight.controller),
                joinedload(Flight.sector)
            ).filter(
                and_(
                    Flight.status == "active",
                    Flight.last_updated >= datetime.utcnow() - timedelta(minutes=5)
                )
            ).order_by(desc(Flight.last_updated)).limit(1000).all()
            
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
                    "last_updated": flight.last_updated.isoformat() if flight.last_updated else None,
                    "controller_callsign": flight.controller.callsign if flight.controller else None,
                    "sector_name": flight.sector.name if flight.sector else None
                })
            
            return flights_data
            
        except Exception as e:
            logger.error(f"Error in optimized flights query: {e}")
            return []
    
    async def get_traffic_movements_optimized(
        self, 
        db: Session, 
        airport_icao: str, 
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get traffic movements with optimized query"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Use optimized query with proper indexing
            movements = db.query(TrafficMovement).filter(
                and_(
                    TrafficMovement.airport_icao == airport_icao.upper(),
                    TrafficMovement.timestamp >= cutoff_time
                )
            ).order_by(desc(TrafficMovement.timestamp)).limit(500).all()
            
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
            
            return movements_data
            
        except Exception as e:
            logger.error(f"Error in optimized movements query: {e}")
            return []
    
    async def get_network_stats_optimized(self, db: Session) -> Dict[str, Any]:
        """Get network statistics with optimized queries"""
        try:
            # Use single query with aggregation
            stats = db.query(
                func.count(Controller.id).label('total_controllers'),
                func.count(Flight.id).label('total_flights'),
                func.count(Sector.id).label('total_sectors'),
                func.count(TrafficMovement.id).label('total_movements')
            ).outerjoin(
                Flight, Flight.id.isnot(None)
            ).outerjoin(
                Sector, Sector.id.isnot(None)
            ).outerjoin(
                TrafficMovement, TrafficMovement.id.isnot(None)
            ).filter(
                and_(
                    Controller.status == "online",
                    Flight.status == "active",
                    TrafficMovement.timestamp >= datetime.utcnow() - timedelta(hours=24)
                )
            ).first()
            
            return {
                "controllers_count": stats.total_controllers or 0,
                "flights_count": stats.total_flights or 0,
                "sectors_count": stats.total_sectors or 0,
                "movements_count": stats.total_movements or 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in optimized stats query: {e}")
            return {
                "controllers_count": 0,
                "flights_count": 0,
                "sectors_count": 0,
                "movements_count": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_airport_traffic_summary_optimized(
        self, 
        db: Session, 
        airport_icao: str, 
        days: int = 7
    ) -> Dict[str, Any]:
        """Get airport traffic summary with optimized query"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # Use aggregation query for better performance
            summary = db.query(
                TrafficMovement.airport_icao,
                TrafficMovement.movement_type,
                func.count(TrafficMovement.id).label('count'),
                func.avg(TrafficMovement.confidence).label('avg_confidence'),
                func.avg(TrafficMovement.altitude).label('avg_altitude'),
                func.avg(TrafficMovement.speed).label('avg_speed')
            ).filter(
                and_(
                    TrafficMovement.airport_icao == airport_icao.upper(),
                    TrafficMovement.timestamp >= cutoff_time
                )
            ).group_by(
                TrafficMovement.airport_icao,
                TrafficMovement.movement_type
            ).all()
            
            # Process results
            arrivals = 0
            departures = 0
            total_confidence = 0
            total_count = 0
            
            for row in summary:
                if row.movement_type == "arrival":
                    arrivals = row.count
                else:
                    departures = row.count
                total_count += row.count
                total_confidence += row.avg_confidence * row.count
            
            avg_confidence = total_confidence / total_count if total_count > 0 else 0
            
            return {
                "airport_icao": airport_icao,
                "period_days": days,
                "arrivals": arrivals,
                "departures": departures,
                "total_movements": total_count,
                "avg_confidence": round(avg_confidence, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in optimized airport summary query: {e}")
            return {
                "airport_icao": airport_icao,
                "period_days": days,
                "arrivals": 0,
                "departures": 0,
                "total_movements": 0,
                "avg_confidence": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_sector_workload_optimized(self, db: Session) -> List[Dict[str, Any]]:
        """Get sector workload with optimized query"""
        try:
            # Use subquery for better performance
            sector_workload = db.query(
                Sector.id,
                Sector.name,
                Sector.facility,
                Sector.status,
                func.count(Flight.id).label('flight_count'),
                func.avg(Flight.altitude).label('avg_altitude'),
                func.max(Flight.altitude).label('max_altitude')
            ).outerjoin(
                Flight, Flight.sector_id == Sector.id
            ).filter(
                Flight.status == "active"
            ).group_by(
                Sector.id,
                Sector.name,
                Sector.facility,
                Sector.status
            ).order_by(
                desc(text('flight_count'))
            ).all()
            
            workload_data = []
            for sector in sector_workload:
                workload_data.append({
                    "id": sector.id,
                    "name": sector.name,
                    "facility": sector.facility,
                    "status": sector.status,
                    "flight_count": sector.flight_count or 0,
                    "avg_altitude": round(sector.avg_altitude or 0),
                    "max_altitude": sector.max_altitude or 0,
                    "workload_level": self._calculate_workload_level(sector.flight_count or 0)
                })
            
            return workload_data
            
        except Exception as e:
            logger.error(f"Error in optimized sector workload query: {e}")
            return []
    
    def _calculate_workload_level(self, flight_count: int) -> str:
        """Calculate workload level based on flight count"""
        if flight_count == 0:
            return "low"
        elif flight_count <= 5:
            return "medium"
        elif flight_count <= 15:
            return "high"
        else:
            return "very_high"
    
    async def optimize_database_queries(self, db: Session) -> Dict[str, Any]:
        """Run database optimization tasks"""
        try:
            # Analyze table statistics
            db.execute(text("ANALYZE"))
            
            # Update table statistics
            tables = ["controllers", "flights", "sectors", "traffic_movements"]
            for table in tables:
                db.execute(text(f"ANALYZE {table}"))
            
            # Check for slow queries
            slow_queries = await self._identify_slow_queries(db)
            
            return {
                "status": "optimized",
                "tables_analyzed": len(tables),
                "slow_queries_found": len(slow_queries),
                "optimization_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error optimizing database queries: {e}")
            return {
                "status": "error",
                "error": str(e),
                "optimization_timestamp": datetime.utcnow().isoformat()
            }
    
    async def _identify_slow_queries(self, db: Session) -> List[Dict[str, Any]]:
        """Identify potentially slow queries"""
        try:
            # This would typically query database performance views
            # For now, return empty list as placeholder
            return []
        except Exception as e:
            logger.error(f"Error identifying slow queries: {e}")
            return []

# Global query optimizer instance
_query_optimizer = None

def get_query_optimizer() -> QueryOptimizer:
    """Get or create query optimizer instance"""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    return _query_optimizer 