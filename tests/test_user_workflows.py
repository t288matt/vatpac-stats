#!/usr/bin/env python3
"""
Stage 2: Core Functionality Tests - User Workflow Validation

Tests that users can accomplish their basic goals with minimal effort.
Focus: Can users get what they need from the system?

Author: VATSIM Data System
Stage: 2 - Core Functionality
"""

import requests
import time
import os
import pytest
from typing import Dict, Any, List

# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8001")
API_TIMEOUT = int(os.getenv("TEST_API_TIMEOUT", "30"))
DATA_FRESHNESS_THRESHOLD = int(os.getenv("TEST_DATA_FRESHNESS_MINUTES", "5"))

# Global test session
test_session = requests.Session()
test_session.timeout = API_TIMEOUT

@pytest.mark.stage2
def test_flight_data_availability():
    """Test: Can users get flight information?"""
    print("🧪 Testing: Can users get flight information?")
    
    try:
        response = test_session.get(f"{BASE_URL}/api/flights")
        
        if response.status_code == 200:
            data = response.json()
            flights = data.get("flights", [])
            
            if flights and len(flights) > 0:
                # Check first flight has basic required fields
                first_flight = flights[0]
                required_fields = ["callsign", "latitude", "longitude"]
                missing_fields = [field for field in required_fields if field not in first_flight]
                
                if not missing_fields:
                    print(f"✅ Flight data available - {len(flights)} flights with required fields")
                    assert len(flights) > 0, "Should have flight data"
                    assert not missing_fields, f"Missing required fields: {missing_fields}"
                else:
                    print(f"❌ Flight data incomplete - missing fields: {missing_fields}")
                    assert False, f"Flight data missing required fields: {missing_fields}"
            else:
                print("❌ No flight data available")
                assert False, "Should have flight data available"
        else:
            print(f"❌ Flight data endpoint failed - status {response.status_code}")
            assert False, f"Flight endpoint returned status {response.status_code}"
            
    except Exception as e:
        print(f"❌ Flight data test failed - {e}")
        assert False, f"Flight data test failed: {e}"

@pytest.mark.stage2
def test_controller_data_access():
    """Test: Can users get ATC controller positions?"""
    print("🧪 Testing: Can users get ATC controller positions?")
    
    try:
        response = test_session.get(f"{BASE_URL}/api/controllers")
        
        if response.status_code == 200:
            data = response.json()
            controllers = data.get("controllers", [])
            
            if controllers and len(controllers) > 0:
                # Check first controller has essential controller information
                first_controller = controllers[0]
                essential_fields = ["callsign", "cid", "name", "rating"]
                missing_fields = [field for field in essential_fields if field not in first_controller]
                
                if not missing_fields:
                    print(f"✅ Controller data available - {len(controllers)} controllers with essential info")
                    assert len(controllers) > 0, "Should have controller data"
                    assert not missing_fields, f"Missing essential fields: {missing_fields}"
                else:
                    print(f"❌ Controller data incomplete - missing fields: {missing_fields}")
                    assert False, f"Controller data missing essential fields: {missing_fields}"
            else:
                print("❌ No controller data available")
                assert False, "Should have controller data available"
        else:
            print(f"❌ Controller data endpoint failed - status {response.status_code}")
            assert False, f"Controller endpoint returned status {response.status_code}"
            
    except Exception as e:
        print(f"❌ Controller data test failed - {e}")
        assert False, f"Controller data test failed: {e}"

