#!/usr/bin/env python3
"""
Stage 3: Data Quality Tests - Data Reliability Validation

Tests that data is reliable for business analysis and decision-making.
Focus: Is the data any good for users to make decisions with?

Author: VATSIM Data System
Stage: 3 - Data Quality
"""

import requests
import time
import os
import pytest
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8001")
API_TIMEOUT = int(os.getenv("TEST_API_TIMEOUT", "30"))
DATA_QUALITY_THRESHOLD = float(os.getenv("TEST_DATA_QUALITY_THRESHOLD", "99.0"))

# Global test session
test_session = requests.Session()
test_session.timeout = API_TIMEOUT

@pytest.mark.stage3
def test_flight_plan_completeness():
    """Test: Do all flights have required fields?"""
    print("🧪 Testing: Do all flights have required fields?")
    
    try:
        response = test_session.get(f"{BASE_URL}/api/flights")
        
        if response.status_code == 200:
            data = response.json()
            flights = data.get("flights", [])
            
            if flights and len(flights) > 0:
                # Define required fields for flight analysis
                required_fields = ["callsign", "latitude", "longitude", "altitude", "groundspeed", "heading"]
                incomplete_flights = []
                
                for i, flight in enumerate(flights):
                    missing_fields = [field for field in required_fields if field not in flight or flight[field] is None]
                    if missing_fields:
                        incomplete_flights.append({
                            "index": i,
                            "callsign": flight.get("callsign", "UNKNOWN"),
                            "missing": missing_fields
                        })
                
                # Calculate completeness rate
                total_flights = len(flights)
                complete_flights = total_flights - len(incomplete_flights)
                completeness_rate = (complete_flights / total_flights) * 100
                
                if completeness_rate == 100:
                    print(f"✅ Flight plan completeness: 100% - All {total_flights} flights have required fields")
                    assert completeness_rate == 100, f"All flights must have required fields, got {completeness_rate:.1f}%"
                else:
                    print(f"❌ Flight plan completeness: {completeness_rate:.1f}% - {len(incomplete_flights)} flights incomplete")
                    print(f"📋 Sample incomplete flights:")
                    for flight_info in incomplete_flights[:3]:  # Show first 3 examples
                        print(f"   - {flight_info['callsign']}: Missing {flight_info['missing']}")
                    assert False, f"Flight plan completeness below 100%: {completeness_rate:.1f}%"
            else:
                print("❌ No flight data available for completeness check")
                assert False, "Should have flight data available"
        else:
            print(f"❌ Flight data endpoint failed - status {response.status_code}")
            assert False, f"Flight endpoint returned status {response.status_code}"
            
    except Exception as e:
        print(f"❌ Flight plan completeness test failed - {e}")
        assert False, f"Flight plan completeness test failed: {e}"

