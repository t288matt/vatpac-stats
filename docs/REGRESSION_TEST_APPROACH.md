# Regression Test Pack - Approach & Design

## Overview

The VATSIM Data Collection System Regression Test Pack is designed to prevent unexpected application breakage by providing comprehensive coverage of all components and the complete data flow from API to database tables.

## Problem Statement

**Current Issues:**
- Frequent regressions break the application unexpectedly
- Changes to one component can break others without detection
- No systematic validation of complete data flow
- Limited confidence in deployments

**Solution:**
Comprehensive regression test pack that validates every step of the data pipeline and catches breaking changes before they reach production.

## Testing Philosophy

### Core Principles

1. **Complete Data Flow Coverage**
   - Test every step from VATSIM API to database tables
   - Validate data transformations at each stage
   - Ensure filters work correctly in sequence

2. **Known Input → Expected Output**
   - Use controlled test data with predictable results
   - Mock external dependencies (VATSIM API)
   - Validate exact expected outcomes

3. **Fail Fast, Fail Clear**
   - Tests should fail immediately when regressions occur
   - Clear error messages indicating what broke
   - Pinpoint exact component or step that failed

4. **Realistic Test Scenarios**
   - Use real-world data patterns
   - Test edge cases and error conditions
   - Validate performance under load

## Architecture Overview

### Data Flow Under Test

```
VATSIM API → VATSIM Service → Flight Filters → Data Service → Database Tables
     ↓              ↓              ↓              ↓              ↓
  Mock API    Parse/Transform  Filter Pipeline  Memory Cache   PostgreSQL
```

### Test Categories

#### 1. **Core Data Flow Tests** (`tests/regression/core/`)
**Purpose**: Validate complete end-to-end data pipeline

**Key Tests:**
- `test_vatsim_api_to_database_complete_flow()`: Full pipeline validation
- `test_data_transformation_accuracy()`: Field mapping and type conversion
- `test_filter_pipeline_integration()`: Sequential filter application

**Approach:**
```python
# Input: Known VATSIM API response
test_data = {
    "pilots": [
        {"callsign": "QFA123", "departure": "YSSY", "latitude": -33.8688, ...},  # Australian
        {"callsign": "UAL456", "departure": "EGLL", "latitude": 51.5074, ...}   # Non-Australian
    ],
    "controllers": [...]
}

# Process: Trigger full data ingestion
vatsim_data = await vatsim_service.get_current_data()
await data_service.process_data(vatsim_data)

# Verify: Check database contains expected data
flights = db.query(Flight).all()
assert len(flights) == 1  # Only Australian flight
assert flights[0].callsign == "QFA123"
```

#### 2. **Filter Pipeline Tests** (`tests/regression/filters/`)
**Purpose**: Validate filtering logic works correctly

**Key Tests:**
- `test_airport_filter_y_code_detection()`: Australian airport identification
- `test_geographic_filter_polygon_accuracy()`: Point-in-polygon calculations
- `test_filter_performance_requirements()`: Processing time validation

**Approach:**
```python
# Test airport filter with known cases
test_cases = [
    ("YSSY", "YBBN", True),   # Both Australian → Pass
    ("EGLL", "KLAX", False),  # Neither Australian → Fail
    ("YSSY", None, True),     # Missing dest, Aus origin → Pass
]

for departure, arrival, expected in test_cases:
    result = flight_filter.should_include_flight({"departure": departure, "arrival": arrival})
    assert result == expected
```

#### 3. **Database Integrity Tests** (`tests/regression/models/`)
**Purpose**: Ensure database schema and relationships work correctly

**Key Tests:**
- `test_model_field_completeness()`: All required fields present
- `test_foreign_key_relationships()`: Controller ↔ Sector relationships
- `test_unique_constraints()`: Duplicate prevention

**Approach:**
```python
# Test unique constraint on flights
flight1 = Flight(callsign="QFA123", last_updated=datetime(2024,1,1,12,0,0))
flight2 = Flight(callsign="QFA123", last_updated=datetime(2024,1,1,12,1,0))

db.add_all([flight1, flight2])
db.commit()

# Should create 2 records (different timestamps)
flights = db.query(Flight).filter(Flight.callsign == "QFA123").all()
assert len(flights) == 2
```

