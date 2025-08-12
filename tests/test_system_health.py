#!/usr/bin/env python3
"""
Stage 1: Foundation Tests - Basic System Validation

Tests basic system accessibility and health with minimal effort.
Focus: Can users reach the system and is it running?

Author: VATSIM Data System
Stage: 1 - Foundation
"""

import requests
import time
import os
import pytest
from typing import Dict, Any

# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8001")
API_TIMEOUT = int(os.getenv("TEST_API_TIMEOUT", "30"))
WAIT_TIMEOUT = int(os.getenv("TEST_WAIT_TIMEOUT", "60"))

# Global test session
test_session = requests.Session()
test_session.timeout = API_TIMEOUT

@pytest.mark.stage1
def test_system_accessible():
    """Test: Can users reach the system?"""
    print("🧪 Testing: Can users reach the system?")
    
    try:
        response = test_session.get(f"{BASE_URL}/api/status")
        
        if response.status_code == 200:
            print("✅ System is accessible - status endpoint responding")
            assert True, "System is accessible"
        else:
            print(f"❌ System not accessible - status code {response.status_code}")
            assert False, f"System not accessible - status code {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        print("❌ System not accessible - connection refused")
        assert False, "System not accessible - connection refused"
    except Exception as e:
        print(f"❌ System access test failed - {e}")
        assert False, f"System access test failed: {e}"

@pytest.mark.stage1
def test_system_health():
    """Test: Is the system healthy and operational?"""
    print("🧪 Testing: Is the system healthy and operational?")
    
    try:
        response = test_session.get(f"{BASE_URL}/api/status")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check basic health indicators
            status = data.get("status")
            timestamp = data.get("timestamp")
            
            if status == "operational" and timestamp:
                print("✅ System is healthy - operational status confirmed")
                assert status == "operational", "System status should be operational"
                assert timestamp is not None, "System should have timestamp"
            else:
                print(f"❌ System not healthy - status: {status}, timestamp: {timestamp}")
                assert False, f"System not healthy - status: {status}, timestamp: {timestamp}"
        else:
            print(f"❌ Health check failed - status code {response.status_code}")
            assert False, f"Health check failed - status code {response.status_code}"
            
    except Exception as e:
        print(f"❌ Health check failed - {e}")
        assert False, f"Health check failed: {e}"

@pytest.mark.stage1
def test_database_connectivity():
    """Test: Is the database accessible and responding?"""
    print("🧪 Testing: Is the database accessible and responding?")
    
    try:
        response = test_session.get(f"{BASE_URL}/api/database/status")
        
        if response.status_code == 200:
            data = response.json()
            db_status = data.get("database_status", {})
            
            # Check database connection
            connection = db_status.get("connection")
            tables = db_status.get("tables", 0)
            
            if connection == "operational" and tables > 0:
                print(f"✅ Database is accessible - {tables} tables available")
                assert connection == "operational", "Database connection should be operational"
                assert tables > 0, "Database should have tables"
            else:
                print(f"❌ Database not accessible - connection: {connection}, tables: {tables}")
                assert False, f"Database not accessible - connection: {connection}, tables: {tables}"
        else:
            print(f"❌ Database check failed - status code {response.status_code}")
            assert False, f"Database check failed - status code {response.status_code}"
            
    except Exception as e:
        print(f"❌ Database check failed - {e}")
        assert False, f"Database check failed: {e}"

@pytest.mark.stage1
def test_basic_api_endpoints():
    """Test: Are basic API endpoints responding?"""
    print("🧪 Testing: Are basic API endpoints responding?")
    
    try:
        # Test a few key endpoints
        endpoints = [
            "/api/status",
            "/api/flights", 
            "/api/controllers"
        ]
        
        working_endpoints = 0
        total_endpoints = len(endpoints)
        
        for endpoint in endpoints:
            try:
                response = test_session.get(f"{BASE_URL}{endpoint}")
                if response.status_code == 200:
                    working_endpoints += 1
                    print(f"✅ {endpoint} - responding")
                else:
                    print(f"❌ {endpoint} - status {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint} - error: {e}")
        
        success_rate = (working_endpoints / total_endpoints) * 100
        
        if success_rate >= 66:  # At least 2 out of 3 working
            print(f"✅ Basic API endpoints working - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)")
            assert working_endpoints >= 2, f"At least 2 endpoints should work, got {working_endpoints}"
        else:
            print(f"❌ Basic API endpoints failing - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)")
            assert False, f"Basic API endpoints failing - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)"
            
    except Exception as e:
        print(f"❌ API endpoint test failed - {e}")
        assert False, f"API endpoint test failed: {e}"

