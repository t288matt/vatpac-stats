#!/usr/bin/env python3
"""
Final API Status Test
Comprehensive endpoint testing without curl
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

class APIFinalTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = []
        
    def test_endpoint(self, endpoint: str, description: str = "") -> Dict[str, Any]:
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            response = requests.get(url, timeout=5)
            response_time = time.time() - start_time
            
            result = {
                "endpoint": endpoint,
                "url": url,
                "status_code": response.status_code,
                "response_time": round(response_time, 3),
                "success": response.status_code == 200,
                "description": description
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        result["response_keys"] = list(data.keys())
                        if "total" in data:
                            result["total_items"] = data["total"]
                        if "status" in data:
                            result["status"] = data["status"]
                except json.JSONDecodeError:
                    result["response_size"] = len(response.content)
            else:
                result["error"] = f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            result = {
                "endpoint": endpoint,
                "url": url,
                "status_code": None,
                "response_time": round(response_time, 3),
                "success": False,
                "error": "Timeout",
                "description": description
            }
        except Exception as e:
            response_time = time.time() - start_time
            result = {
                "endpoint": endpoint,
                "url": url,
                "status_code": None,
                "response_time": round(response_time, 3),
                "success": False,
                "error": str(e),
                "description": description
            }
        
        self.results.append(result)
        return result
    
    def test_all_endpoints(self):
        """Test all API endpoints"""
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
            ("/api/vatsim/ratings", "VATSIM Ratings"),
        ]
        
        for endpoint, description in endpoints:
            self.test_endpoint(endpoint, description)
    
    def print_summary(self):
        """Print comprehensive summary"""
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r["success"]])
        failed_tests = total_tests - successful_tests
        
        print("\n" + "=" * 80)
        print("🎯 FINAL API STATUS SUMMARY")
        print("=" * 80)
        print(f"📊 Overall Status: {successful_tests}/{total_tests} endpoints working")
        print(f"📈 Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Working endpoints
        working = [r for r in self.results if r["success"]]
        if working:
            print("✅ WORKING ENDPOINTS:")
            for result in working:
                status_info = []
                if "total_items" in result:
                    status_info.append(f"Total: {result['total_items']}")
                if "status" in result:
                    status_info.append(f"Status: {result['status']}")
                if "response_time" in result:
                    status_info.append(f"Time: {result['response_time']}s")
                
                print(f"   {result['endpoint']} - {result['description']}")
                if status_info:
                    print(f"      {' | '.join(status_info)}")
            print()
        
        # Failed endpoints
        failed = [r for r in self.results if not r["success"]]
        if failed:
            print("❌ FAILED ENDPOINTS:")
            for result in failed:
                error = result.get("error", "Unknown error")
                print(f"   {result['endpoint']} - {result['description']} ({error})")
            print()
        
        # Performance summary
        response_times = [r["response_time"] for r in self.results if r["response_time"] is not None]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            print(f"⏱️  Performance: Average response time {avg_time:.3f}s")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if successful_tests == total_tests:
            print("   🎉 All endpoints are working perfectly!")
        elif successful_tests > total_tests * 0.7:
            print("   ⚠️  Most endpoints are working. Check the failed ones.")
        else:
            print("   🔧 Several endpoints need attention. Review error logs.")
        
        print(f"\n📋 Test completed without using curl - Pure Python implementation")

def main():
    """Main function"""
    print("🚀 Final API Status Test")
    print("🐍 Pure Python implementation (No curl)")
    print("=" * 60)
    
    tester = APIFinalTester()
    tester.test_all_endpoints()
    tester.print_summary()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"final_api_status_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "test_summary": {
                "total_tests": len(tester.results),
                "successful_tests": len([r for r in tester.results if r["success"]]),
                "failed_tests": len([r for r in tester.results if not r["success"]]),
                "timestamp": datetime.now().isoformat(),
                "method": "python_requests_no_curl"
            },
            "results": tester.results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")

if __name__ == "__main__":
    main() 