#### 4. **Service Integration Tests** (`tests/regression/services/`)
**Purpose**: Validate individual services work correctly

**Key Tests:**
- `test_vatsim_service_api_parsing()`: API response parsing
- `test_data_service_memory_optimization()`: Memory caching behavior
- `test_cache_service_performance()`: Cache hit/miss rates

#### 5. **Error Scenario Tests** (`tests/regression/integration/`)
**Purpose**: Test system resilience to failures

**Key Tests:**
- `test_malformed_api_data_handling()`: Invalid JSON, missing fields
- `test_database_connection_loss()`: Recovery from DB failures
- `test_concurrent_request_handling()`: Race condition prevention

#### 6. **Performance Tests** (`tests/regression/performance/`)
**Purpose**: Prevent performance regressions

**Key Tests:**
- `test_api_response_times()`: Endpoint performance
- `test_large_dataset_processing()`: Scalability validation
- `test_memory_usage_limits()`: Memory leak detection

## Test Data Strategy

### Golden Dataset Approach

**Concept**: Use a carefully crafted dataset with known expected outcomes

```python
GOLDEN_VATSIM_RESPONSE = {
    "pilots": [
        # Test case 1: Australian flight (should pass all filters)
        {
            "callsign": "QFA123",
            "cid": 123456,
            "latitude": -33.8688,     # Sydney coordinates
            "longitude": 151.2093,
            "flight_plan": {
                "departure": "YSSY",  # Australian airport
                "arrival": "YBBN"     # Australian airport
            }
        },
        # Test case 2: Non-Australian flight (should be filtered out)
        {
            "callsign": "UAL456", 
            "latitude": 51.5074,     # London coordinates
            "longitude": -0.1278,
            "flight_plan": {
                "departure": "EGLL",  # Non-Australian
                "arrival": "KLAX"     # Non-Australian
            }
        },
        # Test case 3: Edge case - missing coordinates (conservative handling)
        {
            "callsign": "QFA789",
            "latitude": None,
            "longitude": None,
            "flight_plan": {
                "departure": "YSSY",  # Australian
                "arrival": "YBBN"     # Australian
            }
        }
    ],
    "controllers": [
        # Test case: String ID conversion
        {
            "cid": "345678",          # String from API
            "name": "Test Controller",
            "callsign": "SY_APP",
            "rating": "3"             # String from API
        }
    ]
}
```

### Expected Outcomes

```python
EXPECTED_DATABASE_STATE = {
    "flights": [
        {"callsign": "QFA123", "departure": "YSSY", "arrival": "YBBN"},  # Passed filters
        {"callsign": "QFA789", "departure": "YSSY", "arrival": "YBBN"}   # Missing coords allowed
        # UAL456 should NOT be present (filtered out)
    ],
    "controllers": [
        {"callsign": "SY_APP", "controller_id": 345678}  # String converted to int
    ]
}
```

## Mock Strategy

### VATSIM API Mock

**Purpose**: Provide controlled, repeatable API responses

```python
class VATSIMAPIMock:
    def __init__(self):
        self.responses = {}
        self.error_conditions = {}
    
    def set_response(self, endpoint, data):
        """Set mock response for endpoint"""
        self.responses[endpoint] = data
    
    def set_error_condition(self, endpoint, error_type):
        """Simulate API errors"""
        self.error_conditions[endpoint] = error_type
```

**Usage:**
```python
@pytest.fixture
def vatsim_api_mock():
    mock = VATSIMAPIMock()
    mock.set_response("/v3/vatsim-data.json", GOLDEN_VATSIM_RESPONSE)
    return mock
```

### Database Isolation

**Purpose**: Clean database state for each test

```python
@pytest.fixture
def clean_database():
    """Clean database state for each test"""
    db = SessionLocal()
    try:
        # Truncate all tables in correct order (respecting foreign keys)
        db.execute("TRUNCATE TABLE frequency_matches CASCADE")
        db.execute("TRUNCATE TABLE transceivers CASCADE") 
        db.execute("TRUNCATE TABLE flights CASCADE")
        db.execute("TRUNCATE TABLE controllers CASCADE")
        db.execute("TRUNCATE TABLE sectors CASCADE")
        db.commit()
    finally:
        db.close()
```