# Legacy class-based tests for direct execution
class SystemHealthTester:
    """Basic system health and accessibility validation (legacy support)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = API_TIMEOUT
        self.test_results = []
    
    def test_system_accessible(self) -> bool:
        """Test: Can users reach the system?"""
        try:
            print("🧪 Testing: Can users reach the system?")
            
            response = self.session.get(f"{BASE_URL}/api/status")
            
            if response.status_code == 200:
                print("✅ System is accessible - status endpoint responding")
                self.test_results.append(("System Access", "PASS", "Status endpoint responding"))
                return True
            else:
                print(f"❌ System not accessible - status code {response.status_code}")
                self.test_results.append(("System Access", "FAIL", f"Status code {response.status_code}"))
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ System not accessible - connection refused")
            self.test_results.append(("System Access", "FAIL", "Connection refused"))
            return False
        except Exception as e:
            print(f"❌ System access test failed - {e}")
            self.test_results.append(("System Access", "FAIL", str(e)))
            return False
    
    def test_system_health(self) -> bool:
        """Test: Is the system healthy and operational?"""
        try:
            print("🧪 Testing: Is the system healthy and operational?")
            
            response = self.session.get(f"{BASE_URL}/api/status")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check basic health indicators
                status = data.get("status")
                timestamp = data.get("timestamp")
                
                if status == "operational" and timestamp:
                    print("✅ System is healthy - operational status confirmed")
                    self.test_results.append(("System Health", "PASS", "Operational status"))
                    return True
                else:
                    print(f"❌ System not healthy - status: {status}, timestamp: {timestamp}")
                    self.test_results.append(("System Health", "FAIL", f"Status: {status}"))
                    return False
            else:
                print(f"❌ Health check failed - status code {response.status_code}")
                self.test_results.append(("System Health", "FAIL", f"Status code {response.status_code}"))
                return False
                
        except Exception as e:
            print(f"❌ Health check failed - {e}")
            self.test_results.append(("System Health", "FAIL", str(e)))
            return False
    
    def test_database_connectivity(self) -> bool:
        """Test: Is the database accessible and responding?"""
        try:
            print("🧪 Testing: Is the database accessible and responding?")
            
            response = self.session.get(f"{BASE_URL}/api/database/status")
            
            if response.status_code == 200:
                data = response.json()
                db_status = data.get("database_status", {})
                
                # Check database connection
                connection = db_status.get("connection")
                tables = db_status.get("tables", 0)
                
                if connection == "operational" and tables > 0:
                    print(f"✅ Database is accessible - {tables} tables available")
                    self.test_results.append(("Database", "PASS", f"{tables} tables accessible"))
                    return True
                else:
                    print(f"❌ Database not accessible - connection: {connection}, tables: {tables}")
                    self.test_results.append(("Database", "FAIL", f"Connection: {connection}"))
                    return False
            else:
                print(f"❌ Database check failed - status code {response.status_code}")
                self.test_results.append(("Database", "FAIL", f"Status code {response.status_code}"))
                return False
                
        except Exception as e:
            print(f"❌ Database check failed - {e}")
            self.test_results.append(("Database", "FAIL", str(e)))
            return False
    
    def test_basic_api_endpoints(self) -> bool:
        """Test: Are basic API endpoints responding?"""
        try:
            print("🧪 Testing: Are basic API endpoints responding?")
            
            # Test a few key endpoints
            endpoints = [
                "/api/status",
                "/api/flights", 
                "/api/controllers"
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints)
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(f"{BASE_URL}{endpoint}")
                    if response.status_code == 200:
                        working_endpoints += 1
                        print(f"✅ {endpoint} - responding")
                    else:
                        print(f"❌ {endpoint} - status {response.status_code}")
                except Exception as e:
                    print(f"❌ {endpoint} - error: {e}")
            
            success_rate = (working_endpoints / total_endpoints) * 100
            
            if success_rate >= 66:  # At least 2 out of 3 working
                print(f"✅ Basic API endpoints working - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)")
                self.test_results.append(("API Endpoints", "PASS", f"{working_endpoints}/{total_endpoints} working"))
                return True
            else:
                print(f"❌ Basic API endpoints failing - {working_endpoints}/{total_endpoints} ({success_rate:.0f}%)")
                self.test_results.append(("API Endpoints", "FAIL", f"{working_endpoints}/{total_endpoints} working"))
                return False
                
        except Exception as e:
            print(f"❌ API endpoint test failed - {e}")
            self.test_results.append(("API Endpoints", "FAIL", str(e)))
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all foundation tests and return results"""
        print("🚀 Starting Stage 1: Foundation Tests")
        print("=" * 50)
        
        # Run all tests
        tests = [
            self.test_system_accessible,
            self.test_system_health,
            self.test_database_connectivity,
            self.test_basic_api_endpoints
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
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} passed ({success_rate:.0f}%)")
        print(f"🎯 Overall Status: {overall_status}")
        
        # Print detailed results
        print("\n📋 Detailed Results:")
        for test_name, status, details in self.test_results:
            icon = "✅" if status == "PASS" else "❌"
            print(f"  {icon} {test_name}: {status} - {details}")
        
        return {
            "stage": "1 - Foundation",
            "overall_status": overall_status,
            "passed": passed,
            "total": total,
            "success_rate": success_rate,
            "test_results": self.test_results
        }

def main():
    """Main test execution for direct running"""
    tester = SystemHealthTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code for CI/CD
    if results["overall_status"] == "PASS":
        print("\n🎉 Stage 1 Foundation Tests PASSED!")
        print("✅ System is accessible, healthy, and responding")
        exit(0)
    else:
        print("\n❌ Stage 1 Foundation Tests FAILED!")
        print("⚠️  System has issues that need attention")
        exit(1)

if __name__ == "__main__":
    main()
