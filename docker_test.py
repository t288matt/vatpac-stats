#!/usr/bin/env python3
"""
Docker API Testing Script
Tests endpoints within Docker environment without curl
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any

def test_endpoint(url: str, description: str = "") -> Dict[str, Any]:
    """Test a single endpoint"""
    print(f"🔍 Testing: {description}")
    start_time = time.time()
    
    try:
        response = requests.get(url, timeout=15)
        response_time = time.time() - start_time
        
        result = {
            "url": url,
            "status_code": response.status_code,
            "response_time": round(response_time, 3),
            "success": response.status_code == 200,
            "description": description
        }
        
        if response.status_code == 200:
            print(f"✅ {url} - Status: {response.status_code} ({response_time:.3f}s)")
            
            # Try to parse JSON response
            try:
                data = response.json()
                if isinstance(data, dict):
                    result["response_keys"] = list(data.keys())
                    result["response_type"] = "json"
                    if "total" in data:
                        result["total_items"] = data["total"]
                        print(f"   📊 Total items: {data['total']}")
                    if "timestamp" in data:
                        result["timestamp"] = data["timestamp"]
                        print(f"   ⏰ Timestamp: {data['timestamp']}")
                    if "status" in data:
                        print(f"   🟢 Status: {data['status']}")
                else:
                    result["response_type"] = type(data).__name__
                    print(f"   📄 Response type: {type(data).__name__}")
            except json.JSONDecodeError:
                result["response_type"] = "text"
                result["response_size"] = len(response.content)
                print(f"   📄 Response size: {len(response.content)} bytes")
                
        else:
            print(f"❌ {url} - Status: {response.status_code} ({response_time:.3f}s)")
            result["error"] = f"HTTP {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        response_time = time.time() - start_time
        print(f"❌ {url} - Connection failed ({response_time:.3f}s)")
        result = {
            "url": url,
            "status_code": None,
            "response_time": round(response_time, 3),
            "success": False,
            "error": "Connection failed",
            "description": description
        }
    except requests.exceptions.Timeout:
        response_time = time.time() - start_time
        print(f"❌ {url} - Timeout ({response_time:.3f}s)")
        result = {
            "url": url,
            "status_code": None,
            "response_time": round(response_time, 3),
            "success": False,
            "error": "Timeout",
            "description": description
        }
    except Exception as e:
        response_time = time.time() - start_time
        print(f"❌ {url} - Error: {str(e)} ({response_time:.3f}s)")
        result = {
            "url": url,
            "status_code": None,
            "response_time": round(response_time, 3),
            "success": False,
            "error": str(e),
            "description": description
        }
    
    return result

def test_docker_endpoints():
    """Test all endpoints in Docker environment"""
    base_url = "http://localhost:8001"
    
    print("🐳 Docker API Testing")
    print(f"📡 Testing endpoints at: {base_url}")
    print("=" * 60)
    
    endpoints = [
        ("/api/status", "System Status"),
        ("/api/network/status", "Network Status"),
        ("/api/atc-positions", "ATC Positions"),
        ("/api/flights", "Active Flights"),
        ("/api/health/comprehensive", "Health Check"),
        ("/api/health/endpoints", "Endpoint Health"),
        ("/api/health/database", "Database Health"),
        ("/api/health/system", "System Health"),
        ("/api/health/data-freshness", "Data Freshness"),
        ("/api/database/status", "Database Status"),
        ("/api/database/tables", "Database Tables"),
        ("/api/performance/metrics", "Performance Metrics"),
        ("/api/performance/optimize", "Performance Optimization"),
        ("/api/flights/memory", "Flight Memory Usage"),
        ("/api/traffic/movements/KJFK", "Traffic Movements (KJFK)"),
        ("/api/traffic/movements/KLAX", "Traffic Movements (KLAX)"),
        ("/api/traffic/summary/US", "Traffic Summary (US)"),
        ("/api/traffic/trends/KJFK", "Traffic Trends (KJFK)"),
        ("/api/airports/region/US", "Airports (US Region)"),
        ("/api/airports/KJFK/coordinates", "Airport Coordinates (KJFK)"),
        ("/api/airports/KLAX/coordinates", "Airport Coordinates (KLAX)"),
        ("/api/vatsim/ratings", "VATSIM Ratings"),
        ("/traffic-dashboard", "Traffic Dashboard"),
    ]
    
    results = []
    
    for endpoint, description in endpoints:
        url = f"{base_url}{endpoint}"
        result = test_endpoint(url, description)
        results.append(result)
        print()  # Empty line for readability
    
    return results

def print_summary(results):
    """Print test summary"""
    total_tests = len(results)
    successful_tests = len([r for r in results if r["success"]])
    failed_tests = total_tests - successful_tests
    
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print(f"\n❌ Failed Tests:")
        for result in results:
            if not result["success"]:
                print(f"  {result['url']} - {result.get('error', 'Unknown error')}")
    
    # Performance analysis
    response_times = [r["response_time"] for r in results if r["response_time"] is not None]
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"\n⏱️  Performance:")
        print(f"  Average Response Time: {avg_time:.3f}s")
        print(f"  Fastest: {min_time:.3f}s")
        print(f"  Slowest: {max_time:.3f}s")
    
    # Success rate by endpoint type
    health_endpoints = [r for r in results if "health" in r["url"]]
    api_endpoints = [r for r in results if "/api/" in r["url"] and "health" not in r["url"]]
    dashboard_endpoints = [r for r in results if "dashboard" in r["url"]]
    
    if health_endpoints:
        health_success = len([r for r in health_endpoints if r["success"]])
        print(f"\n🏥 Health Endpoints: {health_success}/{len(health_endpoints)} successful")
    
    if api_endpoints:
        api_success = len([r for r in api_endpoints if r["success"]])
        print(f"🔌 API Endpoints: {api_success}/{len(api_endpoints)} successful")
    
    if dashboard_endpoints:
        dashboard_success = len([r for r in dashboard_endpoints if r["success"]])
        print(f"📊 Dashboard Endpoints: {dashboard_success}/{len(dashboard_endpoints)} successful")

def main():
    """Main function"""
    print("🚀 Starting Docker API Testing...")
    print("🐳 Testing within Docker environment")
    print("=" * 60)
    
    # Test all endpoints
    results = test_docker_endpoints()
    
    # Print summary
    print_summary(results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"docker_api_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "test_summary": {
                "total_tests": len(results),
                "successful_tests": len([r for r in results if r["success"]]),
                "failed_tests": len([r for r in results if not r["success"]]),
                "timestamp": datetime.now().isoformat(),
                "environment": "docker"
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")
    
    # Final status
    successful_tests = len([r for r in results if r["success"]])
    total_tests = len(results)
    
    if successful_tests == total_tests:
        print("\n🎉 All tests passed! API is working correctly.")
    elif successful_tests > total_tests * 0.8:
        print(f"\n⚠️  {successful_tests}/{total_tests} tests passed. API is mostly working.")
    else:
        print(f"\n❌ Only {successful_tests}/{total_tests} tests passed. API needs attention.")

if __name__ == "__main__":
    main() 