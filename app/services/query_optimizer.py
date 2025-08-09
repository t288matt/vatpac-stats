#!/usr/bin/env python3
"""
Query Optimization Service for VATSIM Data Collection System

This service provides optimized database queries and connection management
to improve performance and reduce database load. It implements query optimization
techniques including eager loading, query caching, and performance monitoring.

INPUTS:
- Database session objects
- Query parameters and filters
- Performance thresholds and monitoring data
- Query optimization requests

OUTPUTS:
- Optimized query results with eager loading
- Performance metrics and monitoring data
- Query optimization recommendations
- Database performance analysis

OPTIMIZATION TECHNIQUES:
- Eager loading to reduce N+1 queries
- Query result caching
- Index-aware query construction
- Connection pooling optimization
- Query performance monitoring

QUERY TYPES:
- Active ATC positions with flight counts
- Active flights with position data
- Traffic movements by airport
- Network statistics and summaries
- Sector workload analysis
- Airport traffic summaries

PERFORMANCE FEATURES:
- Slow query detection and logging
- Query execution time monitoring
- Connection pool health checks
- Query result size optimization
- Automatic query optimization suggestions

MONITORING:
- Query execution time tracking
- Connection pool utilization
- Query result caching efficiency
- Database load analysis
- Performance bottleneck identification

OPTIMIZATIONS:
- Eager loading for related data
- Query result limiting
- Index-optimized filtering
- Connection reuse
- Query plan analysis
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, text
from datetime import datetime, timezone, timedelta, timezone
import asyncio

from ..config import get_config
from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation, create_error_handler
from ..utils.exceptions import DatabaseError, DataProcessingError
from ..models import Controller, Flight, Sector, TrafficMovement, AirportConfig

class QueryOptimizer:
    """Database query optimization service"""
    
    def __init__(self):
        self.config = get_config()
        self.error_handler = create_error_handler("query_optimizer")
        self.query_cache = {}
        self.slow_query_threshold = 1.0  # seconds
        
    @handle_service_errors
    @log_operation("get_active_atc_positions_optimized")
    async def get_active_atc_positions_optimized(self, db: Session) -> List[Dict[str, Any]]:
        """Get active ATC positions with optimized query"""
        try:
            # Use eager loading to reduce N+1 queries
            atc_positions = db.query(Controller).options(
                joinedload(Controller.flights)
            ).filter(
                and_(
                    Controller.status == "online",
                    Controller.last_seen >= datetime.now(timezone.utc) - timedelta(minutes=5)
                )
            ).all()
            
            atc_positions_data = []
            for atc_position in atc_positions:
                atc_positions_data.append({
                    "id": atc_position.id,
                    "callsign": atc_position.callsign,
                    "facility": atc_position.facility,
                    "position": atc_position.position,
                    "status": atc_position.status,
                    "frequency": atc_position.frequency,
                    "last_seen": atc_position.last_seen.isoformat() if atc_position.last_seen else None,
                    "workload_score": atc_position.workload_score,
                    "flight_count": len(atc_position.flights)
                })
            
            logger.info(f"Retrieved {len(atc_positions_data)} active ATC positions")
            return atc_positions_data
            
        except Exception as e:
            self.error_handler.logger.error(f"Error in optimized ATC positions query: {e}")
            # Return empty list only on actual errors, not when no data is found
            return []
    
    @handle_service_errors
    @log_operation("get_active_flights_optimized")
    async def get_active_flights_optimized(self, db: Session) -> List[Dict[str, Any]]:
        """Get active flights with optimized query"""
        try:
            # Use eager loading and filtering (status column removed)
            flights = db.query(Flight).options(
                joinedload(Flight.atc_position),
                joinedload(Flight.sector)
            ).filter(
                Flight.last_updated >= datetime.now(timezone.utc) - timedelta(minutes=5)
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
                    "groundspeed": flight.groundspeed,
                    "cruise_tas": flight.cruise_tas,
                    "position": flight.position,
                    "last_updated": flight.last_updated.isoformat() if flight.last_updated else None,
                    "atc_position_callsign": flight.atc_position.callsign if flight.atc_position else None,
                    "sector_name": flight.sector.name if flight.sector else None
                })
            
            logger.info(f"Retrieved {len(flights_data)} active flights")
            return flights_data
            
        except Exception as e:
            self.error_handler.logger.error(f"Error in optimized flights query: {e}")
            # Return empty list only on actual errors, not when no data is found
            return []
    
    @handle_service_errors
    @log_operation("get_traffic_movements_optimized")
    async def get_traffic_movements_optimized(
        self, 
        db: Session, 
        airport_icao: str, 
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get traffic movements with optimized query"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Use optimized query with proper indexing
            movements = db.query(TrafficMovement).filter(
                and_(
                    TrafficMovement.airport_code == airport_icao.upper(),
                    TrafficMovement.timestamp >= cutoff_time
                )
            ).order_by(desc(TrafficMovement.timestamp)).limit(500).all()
            
            movements_data = []
            for movement in movements:
                movements_data.append({
                    "id": movement.id,
                    "airport_code": movement.airport_code,
                    "aircraft_callsign": movement.aircraft_callsign,
                    "movement_type": movement.movement_type,
                    "timestamp": movement.timestamp.isoformat() if movement.timestamp else None,
                    "altitude": movement.altitude,
                    "heading": movement.heading
                })
            
            logger.info(f"Retrieved {len(movements_data)} traffic movements for {airport_icao}")
            return movements_data
            
        except Exception as e:
            self.error_handler.logger.error(f"Error in optimized traffic movements query: {e}")
            # Return empty list only on actual errors, not when no data is found
            return []
    
    @handle_service_errors
    @log_operation("get_network_stats_optimized")
    async def get_network_stats_optimized(self, db: Session) -> Dict[str, Any]:
        """Get network statistics with optimized queries"""
        try:
            # Use single query with aggregation
            stats = db.query(
                func.count(Controller.id).label('total_atc_positions'),
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
                    TrafficMovement.timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)
                )
            ).first()
            
            return {
                "atc_positions_count": stats.total_atc_positions or 0,
                "flights_count": stats.total_flights or 0,
                "sectors_count": stats.total_sectors or 0,
                "movements_count": stats.total_movements or 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.error_handler.logger.error(f"Error in optimized stats query: {e}")
            return {
                "atc_positions_count": 0,
                "flights_count": 0,
                "sectors_count": 0,
                "movements_count": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @handle_service_errors
    @log_operation("get_airport_traffic_summary_optimized")
    async def get_airport_traffic_summary_optimized(
        self, 
        db: Session, 
        airport_icao: str, 
        days: int = 7
    ) -> Dict[str, Any]:
        """Get airport traffic summary with optimized query"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Use aggregation query for better performance
            summary = db.query(
                TrafficMovement.airport_code,
                TrafficMovement.movement_type,
                func.count(TrafficMovement.id).label('count'),
                func.avg(TrafficMovement.altitude).label('avg_altitude')
            ).filter(
                and_(
                    TrafficMovement.airport_code == airport_icao.upper(),
                    TrafficMovement.timestamp >= cutoff_time
                )
            ).group_by(
                TrafficMovement.airport_code,
                TrafficMovement.movement_type
            ).all()
            
            # Process results
            arrivals = 0
            departures = 0
            total_altitude = 0
            total_count = 0
            
            for row in summary:
                if row.movement_type == "arrival":
                    arrivals = row.count
                else:
                    departures = row.count
                total_count += row.count
                total_altitude += (row.avg_altitude or 0) * row.count
            
            avg_altitude = total_altitude / total_count if total_count > 0 else 0
            
            logger.info(f"Retrieved traffic summary for {airport_icao}: {arrivals} arrivals, {departures} departures")
            
            return {
                "airport_icao": airport_icao,
                "arrivals": arrivals,
                "departures": departures,
                "total_movements": total_count,
                "avg_altitude": round(avg_altitude, 2),
                "period_days": days,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.error_handler.logger.error(f"Error in optimized airport traffic summary query: {e}")
            return {
                "airport_icao": airport_icao,
                "arrivals": 0,
                "departures": 0,
                "total_movements": 0,
                "avg_altitude": 0,
                "period_days": days,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    @handle_service_errors
    @log_operation("get_sector_workload_optimized")
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
            self.error_handler.logger.error(f"Error in optimized sector workload query: {e}")
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
    
    @handle_service_errors
    @log_operation("optimize_database_queries")
    async def optimize_database_queries(self, db: Session) -> Dict[str, Any]:
        """Run database optimization tasks"""
        try:
            # Analyze table statistics
            db.execute(text("ANALYZE"))
            
            # Update table statistics
            tables = ["atc_positions", "flights", "sectors", "traffic_movements"]
            for table in tables:
                db.execute(text(f"ANALYZE {table}"))
            
            # Check for slow queries
            slow_queries = await self._identify_slow_queries(db)
            
            return {
                "status": "optimized",
                "tables_analyzed": len(tables),
                "slow_queries_found": len(slow_queries),
                "optimization_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.error_handler.logger.error(f"Error optimizing database queries: {e}")
            return {
                "status": "error",
                "error": str(e),
                "optimization_timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @handle_service_errors
    @log_operation("identify_slow_queries")
    async def _identify_slow_queries(self, db: Session) -> List[Dict[str, Any]]:
        """Identify potentially slow queries using PostgreSQL performance views"""
        try:
            # Query PostgreSQL's pg_stat_statements to identify slow queries
            # This requires the pg_stat_statements extension to be enabled
            slow_queries = []
            
            # Check if pg_stat_statements extension is available
            try:
                result = db.execute(text("""
                    SELECT 
                        query,
                        calls,
                        total_time,
                        mean_time,
                        rows
                    FROM pg_stat_statements 
                    WHERE mean_time > 100  -- Queries taking more than 100ms on average
                    ORDER BY mean_time DESC 
                    LIMIT 10
                """))
                
                for row in result:
                    slow_queries.append({
                        "query": row.query[:200] + "..." if len(row.query) > 200 else row.query,
                        "calls": row.calls,
                        "total_time_ms": round(row.total_time, 2),
                        "mean_time_ms": round(row.mean_time, 2),
                        "rows_affected": row.rows
                    })
                    
            except Exception as e:
                # If pg_stat_statements is not available, use alternative approach
                logger.warning(f"pg_stat_statements not available: {e}")
                
                # Alternative: Check for queries that might be slow based on table statistics
                slow_queries = await self._identify_potential_slow_queries(db)
            
            return slow_queries
            
        except Exception as e:
            self.error_handler.logger.error(f"Error identifying slow queries: {e}")
            return []
    
    @handle_service_errors
    @log_operation("identify_potential_slow_queries")
    async def _identify_potential_slow_queries(self, db: Session) -> List[Dict[str, Any]]:
        """Identify potentially slow queries using table statistics"""
        try:
            potential_slow_queries = []
            
            # Check for tables with high row counts that might cause slow queries
            result = db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables 
                WHERE n_live_tup > 10000  -- Tables with more than 10k rows
                ORDER BY n_live_tup DESC
            """))
            
            for row in result:
                potential_slow_queries.append({
                    "table": f"{row.schemaname}.{row.tablename}",
                    "live_rows": row.live_rows,
                    "dead_rows": row.dead_rows,
                    "inserts": row.inserts,
                    "updates": row.updates,
                    "deletes": row.deletes,
                    "recommendation": "Consider adding indexes or cleaning up dead rows"
                })
            
            return potential_slow_queries
            
        except Exception as e:
            self.error_handler.logger.error(f"Error identifying potential slow queries: {e}")
            return []

# Global query optimizer instance
_query_optimizer = None

def get_query_optimizer() -> QueryOptimizer:
    """Get or create query optimizer instance"""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    return _query_optimizer 
