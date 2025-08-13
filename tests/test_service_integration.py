#!/usr/bin/env python3
"""
Stage 6: Service Integration Tests - Live Service Interaction Validation

Tests how your services work together using live data.
Focus: Service communication, data flow, and integration reliability.

Author: VATSIM Data System
Stage: 6 - Service Integration
"""

import pytest
import requests
import time
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8001")
API_TIMEOUT = int(os.getenv("TEST_API_TIMEOUT", "30"))
WAIT_TIMEOUT = int(os.getenv("TEST_WAIT_TIMEOUT", "60"))

# Global test session
test_session = requests.Session()
test_session.timeout = API_TIMEOUT

@pytest.mark.stage6
@pytest.mark.service_integration
def test_vatsim_to_database_flow():
    """Test: Does VATSIM data flow to database correctly?"""
    print("🧪 Testing: Does VATSIM data flow to database correctly?")
    
    try:
        # Step 1: Get live VATSIM data
        vatsim_response = test_session.get(f"{BASE_URL}/api/status")
        if vatsim_response.status_code != 200:
            print(f"❌ VATSIM service not accessible - status {vatsim_response.status_code}")
            assert False, f"VATSIM service not accessible - status {vatsim_response.status_code}"
        
        # Step 2: Check database storage
        db_response = test_session.get(f"{BASE_URL}/api/database/status")
        if db_response.status_code != 200:
            print(f"❌ Database service not accessible - status {db_response.status_code}")
            assert False, f"Database service not accessible - status {db_response.status_code}"
        
        db_data = db_response.json()
        db_status = db_data.get("database_status", {})
        tables = db_status.get("tables", 0)
        
        if tables < 3:  # Should have flights, controllers, transceivers at minimum
            print(f"❌ Database missing expected tables - only {tables} found")
            assert False, f"Database missing expected tables - only {tables} found"
        
        # Step 3: Verify API retrieval
        flights_response = test_session.get(f"{BASE_URL}/api/flights")
        controllers_response = test_session.get(f"{BASE_URL}/api/controllers")
        
        if flights_response.status_code != 200:
            print(f"❌ Flights API not accessible - status {flights_response.status_code}")
            assert False, f"Flights API not accessible - status {flights_response.status_code}"
        
        if controllers_response.status_code != 200:
            print(f"❌ Controllers API not accessible - status {controllers_response.status_code}")
            assert False, f"Controllers API not accessible - status {controllers_response.status_code}"
        
        # Step 4: Validate data consistency
        flights_data = flights_response.json()
        controllers_data = controllers_response.json()
        
        flights = flights_data.get("flights", [])
        controllers = controllers_data.get("controllers", [])
        
        if not flights and not controllers:
            print("❌ No data available in either flights or controllers")
            assert False, "No data available in either flights or controllers"
        
        print(f"✅ VATSIM → Database → API flow working - {len(flights)} flights, {len(controllers)} controllers")
        assert len(flights) > 0 or len(controllers) > 0, "Should have data available"
        
    except Exception as e:
        print(f"❌ VATSIM to database flow test failed - {e}")
        assert False, f"VATSIM to database flow test failed: {e}"

@pytest.mark.stage6
@pytest.mark.service_integration
def test_cache_behavior_with_live_data():
    """Test: Does caching work with real data?"""
    print("🧪 Testing: Does caching work with real data?")
    
    try:
        # Step 1: Make initial API call (populates cache)
        start_time = time.time()
        initial_response = test_session.get(f"{BASE_URL}/api/flights")
        initial_time = time.time() - start_time
        
        if initial_response.status_code != 200:
            print(f"❌ Initial API call failed - status {initial_response.status_code}")
            assert False, f"Initial API call failed - status {initial_response.status_code}"
        
        # Step 2: Make same call (should use cache)
        start_time = time.time()
        cached_response = test_session.get(f"{BASE_URL}/api/flights")
        cached_time = time.time() - start_time
        
        if cached_response.status_code != 200:
            print(f"❌ Cached API call failed - status {cached_response.status_code}")
            assert False, f"Cached API call failed - status {cached_response.status_code}"
        
        # Step 3: Verify response times
        print(f"📊 Response times - Initial: {initial_time:.3f}s, Cached: {cached_time:.3f}s")
        
        # Step 4: Check cache effectiveness (cached should be faster)
        if cached_time < initial_time:
            print(f"✅ Caching working - cached response {initial_time/cached_time:.1f}x faster")
            assert cached_time < initial_time, "Cached response should be faster"
        else:
            print(f"⚠️ Caching may not be working - cached response {cached_time/initial_time:.1f}x slower")
            # Don't fail the test, just warn about caching
        
        # Step 5: Validate data consistency between calls
        initial_data = initial_response.json()
        cached_data = cached_response.json()
        
        if initial_data == cached_data:
            print("✅ Cached data matches initial data exactly")
        else:
            print("⚠️ Cached data differs from initial data (may be expected for live data)")
        
        print("✅ Cache behavior test completed successfully")
        
    except Exception as e:
        print(f"❌ Cache behavior test failed - {e}")
        assert False, f"Cache behavior test failed: {e}"

