"""
VATSIM Data Collection System - Regression Test Pack

This package contains comprehensive regression tests designed to prevent
unexpected application breakage by validating the complete data flow
from VATSIM API through all services to database tables.

Test Categories:
- Core: End-to-end data flow validation
- Services: Service-level regression tests  
- Filters: Filter pipeline validation
- Models: Database model integrity tests
- Integration: Cross-component integration tests
- Performance: Performance regression tests

Usage:
    # Run all regression tests
    pytest tests/regression/ -v

    # Run specific category
    pytest tests/regression/core/ -v
    pytest tests/regression/filters/ -v
    
    # Run with coverage
    pytest tests/regression/ --cov=app --cov-report=html

    # Run performance tests only
    pytest tests/regression/performance/ -v
"""

__version__ = "1.0.0"
