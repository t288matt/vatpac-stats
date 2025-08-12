#!/usr/bin/env python3
"""
Test Configuration and Utilities for VATSIM Data Collection System

This module provides test configuration, fixtures, and utilities for all test stages.
Focus: Simple, maintainable test setup with minimal complexity.

Author: VATSIM Data System
Stage: 1 - Foundation
"""

import os
import pytest
import requests
import time
from typing import Dict, Any, Optional

# Test configuration
TEST_CONFIG = {
    "base_url": os.getenv("TEST_BASE_URL", "http://localhost:8001"),
    "api_timeout": int(os.getenv("TEST_API_TIMEOUT", "30")),
    "wait_timeout": int(os.getenv("TEST_WAIT_TIMEOUT", "60")),
    "retry_attempts": int(os.getenv("TEST_RETRY_ATTEMPTS", "3")),
    "retry_delay": int(os.getenv("TEST_RETRY_DELAY", "5"))
}

class TestHelper:
    """Helper utilities for tests"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = TEST_CONFIG["api_timeout"]
    
    def wait_for_service(self, max_wait: int = None) -> bool:
        """Wait for service to be ready"""
        max_wait = max_wait or TEST_CONFIG["wait_timeout"]
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = self.session.get(f"{TEST_CONFIG['base_url']}/api/status")
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(2)
        
        return False
    
    def make_request(self, endpoint: str, method: str = "GET", **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retry logic"""
        url = f"{TEST_CONFIG['base_url']}{endpoint}"
        
        for attempt in range(TEST_CONFIG["retry_attempts"]):
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, **kwargs)
                elif method.upper() == "POST":
                    response = self.session.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                return response
                
            except Exception as e:
                if attempt == TEST_CONFIG["retry_attempts"] - 1:
                    print(f"Request failed after {TEST_CONFIG['retry_attempts']} attempts: {e}")
                    return None
                time.sleep(TEST_CONFIG["retry_delay"])
        
        return None
    
    def validate_response(self, response: requests.Response, expected_status: int = 200) -> bool:
        """Validate HTTP response"""
        if response is None:
            return False
        
        if response.status_code != expected_status:
            print(f"Expected status {expected_status}, got {response.status_code}")
            return False
        
        try:
            response.json()  # Ensure response is valid JSON
            return True
        except ValueError:
            print("Response is not valid JSON")
            return False

# Pytest fixtures
@pytest.fixture(scope="session")
def test_helper():
    """Provide test helper utilities"""
    return TestHelper()

@pytest.fixture(scope="session")
def base_url():
    """Provide base URL for tests"""
    return TEST_CONFIG["base_url"]

@pytest.fixture(scope="session")
def api_timeout():
    """Provide API timeout for tests"""
    return TEST_CONFIG["api_timeout"]

@pytest.fixture(scope="session")
def wait_timeout():
    """Provide wait timeout for tests"""
    return TEST_CONFIG["wait_timeout"]

# Test markers for different stages
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "stage1: marks tests as Stage 1 - Foundation tests"
    )
    config.addinivalue_line(
        "markers", "stage2: marks tests as Stage 2 - Core Functionality tests"
    )
    config.addinivalue_line(
        "markers", "stage3: marks tests as Stage 3 - Data Quality tests"
    )
    config.addinivalue_line(
        "markers", "stage4: marks tests as Stage 4 - Geographic Filtering tests"
    )
    config.addinivalue_line(
        "markers", "stage5: marks tests as Stage 5 - Flight Summaries tests"
    )
    config.addinivalue_line(
        "markers", "stage6: marks tests as Stage 6 - Integration tests"
    )

# Test utilities
def print_test_header(stage: str, description: str):
    """Print formatted test header"""
    print(f"\n{'='*60}")
    print(f"🚀 {stage}")
    print(f"📝 {description}")
    print(f"{'='*60}")

def print_test_result(test_name: str, status: str, details: str = ""):
    """Print formatted test result"""
    icon = "✅" if status == "PASS" else "❌"
    print(f"{icon} {test_name}: {status}")
    if details:
        print(f"   📋 {details}")

def calculate_success_rate(passed: int, total: int) -> float:
    """Calculate test success rate"""
    return (passed / total * 100) if total > 0 else 0.0

def get_overall_status(success_rate: float, threshold: float = 75.0) -> str:
    """Determine overall test status"""
    return "PASS" if success_rate >= threshold else "FAIL"