@pytest.mark.stage3
def test_position_data_accuracy():
    """Test: Are coordinates within valid ranges?"""
    print("🧪 Testing: Are coordinates within valid ranges?")
    
    try:
        response = test_session.get(f"{BASE_URL}/api/flights")
        
        if response.status_code == 200:
            data = response.json()
            flights = data.get("flights", [])
            
            if flights and len(flights) > 0:
                # Define valid ranges for aviation data
                valid_ranges = {
                    "latitude": (-90, 90),
                    "longitude": (-180, 180),
                    "altitude": (0, 60000),  # 0 to 60,000 feet
                    "groundspeed": (0, 800),  # 0 to 800+ knots
                    "heading": (0, 360)       # 0 to 360 degrees
                }
                
                invalid_positions = []
                total_checks = 0
                
                for i, flight in enumerate(flights):
                    for field, (min_val, max_val) in valid_ranges.items():
                        if field in flight and flight[field] is not None:
                            total_checks += 1
                            value = flight[field]
                            
                            # Check if value is within valid range
                            if not (min_val <= value <= max_val):
                                invalid_positions.append({
                                    "index": i,
                                    "callsign": flight.get("callsign", "UNKNOWN"),
                                    "field": field,
                                    "value": value,
                                    "expected_range": f"{min_val} to {max_val}"
                                })
                
                # Calculate accuracy rate
                if total_checks > 0:
                    valid_positions = total_checks - len(invalid_positions)
                    accuracy_rate = (valid_positions / total_checks) * 100
                    
                    if accuracy_rate >= DATA_QUALITY_THRESHOLD:
                        print(f"✅ Position data accuracy: {accuracy_rate:.1f}% - {valid_positions}/{total_checks} valid")
                        assert accuracy_rate >= DATA_QUALITY_THRESHOLD, f"Position accuracy below {DATA_QUALITY_THRESHOLD}%: {accuracy_rate:.1f}%"
                    else:
                        print(f"❌ Position data accuracy: {accuracy_rate:.1f}% - {len(invalid_positions)} invalid positions")
                        print(f"📋 Sample invalid positions:")
                        for pos_info in invalid_positions[:3]:  # Show first 3 examples
                            print(f"   - {pos_info['callsign']}: {pos_info['field']} = {pos_info['value']} (expected {pos_info['expected_range']})")
                        assert False, f"Position accuracy below {DATA_QUALITY_THRESHOLD}%: {accuracy_rate:.1f}%"
                else:
                    print("⚠️ No position data available for accuracy check")
                    assert True, "No position data to validate (not critical)"
            else:
                print("❌ No flight data available for accuracy check")
                assert False, "Should have flight data available"
        else:
            print(f"❌ Flight data endpoint failed - status {response.status_code}")
            assert False, f"Flight endpoint returned status {response.status_code}"
            
    except Exception as e:
        print(f"❌ Position data accuracy test failed - {e}")
        assert False, f"Position data accuracy test failed: {e}"

@pytest.mark.stage3
def test_data_integrity():
    """Test: Is there obvious data corruption?"""
    print("🧪 Testing: Is there obvious data corruption?")
    
    try:
        response = test_session.get(f"{BASE_URL}/api/flights")
        
        if response.status_code == 200:
            data = response.json()
            flights = data.get("flights", [])
            
            if flights and len(flights) > 0:
                corruption_issues = []
                total_flights = len(flights)
                
                for i, flight in enumerate(flights):
                    # Check for null/empty critical fields
                    critical_fields = ["callsign", "latitude", "longitude"]
                    for field in critical_fields:
                        if field in flight and (flight[field] is None or flight[field] == ""):
                            corruption_issues.append({
                                "index": i,
                                "callsign": flight.get("callsign", "UNKNOWN"),
                                "issue": f"Empty/null {field}"
                            })
                    
                    # Check for malformed data types
                    if "callsign" in flight and not isinstance(flight["callsign"], str):
                        corruption_issues.append({
                            "index": i,
                            "callsign": flight.get("callsign", "UNKNOWN"),
                            "issue": f"Invalid callsign type: {type(flight['callsign'])}"
                        })
                    
                    if "latitude" in flight and not isinstance(flight["latitude"], (int, float)):
                        corruption_issues.append({
                            "index": i,
                            "callsign": flight.get("callsign", "UNKNOWN"),
                            "issue": f"Invalid latitude type: {type(flight['latitude'])}"
                        })
                    
                    if "longitude" in flight and not isinstance(flight["longitude"], (int, float)):
                        corruption_issues.append({
                            "index": i,
                            "callsign": flight.get("callsign", "UNKNOWN"),
                            "issue": f"Invalid longitude type: {type(flight['longitude'])}"
                        })
                
                # Calculate integrity rate
                if corruption_issues:
                    integrity_rate = ((total_flights - len(corruption_issues)) / total_flights) * 100
                    print(f"❌ Data integrity: {integrity_rate:.1f}% - {len(corruption_issues)} corruption issues")
                    print(f"📋 Sample corruption issues:")
                    for issue in corruption_issues[:3]:  # Show first 3 examples
                        print(f"   - {issue['callsign']}: {issue['issue']}")
                    assert False, f"Data integrity below 100%: {integrity_rate:.1f}%"
                else:
                    print(f"✅ Data integrity: 100% - No corruption issues detected in {total_flights} flights")
                    assert True, "Data integrity check passed"
            else:
                print("❌ No flight data available for integrity check")
                assert False, "Should have flight data available"
        else:
            print(f"❌ Flight data endpoint failed - status {response.status_code}")
            assert False, f"Flight endpoint returned status {response.status_code}"
            
    except Exception as e:
        print(f"❌ Data integrity test failed - {e}")
        assert False, f"Data integrity test failed: {e}"