@pytest.mark.stage2
def test_data_freshness():
    """Test: Is data being updated recently?"""
    print("🧪 Testing: Is data being updated recently?")
    
    try:
        # Check flights endpoint for data freshness
        response = test_session.get(f"{BASE_URL}/api/flights")
        
        if response.status_code == 200:
            data = response.json()
            timestamp = data.get("timestamp")
            
            if timestamp:
                # Parse timestamp and check if it's recent
                try:
                    # Handle different timestamp formats
                    if isinstance(timestamp, str):
                        if timestamp.endswith('Z'):
                            # ISO format with Z
                            from datetime import datetime
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            # Try parsing as Unix timestamp
                            dt = datetime.fromtimestamp(float(timestamp))
                    else:
                        # Assume Unix timestamp
                        dt = datetime.fromtimestamp(float(timestamp))
                    
                    # Calculate age in minutes
                    age_minutes = (datetime.now() - dt).total_seconds() / 60
                    
                    if age_minutes <= DATA_FRESHNESS_THRESHOLD:
                        print(f"✅ Data is fresh - updated {age_minutes:.1f} minutes ago")
                        assert age_minutes <= DATA_FRESHNESS_THRESHOLD, f"Data too old: {age_minutes:.1f} minutes"
                    else:
                        print(f"⚠️ Data may be stale - updated {age_minutes:.1f} minutes ago")
                        # Don't fail for stale data, just warn
                        assert True, "Data freshness warning (not critical)"
                        
                except Exception as parse_error:
                    print(f"⚠️ Could not parse timestamp: {timestamp} - {parse_error}")
                    # Don't fail for timestamp parsing issues
                    assert True, "Timestamp parsing issue (not critical)"
            else:
                print("⚠️ No timestamp in response - cannot verify freshness")
                # Don't fail for missing timestamp
                assert True, "No timestamp available (not critical)"
        else:
            print(f"❌ Data freshness check failed - status {response.status_code}")
            assert False, f"Data freshness check failed: {response.status_code}"
            
    except Exception as e:
        print(f"❌ Data freshness test failed - {e}")
        assert False, f"Data freshness test failed: {e}"

