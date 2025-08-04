#!/usr/bin/env python3
"""
Generate Dashboard Queries Script

This script generates SQL queries for Grafana dashboards using the airport configuration
instead of hardcoded airport lists.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "app"))

from app.config.airport_config import get_australian_airports_sql_list, get_major_australian_airports_sql_list

def generate_dashboard_queries():
    """Generate SQL queries for dashboard templates"""
    
    # Get airport lists
    all_australian_airports = get_australian_airports_sql_list()
    major_australian_airports = get_major_australian_airports_sql_list()
    
    # Template queries
    queries = {
        "australian_flights_by_date_7_days": f"""
SELECT
  DATE(created_at) as time,
  COUNT(*) as flights
FROM flights
WHERE (departure IN ({all_australian_airports}) 
    OR arrival IN ({all_australian_airports}))
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY time
""",
        
        "australian_flights_by_date_30_days": f"""
SELECT
  DATE(created_at) as time,
  COUNT(*) as flights
FROM flights
WHERE (departure IN ({all_australian_airports}) 
    OR arrival IN ({all_australian_airports}))
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY time
""",
        
        "top_australian_departure_airports": f"""
SELECT
  COALESCE(departure, 'Unknown') as airport,
  COUNT(*) as flights
FROM flights
WHERE departure IN ({all_australian_airports})
  AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY departure
ORDER BY flights DESC
LIMIT 10
""",
        
        "top_australian_arrival_airports": f"""
SELECT
  COALESCE(arrival, 'Unknown') as airport,
  COUNT(*) as flights
FROM flights
WHERE arrival IN ({all_australian_airports})
  AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY arrival
ORDER BY flights DESC
LIMIT 10
""",
        
        "top_australian_routes": f"""
SELECT
  CONCAT(departure, ' → ', arrival) as route,
  COUNT(*) as flights
FROM flights
WHERE (departure IN ({all_australian_airports}) 
    OR arrival IN ({all_australian_airports}))
  AND departure IS NOT NULL
  AND arrival IS NOT NULL
  AND departure != arrival
  AND departure != ''
  AND arrival != ''
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY departure, arrival
HAVING COUNT(*) >= 1
ORDER BY flights DESC, route ASC
LIMIT 15
""",
        
        "australian_aircraft_types": f"""
SELECT
  aircraft_type,
  COUNT(*) as flights
FROM flights
WHERE (departure IN ({all_australian_airports}) 
    OR arrival IN ({all_australian_airports}))
  AND aircraft_type IS NOT NULL
  AND aircraft_type != ''
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY aircraft_type
ORDER BY flights DESC
LIMIT 10
""",
        
        "unique_australian_routes": f"""
SELECT
  DATE(created_at) as time,
  COUNT(DISTINCT CONCAT(departure, ' → ', arrival)) as unique_routes
FROM flights
WHERE (departure IN ({all_australian_airports}) 
    OR arrival IN ({all_australian_airports}))
  AND departure IS NOT NULL
  AND arrival IS NOT NULL
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY time
""",
        
        "australian_airports_by_destinations": f"""
SELECT
  departure as origin,
  COUNT(DISTINCT arrival) as destinations
FROM flights
WHERE departure IN ({all_australian_airports})
  AND arrival IS NOT NULL
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY departure
ORDER BY destinations DESC
LIMIT 10
""",
        
        "australian_airports_by_origins": f"""
SELECT
  arrival as destination,
  COUNT(DISTINCT departure) as origins
FROM flights
WHERE arrival IN ({all_australian_airports})
  AND departure IS NOT NULL
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY arrival
ORDER BY origins DESC
LIMIT 10
""",
        
        "major_airport_trends": f"""
SELECT
  DATE(created_at) as time,
  COUNT(*) as flights
FROM flights
WHERE departure = 'YBBN' OR arrival = 'YBBN'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY time
"""
    }
    
    return queries

def print_queries():
    """Print all generated queries"""
    queries = generate_dashboard_queries()
    
    print("Generated SQL Queries for Grafana Dashboards")
    print("=" * 50)
    
    for query_name, query in queries.items():
        print(f"\n-- {query_name}")
        print(query.strip())
        print()

if __name__ == "__main__":
    print_queries() 