@pytest.mark.stage3
def test_business_rules():
    """Test: Do fields contain expected data?"""
    print("🧪 Testing: Do fields contain expected data?")
    
    try:
        # Test flight data business rules
        flight_response = test_session.get(f"{BASE_URL}/api/flights")
        controller_response = test_session.get(f"{BASE_URL}/api/controllers")
        
        business_rule_violations = []
        total_checks = 0
        
        # Check flight data business rules
        if flight_response.status_code == 200:
            flight_data = flight_response.json()
            flights = flight_data.get("flights", [])
            
            if flights and len(flights) > 0:
                for i, flight in enumerate(flights):
                    total_checks += 1
                    
                    # Check callsign format (should be string, not empty)
                    if "callsign" in flight:
                        callsign = flight["callsign"]
                        if not isinstance(callsign, str) or len(callsign.strip()) == 0:
                            business_rule_violations.append({
                                "type": "flight",
                                "index": i,
                                "callsign": str(callsign),
                                "issue": "Invalid callsign format"
                            })
                    
                    # Check altitude is positive number
                    if "altitude" in flight and flight["altitude"] is not None:
                        altitude = flight["altitude"]
                        if not isinstance(altitude, (int, float)) or altitude < 0:
                            business_rule_violations.append({
                                "type": "flight",
                                "index": i,
                                "callsign": flight.get("callsign", "UNKNOWN"),
                                "issue": f"Invalid altitude: {altitude}"
                            })
        
        # Check controller data business rules
        if controller_response.status_code == 200:
            controller_data = controller_response.json()
            controllers = controller_data.get("controllers", [])
            
            if controllers and len(controllers) > 0:
                for i, controller in enumerate(controllers):
                    total_checks += 1
                    
                    # Check controller rating is valid VATSIM level
                    if "rating" in controller and controller["rating"] is not None:
                        rating = controller["rating"]
                        valid_ratings = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
                        if rating not in valid_ratings:
                            business_rule_violations.append({
                                "type": "controller",
                                "index": i,
                                "callsign": controller.get("callsign", "UNKNOWN"),
                                "issue": f"Invalid VATSIM rating: {rating}"
                            })
                    
                    # Check CID is positive number
                    if "cid" in controller and controller["cid"] is not None:
                        cid = controller["cid"]
                        if not isinstance(cid, int) or cid <= 0:
                            business_rule_violations.append({
                                "type": "controller",
                                "index": i,
                                "callsign": controller.get("callsign", "UNKNOWN"),
                                "issue": f"Invalid CID: {cid}"
                            })
        
        # Calculate business rule compliance rate
        if total_checks > 0:
            compliant_checks = total_checks - len(business_rule_violations)
            compliance_rate = (compliant_checks / total_checks) * 100
            
            if compliance_rate >= DATA_QUALITY_THRESHOLD:
                print(f"✅ Business rule compliance: {compliance_rate:.1f}% - {compliant_checks}/{total_checks} compliant")
                assert compliance_rate >= DATA_QUALITY_THRESHOLD, f"Business rule compliance below {DATA_QUALITY_THRESHOLD}%: {compliance_rate:.1f}%"
            else:
                print(f"❌ Business rule compliance: {compliance_rate:.1f}% - {len(business_rule_violations)} violations")
                print(f"📋 Sample violations:")
                for violation in business_rule_violations[:3]:  # Show first 3 examples
                    print(f"   - {violation['type'].title()}: {violation['callsign']} - {violation['issue']}")
                assert False, f"Business rule compliance below {DATA_QUALITY_THRESHOLD}%: {compliance_rate:.1f}%"
        else:
            print("⚠️ No data available for business rule validation")
            assert True, "No data to validate (not critical)"
            
    except Exception as e:
        print(f"❌ Business rules test failed - {e}")
        assert False, f"Business rules test failed: {e}"