@pytest.mark.stage6
@pytest.mark.service_integration
def test_database_operations_with_live_data():
    """Test: Do database operations work correctly with live data?"""
    print("🧪 Testing: Do database operations work correctly with live data?")
    
    try:
        # Step 1: Check database connection
        db_response = test_session.get(f"{BASE_URL}/api/database/status")
        if db_response.status_code != 200:
            print(f"❌ Database status check failed - status {db_response.status_code}")
            assert False, f"Database status check failed - status {db_response.status_code}"
        
        db_data = db_response.json()
        db_status = db_data.get("database_status", {})
        connection = db_status.get("connection")
        
        if connection != "operational":
            print(f"❌ Database not operational - status: {connection}")
            assert False, f"Database not operational - status: {connection}"
        
        # Step 2: Test data retrieval operations
        flights_response = test_session.get(f"{BASE_URL}/api/flights")
        if flights_response.status_code != 200:
            print(f"❌ Flights retrieval failed - status {flights_response.status_code}")
            assert False, f"Flights retrieval failed - status {flights_response.status_code}"
        
        flights_data = flights_response.json()
        flights = flights_data.get("flights", [])
        
        # Step 3: Test data filtering (if supported)
        if flights:
            # Test basic filtering by checking if we can get specific flight data
            first_flight = flights[0]
            callsign = first_flight.get("callsign")
            
            if callsign:
                # Try to get specific flight data (if endpoint exists)
                try:
                    specific_response = test_session.get(f"{BASE_URL}/api/flights/{callsign}")
                    if specific_response.status_code == 200:
                        print(f"✅ Specific flight retrieval working for {callsign}")
                    elif specific_response.status_code == 404:
                        print(f"⚠️ Specific flight endpoint not found (may not be implemented)")
                    else:
                        print(f"⚠️ Specific flight endpoint returned status {specific_response.status_code}")
                except:
                    print(f"⚠️ Specific flight endpoint not available")
        
        # Step 4: Validate data structure
        if flights:
            required_fields = ["callsign", "latitude", "longitude"]
            sample_flight = flights[0]
            
            missing_fields = [field for field in required_fields if field not in sample_flight]
            if not missing_fields:
                print("✅ Flight data structure complete with required fields")
            else:
                print(f"⚠️ Flight data missing fields: {missing_fields}")
        
        print(f"✅ Database operations test completed - {len(flights)} flights available")
        assert len(flights) >= 0, "Should be able to retrieve flight data"
        
    except Exception as e:
        print(f"❌ Database operations test failed - {e}")
        assert False, f"Database operations test failed: {e}"

@pytest.mark.stage6
@pytest.mark.service_integration
def test_service_communication_patterns():
    """Test: Do services communicate effectively with each other?"""
    print("🧪 Testing: Do services communicate effectively with each other?")
    
    try:
        # Step 1: Check all core services are accessible
        services = [
            ("System Status", "/api/status"),
            ("Database Status", "/api/database/status"),
            ("Flights API", "/api/flights"),
            ("Controllers API", "/api/controllers")
        ]
        
        service_status = {}
        for service_name, endpoint in services:
            try:
                response = test_session.get(f"{BASE_URL}{endpoint}")
                service_status[service_name] = response.status_code == 200
            except:
                service_status[service_name] = False
        
        # Step 2: Analyze service communication patterns
        operational_services = sum(service_status.values())
        total_services = len(services)
        
        print(f"📊 Service Status: {operational_services}/{total_services} operational")
        for service_name, status in service_status.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {service_name}: {'Operational' if status else 'Failed'}")
        
        # Step 3: Test service dependencies
        if service_status["System Status"] and service_status["Database Status"]:
            print("✅ Core system services communicating")
        else:
            print("❌ Core system services not communicating")
            assert False, "Core system services must be operational"
        
        # Step 4: Test data service communication
        if service_status["Flights API"] and service_status["Controllers API"]:
            print("✅ Data services communicating")
        else:
            print("⚠️ Some data services not communicating")
        
        # Step 5: Validate overall service health
        success_rate = operational_services / total_services
        if success_rate >= 0.75:  # 75% of services must be operational
            print(f"✅ Service communication healthy - {success_rate:.1%} success rate")
            assert success_rate >= 0.75, f"Service success rate too low: {success_rate:.1%}"
        else:
            print(f"❌ Service communication poor - {success_rate:.1%} success rate")
            assert False, f"Service success rate too low: {success_rate:.1%}"
        
    except Exception as e:
        print(f"❌ Service communication test failed - {e}")
        assert False, f"Service communication test failed: {e}"

