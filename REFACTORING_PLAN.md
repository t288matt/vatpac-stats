# Data Service Refactoring Plan

## Current Issues
- DataService is over 3,500 lines with 81 methods
- Violates Single Responsibility Principle with multiple mixed concerns
- High coupling making changes risky
- Difficult to test individual components
- Challenges for new developers to understand and maintain

## Refactoring Strategy

### Phase 1: Extract Domain-Specific Services

1. **Create FlightProcessingService**
   - Extract `_process_flights()` and related methods
   - Move flight-specific filtering logic
   - Create dedicated repository for flight data operations

2. **Create ControllerProcessingService**
   - Extract `_process_controllers()` and related methods
   - Create dedicated repository for controller data operations

3. **Create TransceiverProcessingService**
   - Extract `_process_transceivers()` and related methods
   - Create dedicated repository for transceiver data operations

4. **Create CanonicalProcessingService**
   - Extract `_process_completed_flights_canonical()` and related methods
   - Implement clean interfaces with session_selector

5. **Create SectorTrackingService**
   - Extract sector tracking functionality
   - Implement clean event-based interfaces

### Phase 2: Create Data Access Layer

1. **Create Repository Classes**
   - FlightRepository
   - ControllerRepository
   - TransceiverRepository
   - FlightSummaryRepository
   - ControllerSummaryRepository

2. **Implement Transaction Management**
   - Create UnitOfWork pattern to manage transactions

### Phase 3: Create Orchestration Layer

1. **Transform DataService into Facade**
   - Slim down to basic coordination logic
   - Remove direct database operations
   - Use extracted services via dependency injection

2. **Implement Clean Interfaces Between Services**
   - Define clear contracts
   - Use events for cross-service communication

### Phase 4: Improve Error Handling and Resilience

1. **Standardize Error Handling**
   - Consistent approach across services
   - Better error reporting and recovery

2. **Implement Circuit Breakers**
   - Protect against cascading failures

### Implementation Approach

1. **Step-by-Step Extraction**
   - Start with one service (FlightProcessingService)
   - Test thoroughly before proceeding
   - Incrementally replace functionality in DataService

2. **Comprehensive Test Coverage**
   - Write tests for each extracted component
   - Ensure behavior is preserved during refactoring

3. **Documentation Updates**
   - Update architecture diagrams
   - Document new service responsibilities

## Expected Benefits

1. **Improved Maintainability**
   - Smaller, focused classes with clear responsibilities
   - Reduced risk when making changes

2. **Better Testability**
   - Isolated components easier to test
   - Mocking dependencies more straightforward

3. **Enhanced Onboarding**
   - New developers can understand components in isolation
   - Clearer documentation of responsibilities

4. **Future Extensibility**
   - New features can target specific services
   - Services can be optimized independently