## Performance Requirements

### Response Time Targets

| Component | Target | Measurement |
|-----------|--------|-------------|
| API Endpoints | < 1s | 95th percentile |
| Filter Pipeline | < 100ms | 1000 flights |
| Database Queries | < 500ms | Complex joins |
| Memory Usage | < 512MB | Peak usage |

### Load Testing Scenarios

```python
def test_large_dataset_performance():
    """Test processing 1000 flights + 100 controllers in < 30 seconds"""
    large_dataset = generate_test_dataset(flights=1000, controllers=100)
    
    start_time = time.time()
    await process_complete_dataset(large_dataset)
    processing_time = time.time() - start_time
    
    assert processing_time < 30.0
```

## Error Handling Strategy

### Error Categories

1. **External API Errors**
   - Network timeouts
   - HTTP 500 errors
   - Malformed JSON responses

2. **Data Validation Errors**
   - Invalid data types
   - Missing required fields
   - Out-of-range values

3. **Database Errors**
   - Connection failures
   - Constraint violations
   - Transaction rollbacks

### Test Approach

```python
def test_malformed_api_response():
    """Test graceful handling of invalid API data"""
    malformed_data = {
        "pilots": [
            {"callsign": "TEST", "cid": "not_a_number"}  # Invalid type
        ]
    }
    
    # Should not crash, should log error, should skip invalid record
    result = await process_data(malformed_data)
    
    assert result.errors_count > 0
    assert result.processed_count == 0
    assert len(db.query(Flight).all()) == 0  # No invalid data stored
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Regression Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  regression-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: vatsim_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run regression tests
      run: |
        pytest tests/regression/ -v --cov=app --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:test@localhost:5432/vatsim_test
        REDIS_URL: redis://localhost:6379
        ENVIRONMENT: test
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Test Execution Levels

**Level 1: Fast (< 5 minutes)**
```bash
pytest tests/regression/core/ tests/regression/filters/ -v
```

**Level 2: Medium (< 15 minutes)**
```bash
pytest tests/regression/ -k "not performance" -v
```

**Level 3: Full (< 30 minutes)**
```bash
pytest tests/regression/ -v --cov=app
```

## Maintenance Strategy

### Baseline Management

**Concept**: Maintain known-good test results for comparison

```python
class BaselineManager:
    def save_baseline(self, test_results, version):
        """Save test results as baseline for future comparison"""
        
    def detect_regressions(self, current_results, baseline_results):
        """Compare current results against baseline"""
        
    def generate_regression_report(self, regressions):
        """Generate detailed regression report"""
```

### Test Data Updates

**When to Update Golden Dataset:**
- VATSIM API structure changes
- New filter requirements
- Database schema modifications
- Performance requirement changes

**Update Process:**
1. Validate new test data manually
2. Update expected outcomes
3. Run full regression suite
4. Update baselines if all tests pass

## Success Metrics

### Coverage Targets

- **API Endpoints**: 100% of public endpoints
- **Database Models**: 100% of models and relationships
- **Services**: 100% of service interfaces
- **Data Flow**: 100% of critical data paths
- **Error Scenarios**: 90% of error conditions

### Quality Gates

- **Zero Regressions**: All regression tests must pass before merge
- **Performance SLA**: No endpoint >20% slower than baseline
- **Data Integrity**: 100% data integrity validation must pass
- **Error Handling**: All error scenarios handled gracefully

### Reporting

**Test Results Dashboard:**
- Pass/fail status for each category
- Performance trend analysis
- Coverage metrics
- Error rate tracking

**Alerts:**
- Immediate notification on regression test failures
- Performance degradation alerts
- Coverage drop notifications

## Implementation Timeline

### Phase 1: Foundation (Week 1)
- Core data flow tests
- Basic filter tests
- Database integrity tests

### Phase 2: Service Tests (Week 2)
- Service integration tests
- Error scenario tests
- Performance baseline establishment

### Phase 3: CI/CD Integration (Week 3)
- GitHub Actions workflow
- Automated reporting
- Alert configuration

### Phase 4: Documentation & Training (Week 4)
- Usage documentation
- Team training
- Maintenance procedures

This approach provides comprehensive protection against regressions while being maintainable and integrated into the development workflow.
