#!/usr/bin/env python3
"""
Pure Python API Testing Script
No curl - only Python libraries
"""

import requests
import urllib.request
import urllib.error
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any

def test_with_requests(url: str, description: str = "") -> Dict[str, Any]:
    """Test endpoint using requests library"""
    print(f"🔍 Testing with requests: {description}")
    start_time = time.time()
    
    try:
        response = requests.get(url, timeout=10)
        response_time = time.time() - start_time
        
        result = {
            "library": "requests",
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
                    if "timestamp" in data:
                        result["timestamp"] = data["timestamp"]
                else:
                    result["response_type"] = type(data).__name__
            except json.JSONDecodeError:
                result["response_type"] = "text"
                result["response_size"] = len(response.content)
                
        else:
            print(f"❌ {url} - Status: {response.status_code} ({response_time:.3f}s)")
            result["error"] = f"HTTP {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        response_time = time.time() - start_time
        print(f"❌ {url} - Connection failed ({response_time:.3f}s)")
        result = {
            "library": "requests",
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
            "library": "requests",
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
            "library": "requests",
            "url": url,
            "status_code": None,
            "response_time": round(response_time, 3),
            "success": False,
            "error": str(e),
            "description": description
        }
    
    return result

def test_with_urllib(url: str, description: str = "") -> Dict[str, Any]:
    """Test endpoint using urllib library"""
    print(f"🔍 Testing with urllib: {description}")
    start_time = time.time()
    
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Python-API-Tester/1.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            response_time = time.time() - start_time
            data = response.read()
            
            result = {
                "library": "urllib",
                "url": url,
                "status_code": response.getcode(),
                "response_time": round(response_time, 3),
                "success": response.getcode() == 200,
                "description": description,
                "response_size": len(data)
            }
            
            if response.getcode() == 200:
                print(f"✅ {url} - Status: {response.getcode()} ({response_time:.3f}s)")
                
                # Try to parse JSON
                try:
                    json_data = json.loads(data.decode('utf-8'))
                    if isinstance(json_data, dict):
                        result["response_keys"] = list(json_data.keys())
                        result["response_type"] = "json"
                        if "total" in json_data:
                            result["total_items"] = json_data["total"]
                        if "timestamp" in json_data:
                            result["timestamp"] = json_data["timestamp"]
                    else:
                        result["response_type"] = type(json_data).__name__
                except json.JSONDecodeError:
                    result["response_type"] = "text"
                    
            else:
                print(f"❌ {url} - Status: {response.getcode()} ({response_time:.3f}s)")
                result["error"] = f"HTTP {response.getcode()}"
                
    except urllib.error.URLError as e:
        response_time = time.time() - start_time
        print(f"❌ {url} - URLError: {str(e)} ({response_time:.3f}s)")
        result = {
            "library": "urllib",
            "url": url,
            "status_code": None,
            "response_time": round(response_time, 3),
            "success": False,
            "error": str(e),
            "description": description
        }
    except Exception as e:
        response_time = time.time() - start_time
        print(f"❌ {url} - Error: {str(e)} ({response_time:.3f}s)")
        result = {
            "library": "urllib",
            "url": url,
            "status_code": None,
            "response_time": round(response_time, 3),
            "success": False,
            "error": str(e),
            "description": description
        }
    
    return result

def test_server_health(base_url: str = "http://localhost:8001"):
    """Test if server is running and healthy"""
    print("🏥 Testing server health...")
    
    # Test basic connectivity
    health_url = f"{base_url}/api/health/comprehensive"
    result = test_with_requests(health_url, "Server Health Check")
    
    if result["success"]:
        print("✅ Server is healthy and responding")
        return True
    else:
        print("❌ Server health check failed")
        return False

def test_all_endpoints(base_url: str = "http://localhost:8001"):
    """Test all API endpoints"""
    print(f"\n🚀 Testing all endpoints at: {base_url}")
    print("=" * 60)
    
    endpoints = [
        ("/api/status", "System Status"),
        ("/api/network/status", "Network Status"),
        ("/api/atc-positions", "ATC Positions"),
        ("/api/flights", "Active Flights"),
        ("/api/health/comprehensive", "Health Check"),
        ("/api/database/status", "Database Status"),
        ("/api/performance/metrics", "Performance Metrics"),
        ("/api/traffic/movements/KJFK", "Traffic Movements (KJFK)"),
        ("/api/airports/KJFK/coordinates", "Airport Coordinates (KJFK)"),
    ]
    
    results = []
    
    for endpoint, description in endpoints:
        url = f"{base_url}{endpoint}"
        
        # Test with both libraries
        requests_result = test_with_requests(url, description)
        urllib_result = test_with_urllib(url, description)
        
        results.extend([requests_result, urllib_result])
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
                print(f"  {result['library']} - {result['url']} - {result.get('error', 'Unknown error')}")
    
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

def main():
    """Main function"""
    base_url = "http://localhost:8001"
    
    print("🐍 Pure Python API Testing (No curl)")
    print(f"📡 Base URL: {base_url}")
    print("=" * 60)
    
    # First check if server is running
    if not test_server_health(base_url):
        print("\n❌ Server appears to be down. Please start the server first:")
        print("   python3 run.py")
        sys.exit(1)
    
    # Test all endpoints
    results = test_all_endpoints(base_url)
    
    # Print summary
    print_summary(results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"python_api_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "test_summary": {
                "total_tests": len(results),
                "successful_tests": len([r for r in results if r["success"]]),
                "failed_tests": len([r for r in results if not r["success"]]),
                "timestamp": datetime.now().isoformat(),
                "base_url": base_url
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")

if __name__ == "__main__":
    main() 