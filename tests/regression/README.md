# VATSIM Data Collection System - Regression Test Pack

## Overview

This regression test pack provides comprehensive coverage of the complete data flow from VATSIM API through all services to database tables. It's designed to prevent unexpected application breakage and catch regressions before they reach production.

## Quick Start

### Run All Regression Tests
```bash
pytest tests/regression/ -v
```

### Run Specific Test Categories
```bash
# Core data flow tests
pytest tests/regression/core/ -v

# Filter pipeline tests  
pytest tests/regression/filters/ -v

# Database model tests
pytest tests/regression/models/ -v

# Service integration tests
pytest tests/regression/services/ -v

# Performance tests
pytest tests/regression/performance/ -v
```

### Run with Coverage
```bash
pytest tests/regression/ --cov=app --cov-report=html --cov-report=term
```

## Test Structure

```
tests/regression/
├── __init__.py                 # Package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── pytest.ini                 # Pytest settings
├── README.md                   # This file
├── core/                       # Core data flow tests
│   ├── __init__.py
│   ├── test_data_flow.py       # End-to-end data flow validation
│   ├── test_api_contracts.py   # API contract validation
│   └── test_database_integrity.py # Database integrity tests
├── filters/                    # Filter pipeline tests
│   ├── __init__.py
│   ├── test_flight_filter.py   # Airport filter tests
│   └── test_geographic_filter.py # Geographic boundary filter tests
├── models/                     # Database model tests
│   ├── __init__.py
│   ├── test_model_integrity.py # Model validation tests
│   └── test_model_relationships.py # Relationship tests
├── services/                   # Service integration tests
│   ├── __init__.py
│   ├── test_vatsim_service.py  # VATSIM service tests
│   ├── test_data_service.py    # Data service tests
│   └── test_cache_service.py   # Cache service tests
├── integration/                # Cross-component tests
│   ├── __init__.py
│   ├── test_complete_workflow.py # Full workflow tests
│   └── test_error_scenarios.py # Error handling tests
└── performance/                # Performance regression tests
    ├── __init__.py
    ├── test_response_times.py  # API response time tests
    └── test_memory_usage.py    # Memory usage tests
```

## Test Categories

### 🔄 Core Data Flow Tests
**Purpose**: Validate complete VATSIM API → Database pipeline

**Key Tests**:
- End-to-end data ingestion with known test data
- Data transformation accuracy (string → int conversion, field mapping)
- Filter pipeline integration (airport + geographic filters)

**Example**:
```python
def test_complete_data_flow(golden_vatsim_data, expected_database_state):
    # Process known VATSIM data through complete pipeline
    # Verify only expected data reaches database with correct transformations
```

### 🔍 Filter Pipeline Tests  
**Purpose**: Validate filtering logic works correctly

**Key Tests**:
- Airport filter Y-code detection accuracy
- Geographic filter point-in-polygon calculations
- Filter performance requirements

**Example**:
```python
def test_airport_filter_accuracy(airport_filter_test_cases):
    # Test all combinations of Australian/non-Australian airports
    # Verify correct filtering decisions
```

### 🗄️ Database Model Tests
**Purpose**: Ensure database integrity and relationships

**Key Tests**:
- Model field completeness and data types
- Foreign key relationships (Controller ↔ Sector)
- Unique constraints and duplicate handling

### ⚙️ Service Integration Tests
**Purpose**: Validate individual services work correctly

**Key Tests**:
- VATSIM service API parsing and error handling
- Data service memory optimization and batch operations
- Cache service performance and reliability

### 🚨 Error Scenario Tests
**Purpose**: Test system resilience to failures

**Key Tests**:
- Malformed API data handling
- Database connection failures
- Network timeout recovery

### ⚡ Performance Tests
**Purpose**: Prevent performance regressions

**Key Tests**:
- API response time requirements
- Large dataset processing performance
- Memory usage validation

## Test Data Strategy

### Golden Dataset
The regression tests use a carefully crafted "golden dataset" with known expected outcomes:

```python
# Input: Known VATSIM API response
golden_data = {
    "pilots": [
        {"callsign": "QFA123", "departure": "YSSY", "latitude": -33.8688, ...},  # Australian
        {"callsign": "UAL456", "departure": "EGLL", "latitude": 51.5074, ...}   # Non-Australian
    ]
}

# Expected: Only Australian flight in database
expected_flights = [
    {"callsign": "QFA123", "departure": "YSSY", "arrival": "YBBN"}
]
```

### Mock VATSIM API
Tests use a controllable mock VATSIM API:

```python
# Set up controlled responses
vatsim_api_mock.set_response("/v3/vatsim-data.json", golden_data)

# Simulate error conditions
vatsim_api_mock.set_error_condition("/v3/vatsim-data.json", "timeout")
```

## Performance Requirements

| Component | Requirement | Test |
|-----------|-------------|------|
| API Endpoints | < 1s response time | `test_api_response_times` |
| Filter Pipeline | < 100ms for 1000 flights | `test_filter_performance` |
| Database Queries | < 500ms for complex joins | `test_query_performance` |
| Memory Usage | < 512MB peak usage | `test_memory_limits` |

## Markers

Use pytest markers to run specific test types:

```bash
# Run only performance tests
pytest tests/regression/ -m performance

# Run everything except slow tests
pytest tests/regression/ -m "not slow"

# Run core and filter tests
pytest tests/regression/ -m "core or filters"
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Regression Tests
on: [push, pull_request]

jobs:
  regression:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run regression tests
      run: pytest tests/regression/ -v --cov=app
```

### Test Levels for CI/CD

**Level 1: Fast (< 5 minutes)**
```bash
pytest tests/regression/core/ tests/regression/filters/ -v
```

**Level 2: Medium (< 15 minutes)**  
```bash
pytest tests/regression/ -m "not performance" -v
```

**Level 3: Full (< 30 minutes)**
```bash
pytest tests/regression/ -v --cov=app
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root
   cd /path/to/vatsim-data
   pytest tests/regression/
   ```

2. **Database Connection Issues**
   ```bash
   # Check database environment variables
   echo $DATABASE_URL
   echo $TEST_DATABASE_URL  # When test DB is implemented
   ```

3. **Mock Service Issues**
   ```bash
   # Run with verbose output to see mock calls
   pytest tests/regression/ -v -s
   ```

### Debug Mode
```bash
# Run with debugging output
pytest tests/regression/ -v -s --tb=long

# Run single test with debugging
pytest tests/regression/core/test_data_flow.py::test_complete_data_flow -v -s
```

## Contributing

### Adding New Regression Tests

1. **Identify the regression risk**: What could break?
2. **Create test data**: Use golden dataset approach
3. **Write the test**: Follow existing patterns
4. **Verify expected outcomes**: Ensure test catches the regression
5. **Add to appropriate category**: core/filters/models/services/etc.

### Test Naming Convention
```python
def test_[component]_[scenario]_[expected_outcome]():
    """Test [component] [does what] when [scenario] occurs"""
```

Examples:
- `test_airport_filter_correctly_identifies_australian_airports()`
- `test_data_service_handles_malformed_api_data_gracefully()`
- `test_geographic_filter_processes_missing_coordinates_conservatively()`

### Performance Test Guidelines
- Use realistic data volumes
- Set clear performance thresholds
- Measure actual processing time
- Test memory usage patterns
- Validate under load conditions

This regression test pack provides comprehensive protection against unexpected breakage while being maintainable and integrated into the development workflow.