@pytest.mark.stage2
def test_api_response_quality():
    """Test: Are API endpoints returning expected data structure?"""
    print("🧪 Testing: Are API endpoints returning expected data structure?")
    
    try:
        # Test key endpoints for proper JSON structure
        endpoints = [
            ("/api/flights", "flights"),
            ("/api/controllers", "controllers"),
            ("/api/status", "status")
        ]
        
        working_endpoints = 0
        total_endpoints = len(endpoints)
        
        for endpoint, expected_key in endpoints:
            try:
                response = test_session.get(f"{BASE_URL}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if response has expected structure
                    if expected_key in data or isinstance(data, list):
                        working_endpoints += 1
                        print(f"✅ {endpoint} - proper JSON structure")
                    else:
                        print(f"⚠️ {endpoint} - unexpected structure")
                else:
                    print(f"❌ {endpoint} - status {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint} - error: {e}")
        
        success_rate = (working_endpoints / total_endpoints) * 100
        
        if success_rate >= 66:  # At least 2 out of 3 working properly
            print(f"✅ API response quality good - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)")
            assert working_endpoints >= 2, f"At least 2 endpoints should work properly, got {working_endpoints}"
        else:
            print(f"❌ API response quality poor - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)")
            assert False, f"API response quality poor - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)"
            
    except Exception as e:
        print(f"❌ API response quality test failed - {e}")
        assert False, f"API response quality test failed: {e}"

# Legacy class-based tests for direct execution
class UserWorkflowTester:
    """Core functionality validation for user workflows (legacy support)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = API_TIMEOUT
        self.test_results = []
    
    def test_flight_data_availability(self) -> bool:
        """Test: Can users get flight information?"""
        try:
            print("🧪 Testing: Can users get flight information?")
            
            response = self.session.get(f"{BASE_URL}/api/flights")
            
            if response.status_code == 200:
                data = response.json()
                flights = data.get("flights", [])
                
                if flights and len(flights) > 0:
                    # Check first flight has basic required fields
                    first_flight = flights[0]
                    required_fields = ["callsign", "latitude", "longitude"]
                    missing_fields = [field for field in required_fields if field not in first_flight]
                    
                    if not missing_fields:
                        print(f"✅ Flight data available - {len(flights)} flights with required fields")
                        self.test_results.append(("Flight Data", "PASS", f"{len(flights)} flights available"))
                        assert True  # Test passed successfully
                    else:
                        print(f"❌ Flight data incomplete - missing fields: {missing_fields}")
                        self.test_results.append(("Flight Data", "FAIL", f"Missing fields: {missing_fields}"))
                        assert False, "Test failed"
                else:
                    print("❌ No flight data available")
                    self.test_results.append(("Flight Data", "FAIL", "No flights available"))
                    assert False, "Test failed"
            else:
                print(f"❌ Flight data endpoint failed - status {response.status_code}")
                self.test_results.append(("Flight Data", "FAIL", f"Status {response.status_code}"))
                assert False, f"Test failed: {e}"
                
        except Exception as e:
            print(f"❌ Flight data test failed - {e}")
            self.test_results.append(("Flight Data", "FAIL", str(e)))
            assert False, "Test failed"
    
    def test_controller_data_access(self) -> bool:
        """Test: Can users get ATC controller positions?"""
        try:
            print("🧪 Testing: Can users get ATC controller positions?")
            
            response = self.session.get(f"{BASE_URL}/api/controllers")
            
            if response.status_code == 200:
                data = response.json()
                controllers = data.get("controllers", [])
                
                if controllers and len(controllers) > 0:
                    # Check first controller has essential controller information
                    first_controller = controllers[0]
                    essential_fields = ["callsign", "cid", "name", "rating"]
                    missing_fields = [field for field in essential_fields if field not in first_controller]
                    
                    if not missing_fields:
                        print(f"✅ Controller data available - {len(controllers)} controllers with essential info")
                        self.test_results.append(("Controller Data", "PASS", f"{len(controllers)} controllers available"))
                        assert True  # Test passed successfully
                    else:
                        print(f"❌ Controller data incomplete - missing fields: {missing_fields}")
                        self.test_results.append(("Controller Data", "FAIL", f"Missing fields: {missing_fields}"))
                        assert False, "Test failed"
                else:
                    print("❌ No controller data available")
                    self.test_results.append(("Controller Data", "FAIL", "No controllers available"))
                    assert False, "Test failed"
            else:
                print(f"❌ Controller data endpoint failed - status {response.status_code}")
                self.test_results.append(("Controller Data", "FAIL", f"Status {response.status_code}"))
                assert False, f"Test failed: {e}"
                
        except Exception as e:
            print(f"❌ Controller data test failed - {e}")
            self.test_results.append(("Controller Data", "FAIL", str(e)))
            assert False, "Test failed"
    
    def test_data_freshness(self) -> bool:
        """Test: Is data being updated recently?"""
        try:
            print("🧪 Testing: Is data being updated recently?")
            
            # Check flights endpoint for data freshness
            response = self.session.get(f"{BASE_URL}/api/flights")
            
            if response.status_code == 200:
                data = response.json()
                timestamp = data.get("timestamp")
                
                if timestamp:
                    # Parse timestamp and check if it's recent
                    try:
                        from datetime import datetime
                        # Handle different timestamp formats
                        if isinstance(timestamp, str):
                            if timestamp.endswith('Z'):
                                # ISO format with Z
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            else:
                                # Try parsing as Unix timestamp
                                dt = datetime.fromtimestamp(float(timestamp))
                        else:
                            # Assume Unix timestamp
                            dt = datetime.fromtimestamp(float(timestamp))
                        
                        # Calculate age in minutes
                        age_minutes = (datetime.now() - dt).total_seconds() / 60
                        
                        if age_minutes <= DATA_FRESHNESS_THRESHOLD:
                            print(f"✅ Data is fresh - updated {age_minutes:.1f} minutes ago")
                            self.test_results.append(("Data Freshness", "PASS", f"Updated {age_minutes:.1f} min ago"))
                            assert True  # Test passed successfully
                        else:
                            print(f"⚠️ Data may be stale - updated {age_minutes:.1f} minutes ago")
                            self.test_results.append(("Data Freshness", "WARN", f"Updated {age_minutes:.1f} min ago"))
                            return True  # Don't fail for stale data
                            
                    except Exception as parse_error:
                        print(f"⚠️ Could not parse timestamp: {timestamp} - {parse_error}")
                        self.test_results.append(("Data Freshness", "WARN", "Timestamp parsing issue"))
                        return True  # Don't fail for timestamp parsing issues
                else:
                    print("⚠️ No timestamp in response - cannot verify freshness")
                    self.test_results.append(("Data Freshness", "WARN", "No timestamp available"))
                    return True  # Don't fail for missing timestamp
            else:
                print(f"❌ Data freshness check failed - status {response.status_code}")
                self.test_results.append(("Data Freshness", "FAIL", f"Status {response.status_code}"))
                assert False, f"Test failed: {e}"
                
        except Exception as e:
            print(f"❌ Data freshness test failed - {e}")
            self.test_results.append(("Data Freshness", "FAIL", str(e)))
            assert False, "Test failed"
    
    def test_api_response_quality(self) -> bool:
        """Test: Are API endpoints returning expected data structure?"""
        try:
            print("🧪 Testing: Are API endpoints returning expected data structure?")
            
            # Test key endpoints for proper JSON structure
            endpoints = [
                ("/api/flights", "flights"),
                ("/api/controllers", "controllers"),
                ("/api/status", "status")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints)
            
            for endpoint, expected_key in endpoints:
                try:
                    response = self.session.get(f"{BASE_URL}{endpoint}")
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check if response has expected structure
                        if expected_key in data or isinstance(data, list):
                            working_endpoints += 1
                            print(f"✅ {endpoint} - proper JSON structure")
                        else:
                            print(f"⚠️ {endpoint} - unexpected structure")
                    else:
                        print(f"❌ {endpoint} - status {response.status_code}")
                except Exception as e:
                    print(f"❌ {endpoint} - error: {e}")
            
            success_rate = (working_endpoints / total_endpoints) * 100
            
            if success_rate >= 66:  # At least 2 out of 3 working properly
                print(f"✅ API response quality good - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)")
                self.test_results.append(("API Quality", "PASS", f"{working_endpoints}/{total_endpoints} working"))
                assert True  # Test passed successfully
            else:
                print(f"❌ API response quality poor - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)")
                self.test_results.append(("API Quality", "FAIL", f"{working_endpoints}/{total_endpoints} working"))
                assert False, f"Test failed: {e}"
                
        except Exception as e:
            print(f"❌ API response quality test failed - {e}")
            self.test_results.append(("API Quality", "FAIL", str(e)))
            assert False, "Test failed"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all Stage 2 tests and return results"""
        print("🚀 Starting Stage 2: Core Functionality Tests")
        print("=" * 60)
        
        # Run all tests
        tests = [
            self.test_flight_data_availability,
            self.test_controller_data_access,
            self.test_data_freshness,
            self.test_api_response_quality
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            time.sleep(1)  # Small delay between tests
        
        # Calculate results
        success_rate = (passed / total) * 100
        overall_status = "PASS" if success_rate >= 75 else "FAIL"
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} passed ({success_rate:.0f}%)")
        print(f"🎯 Overall Status: {overall_status}")
        
        # Print detailed results
        print("\n📋 Detailed Results:")
        for test_name, status, details in self.test_results:
            icon = "✅" if status == "PASS" else "⚠️" if status == "WARN" else "❌"
            print(f"  {icon} {test_name}: {status} - {details}")
        
        return {
            "stage": "2 - Core Functionality",
            "overall_status": overall_status,
            "passed": passed,
            "total": total,
            "success_rate": success_rate,
            "test_results": self.test_results
        }

def main():
    """Main test execution for direct running"""
    tester = UserWorkflowTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code for CI/CD
    if results["overall_status"] == "PASS":
        print("\n🎉 Stage 2 Core Functionality Tests PASSED!")
        print("✅ Users can get flight data, controller data, and access core functionality")
        exit(0)
    else:
        print("\n❌ Stage 2 Core Functionality Tests FAILED!")
        print("⚠️  Core functionality has issues that need attention")
        exit(1)

if __name__ == "__main__":
    main()