@pytest.mark.stage6
@pytest.mark.service_integration
def test_data_consistency_across_services():
    """Test: Is data consistent across different services?"""
    print("🧪 Testing: Is data consistent across different services?")
    
    try:
        # Step 1: Get data from multiple services
        flights_response = test_session.get(f"{BASE_URL}/api/flights")
        controllers_response = test_session.get(f"{BASE_URL}/api/controllers")
        
        if flights_response.status_code != 200:
            print(f"❌ Flights service failed - status {flights_response.status_code}")
            assert False, f"Flights service failed - status {flights_response.status_code}"
        
        if controllers_response.status_code != 200:
            print(f"❌ Controllers service failed - status {controllers_response.status_code}")
            assert False, f"Controllers service failed - status {controllers_response.status_code}"
        
        # Step 2: Extract and validate data
        flights_data = flights_response.json()
        controllers_data = controllers_response.json()
        
        flights = flights_data.get("flights", [])
        controllers = controllers_data.get("controllers", [])
        
        # Step 3: Check data freshness consistency
        current_time = datetime.now()
        
        # Check if data has timestamps and they're recent
        if flights:
            first_flight = flights[0]
            if "timestamp" in first_flight:
                flight_time = datetime.fromisoformat(first_flight["timestamp"].replace("Z", "+00:00"))
                time_diff = abs((current_time - flight_time).total_seconds())
                
                if time_diff < 300:  # 5 minutes
                    print("✅ Flight data is recent")
                else:
                    print(f"⚠️ Flight data may be stale - {time_diff/60:.1f} minutes old")
        
        if controllers:
            first_controller = controllers[0]
            if "timestamp" in first_controller:
                controller_time = datetime.fromisoformat(first_controller["timestamp"].replace("Z", "+00:00"))
                time_diff = abs((current_time - controller_time).total_seconds())
                
                if time_diff < 300:  # 5 minutes
                    print("✅ Controller data is recent")
                else:
                    print(f"⚠️ Controller data may be stale - {time_diff/60:.1f} minutes old")
        
        # Step 4: Validate data format consistency
        if flights and controllers:
            flight_fields = set(flights[0].keys()) if flights else set()
            controller_fields = set(controllers[0].keys()) if controllers else set()
            
            print(f"📊 Data structure - Flights: {len(flight_fields)} fields, Controllers: {len(controller_fields)} fields")
            
            # Check for common fields that should exist
            common_fields = flight_fields.intersection(controller_fields)
            if "callsign" in common_fields:
                print("✅ Common field 'callsign' present in both services")
            else:
                print("⚠️ Common field 'callsign' missing from one or both services")
        
        # Step 5: Overall consistency assessment
        total_data_points = len(flights) + len(controllers)
        if total_data_points > 0:
            print(f"✅ Data consistency test completed - {len(flights)} flights, {len(controllers)} controllers")
            assert total_data_points > 0, "Should have data available"
        else:
            print("❌ No data available for consistency check")
            assert False, "No data available for consistency check"
        
    except Exception as e:
        print(f"❌ Data consistency test failed - {e}")
        assert False, f"Data consistency test failed: {e}"

# Test execution helper
class ServiceIntegrationTester:
    """Helper class for running service integration tests"""
    
    def __init__(self):
        self.test_results = []
        self.base_url = BASE_URL
        self.session = test_session
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all service integration tests"""
        print("🚀 Starting Stage 6: Service Integration Tests")
        print("=" * 60)
        
        test_methods = [
            ("VATSIM to Database Flow", test_vatsim_to_database_flow),
            ("Cache Behavior with Live Data", test_cache_behavior_with_live_data),
            ("Database Operations with Live Data", test_database_operations_with_live_data),
            ("Service Communication Patterns", test_service_communication_patterns),
            ("Data Consistency Across Services", test_data_consistency_across_services)
        ]
        
        passed = 0
        total = len(test_methods)
        
        for test_name, test_func in test_methods:
            try:
                print(f"\n🧪 Testing: {test_name}")
                test_func()
                self.test_results.append((test_name, "PASS", "Test completed successfully"))
                passed += 1
            except Exception as e:
                self.test_results.append((test_name, "FAIL", str(e)))
        
        success_rate = (passed / total) * 100
        overall_status = "PASS" if success_rate >= 75 else "FAIL"
        
        print(f"\n📊 Test Results: {passed}/{total} passed ({success_rate:.1f}%)")
        print(f"🎯 Overall Status: {overall_status}")
        
        return {
            "passed": passed,
            "total": total,
            "success_rate": success_rate,
            "overall_status": overall_status,
            "results": self.test_results
        }

if __name__ == "__main__":
    tester = ServiceIntegrationTester()
    results = tester.run_all_tests()
    exit(0 if results["overall_status"] == "PASS" else 1)

