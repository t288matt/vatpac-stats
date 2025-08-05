#!/usr/bin/env python3
"""
Test script for VATSIM Health Monitoring System

This script tests the health monitoring endpoints to ensure they're working correctly.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_health_endpoints():
    """Test all health monitoring endpoints"""
    base_url = "http://localhost:8001"
    
    endpoints = [
        "/api/health/comprehensive",
        "/api/health/endpoints", 
        "/api/health/database",
        "/api/health/system",
        "/api/health/data-freshness"
    ]
    
    print("🔍 Testing VATSIM Health Monitoring System")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                print(f"\n📊 Testing {endpoint}")
                start_time = datetime.now()
                
                async with session.get(f"{base_url}{endpoint}", timeout=10) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Status: {response.status} | Response Time: {response_time:.3f}s")
                        
                        # Print key metrics
                        if endpoint == "/api/health/comprehensive":
                            print(f"   Overall Health Score: {data.get('overall_health', 'N/A')}%")
                            print(f"   API Endpoints: {len(data.get('api_endpoints', {}))} checked")
                            print(f"   Database Connected: {data.get('database', {}).get('connected', False)}")
                            
                        elif endpoint == "/api/health/endpoints":
                            healthy_count = sum(1 for ep in data.values() 
                                             if isinstance(ep, dict) and ep.get('healthy', False))
                            print(f"   Healthy Endpoints: {healthy_count}/{len(data)}")
                            
                        elif endpoint == "/api/health/database":
                            print(f"   Connected: {data.get('connected', False)}")
                            print(f"   ATC Positions: {data.get('atc_positions', 0)}")
                            print(f"   Active Flights: {data.get('active_flights', 0)}")
                            
                        elif endpoint == "/api/health/system":
                            print(f"   CPU Usage: {data.get('cpu_percent', 'N/A')}%")
                            print(f"   Memory Usage: {data.get('memory_percent', 'N/A')}%")
                            
                        elif endpoint == "/api/health/data-freshness":
                            print(f"   Data Stale: {data.get('data_stale', True)}")
                            print(f"   ATC Freshness: {data.get('atc_freshness_seconds', 'N/A')}s")
                            print(f"   Flight Freshness: {data.get('flight_freshness_seconds', 'N/A')}s")
                            
                    else:
                        print(f"❌ Status: {response.status} | Response Time: {response_time:.3f}s")
                        error_text = await response.text()
                        print(f"   Error: {error_text}")
                        
            except Exception as e:
                print(f"❌ Error testing {endpoint}: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Health monitoring test completed!")

async def test_individual_endpoints():
    """Test individual API endpoints that are monitored"""
    base_url = "http://localhost:8001"
    
    endpoints = [
        "/api/status",
        "/api/network/status",
        "/api/atc-positions", 
        "/api/flights",
        "/api/database/status",
        "/api/performance/metrics"
    ]
    
    print("\n🔍 Testing Individual API Endpoints")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                print(f"\n📊 Testing {endpoint}")
                start_time = datetime.now()
                
                async with session.get(f"{base_url}{endpoint}", timeout=10) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Status: {response.status} | Response Time: {response_time:.3f}s")
                        
                        # Print relevant data
                        if endpoint == "/api/status":
                            print(f"   ATC Positions: {data.get('atc_positions_count', 0)}")
                            print(f"   Flights: {data.get('flights_count', 0)}")
                            
                        elif endpoint == "/api/network/status":
                            print(f"   Controllers: {data.get('total_controllers', 0)}")
                            print(f"   Flights: {data.get('total_flights', 0)}")
                            
                        elif endpoint == "/api/atc-positions":
                            positions = data.get('atc_positions', [])
                            print(f"   ATC Positions: {len(positions)}")
                            
                        elif endpoint == "/api/flights":
                            flights = data.get('flights', [])
                            print(f"   Flights: {len(flights)}")
                            
                        elif endpoint == "/api/database/status":
                            print(f"   Database: {data.get('database', {}).get('connected', False)}")
                            
                        elif endpoint == "/api/performance/metrics":
                            print(f"   Performance metrics available")
                            
                    else:
                        print(f"❌ Status: {response.status} | Response Time: {response_time:.3f}s")
                        error_text = await response.text()
                        print(f"   Error: {error_text}")
                        
            except Exception as e:
                print(f"❌ Error testing {endpoint}: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Individual endpoint test completed!")

if __name__ == "__main__":
    print("🚁 VATSIM Health Monitoring Test")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_health_endpoints())
    asyncio.run(test_individual_endpoints())
    
    print("\n✅ All tests completed!") 