#!/usr/bin/env python3
"""
Comprehensive API Endpoint Testing Script
Tests all endpoints without using curl
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

class APITester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def test_endpoint(self, method: str, endpoint: str, expected_status: int = 200, 
                     data: Optional[Dict] = None, description: str = "") -> Dict[str, Any]:
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=10)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, timeout=10)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = time.time() - start_time
            success = response.status_code == expected_status
            
            result = {
                "method": method,
                "endpoint": endpoint,
                "url": url,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": success,
                "response_time": round(response_time, 3),
                "description": description,
                "timestamp": datetime.now().isoformat()
            }
            
            # Try to parse JSON response
            try:
                result["response_data"] = response.json()
                result["response_size"] = len(response.content)
            except json.JSONDecodeError:
                result["response_data"] = response.text
                result["response_size"] = len(response.content)
            
            if not success:
                result["error"] = f"Expected {expected_status}, got {response.status_code}"
            
            print(f"{'✅' if success else '❌'} {method} {endpoint} ({response.status_code}) - {response_time:.3f}s")
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            result = {
                "method": method,
                "endpoint": endpoint,
                "url": url,
                "status_code": None,
                "expected_status": expected_status,
                "success": False,
                "response_time": round(response_time, 3),
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            print(f"❌ {method} {endpoint} (ERROR) - {response_time:.3f}s - {str(e)}")
        
        self.results.append(result)
        return result
    
    def test_all_endpoints(self):
        """Test all API endpoints"""
        print("🚀 Starting comprehensive API endpoint testing...")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 80)
        
        # Core status endpoints
        self.test_endpoint("GET", "/api/status", description="System status endpoint")
        self.test_endpoint("GET", "/api/network/status", description="Network status endpoint")
        
        # ATC endpoints
        self.test_endpoint("GET", "/api/atc-positions", description="Active ATC positions")
        self.test_endpoint("GET", "/api/atc-positions/by-controller-id", description="ATC positions by controller ID")
        self.test_endpoint("GET", "/api/vatsim/ratings", description="VATSIM ratings")
        
        # Flight endpoints
        self.test_endpoint("GET", "/api/flights", description="Active flights")
        self.test_endpoint("GET", "/api/flights/memory", description="Flight memory usage")
        
        # Traffic endpoints
        self.test_endpoint("GET", "/api/traffic/movements/KJFK", description="Traffic movements for KJFK")
        self.test_endpoint("GET", "/api/traffic/movements/KLAX", description="Traffic movements for KLAX")
        self.test_endpoint("GET", "/api/traffic/summary/US", description="Traffic summary for US region")
        self.test_endpoint("GET", "/api/traffic/trends/KJFK", description="Traffic trends for KJFK")
        self.test_endpoint("GET", "/api/traffic/trends/KLAX", description="Traffic trends for KLAX")
        
        # Airport endpoints
        self.test_endpoint("GET", "/api/airports/region/US", description="Airports in US region")
        self.test_endpoint("GET", "/api/airports/KJFK/coordinates", description="KJFK coordinates")
        self.test_endpoint("GET", "/api/airports/KLAX/coordinates", description="KLAX coordinates")
        
        # Database endpoints
        self.test_endpoint("GET", "/api/database/status", description="Database status")
        self.test_endpoint("GET", "/api/database/tables", description="Database tables")
        self.test_endpoint("POST", "/api/database/query", 
                          data={"query": "SELECT COUNT(*) FROM flights"}, 
                          description="Database query endpoint")
        
        # Performance endpoints
        self.test_endpoint("GET", "/api/performance/metrics", description="Performance metrics")
        self.test_endpoint("GET", "/api/performance/optimize", description="Performance optimization")
        
        # Health check endpoints
        self.test_endpoint("GET", "/api/health/comprehensive", description="Comprehensive health check")
        self.test_endpoint("GET", "/api/health/endpoints", description="Endpoint health check")
        self.test_endpoint("GET", "/api/health/database", description="Database health check")
        self.test_endpoint("GET", "/api/health/system", description="System health check")
        self.test_endpoint("GET", "/api/health/data-freshness", description="Data freshness check")
        
        # Dashboard endpoints
        self.test_endpoint("GET", "/traffic-dashboard", description="Traffic dashboard")
        
        # Test with invalid endpoints to check error handling
        self.test_endpoint("GET", "/api/nonexistent", expected_status=404, description="Non-existent endpoint")
        self.test_endpoint("GET", "/api/flights/invalid", expected_status=404, description="Invalid flights endpoint")
        
        print("\n" + "=" * 80)
        self.print_summary()
        
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - successful_tests
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"   {result['method']} {result['endpoint']} - {result.get('error', 'Unknown error')}")
        
        # Performance analysis
        response_times = [r["response_time"] for r in self.results if r["response_time"] is not None]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            print(f"\n⏱️  Performance Analysis:")
            print(f"   Average Response Time: {avg_response_time:.3f}s")
            print(f"   Fastest Response: {min_response_time:.3f}s")
            print(f"   Slowest Response: {max_response_time:.3f}s")
        
        # Save results to file
        self.save_results()
    
    def save_results(self):
        """Save test results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "test_summary": {
                    "total_tests": len(self.results),
                    "successful_tests": len([r for r in self.results if r["success"]]),
                    "failed_tests": len([r for r in self.results if not r["success"]]),
                    "timestamp": datetime.now().isoformat(),
                    "base_url": self.base_url
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n💾 Test results saved to: {filename}")
    
    def test_specific_endpoint(self, method: str, endpoint: str, data: Optional[Dict] = None):
        """Test a specific endpoint with detailed output"""
        print(f"\n🔍 Testing specific endpoint: {method} {endpoint}")
        result = self.test_endpoint(method, endpoint, data=data)
        
        print(f"\n📋 Detailed Results:")
        print(f"   URL: {result['url']}")
        print(f"   Status Code: {result['status_code']}")
        print(f"   Response Time: {result['response_time']}s")
        print(f"   Success: {result['success']}")
        
        if "response_data" in result:
            if isinstance(result["response_data"], dict):
                print(f"   Response Keys: {list(result['response_data'].keys())}")
                if "total" in result["response_data"]:
                    print(f"   Total Items: {result['response_data']['total']}")
                if "timestamp" in result["response_data"]:
                    print(f"   Timestamp: {result['response_data']['timestamp']}")
            else:
                print(f"   Response Type: {type(result['response_data'])}")
                print(f"   Response Size: {result['response_size']} bytes")
        
        if "error" in result:
            print(f"   Error: {result['error']}")
        
        return result

def main():
    """Main function to run the API tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test VATSIM Data API endpoints")
    parser.add_argument("--base-url", default="http://localhost:8001", 
                       help="Base URL for the API (default: http://localhost:8001)")
    parser.add_argument("--endpoint", help="Test a specific endpoint (e.g., GET /api/status)")
    parser.add_argument("--method", default="GET", help="HTTP method for specific endpoint test")
    parser.add_argument("--data", help="JSON data for POST/PUT requests")
    
    args = parser.parse_args()
    
    tester = APITester(args.base_url)
    
    try:
        if args.endpoint:
            # Test specific endpoint
            data = None
            if args.data:
                try:
                    data = json.loads(args.data)
                except json.JSONDecodeError:
                    print("❌ Invalid JSON data provided")
                    sys.exit(1)
            
            tester.test_specific_endpoint(args.method, args.endpoint, data)
        else:
            # Test all endpoints
            tester.test_all_endpoints()
            
    except KeyboardInterrupt:
        print("\n⏹️  Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 