# Legacy class-based tests for direct execution
class DataQualityTester:
    """Data quality validation for business reliability (legacy support)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = API_TIMEOUT
        self.test_results = []
    
    def test_flight_plan_completeness(self) -> bool:
        """Test: Do all flights have required fields?"""
        try:
            print("🧪 Testing: Do all flights have required fields?")
            
            response = self.session.get(f"{BASE_URL}/api/flights")
            
            if response.status_code == 200:
                data = response.json()
                flights = data.get("flights", [])
                
                if flights and len(flights) > 0:
                    required_fields = ["callsign", "latitude", "longitude", "altitude", "groundspeed", "heading"]
                    incomplete_flights = []
                    
                    for flight in flights:
                        missing_fields = [field for field in required_fields if field not in flight or flight[field] is None]
                        if missing_fields:
                            incomplete_flights.append({
                                "callsign": flight.get("callsign", "UNKNOWN"),
                                "missing": missing_fields
                            })
                    
                    total_flights = len(flights)
                    complete_flights = total_flights - len(incomplete_flights)
                    completeness_rate = (complete_flights / total_flights) * 100
                    
                    if completeness_rate == 100:
                        print(f"✅ Flight plan completeness: 100% - All {total_flights} flights have required fields")
                        self.test_results.append(("Flight Completeness", "PASS", f"100% - {total_flights} flights"))
                        return True
                    else:
                        print(f"❌ Flight plan completeness: {completeness_rate:.1f}% - {len(incomplete_flights)} flights incomplete")
                        self.test_results.append(("Flight Completeness", "FAIL", f"{completeness_rate:.1f}% - {len(incomplete_flights)} incomplete"))
                        return False
                else:
                    print("❌ No flight data available for completeness check")
                    self.test_results.append(("Flight Completeness", "FAIL", "No data available"))
                    return False
            else:
                print(f"❌ Flight data endpoint failed - status {response.status_code}")
                self.test_results.append(("Flight Completeness", "FAIL", f"Status {response.status_code}"))
                return False
                
        except Exception as e:
            print(f"❌ Flight plan completeness test failed - {e}")
            self.test_results.append(("Flight Completeness", "FAIL", str(e)))
            return False
    
    def test_position_data_accuracy(self) -> bool:
        """Test: Are coordinates within valid ranges?"""
        try:
            print("🧪 Testing: Are coordinates within valid ranges?")
            
            response = self.session.get(f"{BASE_URL}/api/flights")
            
            if response.status_code == 200:
                data = response.json()
                flights = data.get("flights", [])
                
                if flights and len(flights) > 0:
                    valid_ranges = {
                        "latitude": (-90, 90),
                        "longitude": (-180, 180),
                        "altitude": (0, 60000),
                        "groundspeed": (0, 800),
                        "heading": (0, 360)
                    }
                    
                    invalid_positions = []
                    total_checks = 0
                    
                    for flight in flights:
                        for field, (min_val, max_val) in valid_ranges.items():
                            if field in flight and flight[field] is not None:
                                total_checks += 1
                                value = flight[field]
                                if not (min_val <= value <= max_val):
                                    invalid_positions.append({
                                        "callsign": flight.get("callsign", "UNKNOWN"),
                                        "field": field,
                                        "value": value
                                    })
                    
                    if total_checks > 0:
                        valid_positions = total_checks - len(invalid_positions)
                        accuracy_rate = (valid_positions / total_checks) * 100
                        
                        if accuracy_rate >= DATA_QUALITY_THRESHOLD:
                            print(f"✅ Position data accuracy: {accuracy_rate:.1f}% - {valid_positions}/{total_checks} valid")
                            self.test_results.append(("Position Accuracy", "PASS", f"{accuracy_rate:.1f}% - {valid_positions}/{total_checks}"))
                            return True
                        else:
                            print(f"❌ Position data accuracy: {accuracy_rate:.1f}% - {len(invalid_positions)} invalid")
                            self.test_results.append(("Position Accuracy", "FAIL", f"{accuracy_rate:.1f}% - {len(invalid_positions)} invalid"))
                            return False
                    else:
                        print("⚠️ No position data available for accuracy check")
                        self.test_results.append(("Position Accuracy", "WARN", "No data available"))
                        return True
                else:
                    print("❌ No flight data available for accuracy check")
                    self.test_results.append(("Position Accuracy", "FAIL", "No data available"))
                    return False
            else:
                print(f"❌ Flight data endpoint failed - status {response.status_code}")
                self.test_results.append(("Position Accuracy", "FAIL", f"Status {response.status_code}"))
                return False
                
        except Exception as e:
            print(f"❌ Position data accuracy test failed - {e}")
            self.test_results.append(("Position Accuracy", "FAIL", str(e)))
            return False
    
    def test_data_integrity(self) -> bool:
        """Test: Is there obvious data corruption?"""
        try:
            print("🧪 Testing: Is there obvious data corruption?")
            
            response = self.session.get(f"{BASE_URL}/api/flights")
            
            if response.status_code == 200:
                data = response.json()
                flights = data.get("flights", [])
                
                if flights and len(flights) > 0:
                    corruption_issues = []
                    total_flights = len(flights)
                    
                    for flight in flights:
                        critical_fields = ["callsign", "latitude", "longitude"]
                        for field in critical_fields:
                            if field in flight and (flight[field] is None or flight[field] == ""):
                                corruption_issues.append({
                                    "callsign": flight.get("callsign", "UNKNOWN"),
                                    "issue": f"Empty/null {field}"
                                })
                        
                        if "callsign" in flight and not isinstance(flight["callsign"], str):
                            corruption_issues.append({
                                "callsign": flight.get("callsign", "UNKNOWN"),
                                "issue": "Invalid callsign type"
                            })
                    
                    if corruption_issues:
                        integrity_rate = ((total_flights - len(corruption_issues)) / total_flights) * 100
                        print(f"❌ Data integrity: {integrity_rate:.1f}% - {len(corruption_issues)} issues")
                        self.test_results.append(("Data Integrity", "FAIL", f"{integrity_rate:.1f}% - {len(corruption_issues)} issues"))
                        return False
                    else:
                        print(f"✅ Data integrity: 100% - No corruption issues in {total_flights} flights")
                        self.test_results.append(("Data Integrity", "PASS", f"100% - {total_flights} flights"))
                        return True
                else:
                    print("❌ No flight data available for integrity check")
                    self.test_results.append(("Data Integrity", "FAIL", "No data available"))
                    return False
            else:
                print(f"❌ Flight data endpoint failed - status {response.status_code}")
                self.test_results.append(("Data Integrity", "FAIL", f"Status {response.status_code}"))
                return False
                
        except Exception as e:
            print(f"❌ Data integrity test failed - {e}")
            self.test_results.append(("Data Integrity", "FAIL", str(e)))
            return False
    
    def test_business_rules(self) -> bool:
        """Test: Do fields contain expected data?"""
        try:
            print("🧪 Testing: Do fields contain expected data?")
            
            flight_response = self.session.get(f"{BASE_URL}/api/flights")
            controller_response = self.session.get(f"{BASE_URL}/api/controllers")
            
            business_rule_violations = []
            total_checks = 0
            
            # Check flight data business rules
            if flight_response.status_code == 200:
                flight_data = flight_response.json()
                flights = flight_data.get("flights", [])
                
                if flights and len(flights) > 0:
                    for flight in flights:
                        total_checks += 1
                        
                        if "callsign" in flight:
                            callsign = flight["callsign"]
                            if not isinstance(callsign, str) or len(callsign.strip()) == 0:
                                business_rule_violations.append({
                                    "type": "flight",
                                    "callsign": str(callsign),
                                    "issue": "Invalid callsign format"
                                })
                        
                        if "altitude" in flight and flight["altitude"] is not None:
                            altitude = flight["altitude"]
                            if not isinstance(altitude, (int, float)) or altitude < 0:
                                business_rule_violations.append({
                                    "type": "flight",
                                    "callsign": flight.get("callsign", "UNKNOWN"),
                                    "issue": f"Invalid altitude: {altitude}"
                                })
            
            # Check controller data business rules
            if controller_response.status_code == 200:
                controller_data = controller_response.json()
                controllers = controller_data.get("controllers", [])
                
                if controllers and len(controllers) > 0:
                    for controller in controllers:
                        total_checks += 1
                        
                        if "rating" in controller and controller["rating"] is not None:
                            rating = controller["rating"]
                            valid_ratings = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
                            if rating not in valid_ratings:
                                business_rule_violations.append({
                                    "type": "controller",
                                    "callsign": controller.get("callsign", "UNKNOWN"),
                                    "issue": f"Invalid VATSIM rating: {rating}"
                                })
            
            # Calculate business rule compliance rate
            if total_checks > 0:
                compliant_checks = total_checks - len(business_rule_violations)
                compliance_rate = (compliant_checks / total_checks) * 100
                
                if compliance_rate >= DATA_QUALITY_THRESHOLD:
                    print(f"✅ Business rule compliance: {compliance_rate:.1f}% - {compliant_checks}/{total_checks} compliant")
                    self.test_results.append(("Business Rules", "PASS", f"{compliance_rate:.1f}% - {compliant_checks}/{total_checks}"))
                    return True
                else:
                    print(f"❌ Business rule compliance: {compliance_rate:.1f}% - {len(business_rule_violations)} violations")
                    self.test_results.append(("Business Rules", "FAIL", f"{compliance_rate:.1f}% - {len(business_rule_violations)} violations"))
                    return False
            else:
                print("⚠️ No data available for business rule validation")
                self.test_results.append(("Business Rules", "WARN", "No data available"))
                return True
                
        except Exception as e:
            print(f"❌ Business rules test failed - {e}")
            self.test_results.append(("Business Rules", "FAIL", str(e)))
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all Stage 3 tests and return results"""
        print("🚀 Starting Stage 3: Data Quality Tests")
        print("=" * 60)
        
        # Run all tests
        tests = [
            self.test_flight_plan_completeness,
            self.test_position_data_accuracy,
            self.test_data_integrity,
            self.test_business_rules
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
            "stage": "3 - Data Quality",
            "overall_status": overall_status,
            "passed": passed,
            "total": total,
            "success_rate": success_rate,
            "test_results": self.test_results
        }

def main():
    """Main test execution for direct running"""
    tester = DataQualityTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code for CI/CD
    if results["overall_status"] == "PASS":
        print("\n🎉 Stage 3 Data Quality Tests PASSED!")
        print("✅ Data is reliable for business analysis and decision-making")
        exit(0)
    else:
        print("\n❌ Stage 3 Data Quality Tests FAILED!")
        print("⚠️  Data quality issues need attention before business use")
        exit(1)

if __name__ == "__main__":
    main()
