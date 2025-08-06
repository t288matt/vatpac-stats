# Flight Filtering System

## Overview
This document outlines the requirements for implementing a simplified flight filter to only include flights that have either origin or destination in Australia, using simple airport code validation.

## Requirements

### 1. Filtering Criteria
- **Inclusion Logic**: Keep flights that have either origin OR destination airport code that exists in the `australian_airports` database view
- **Exclusion Logic**: Discard flights where both origin AND destination airport codes do not exist in the `australian_airports` database view
- **Determination Method**: Check departure and arrival airport codes against the `australian_airports` database view
- **Scope**: Only applies to flight data (pilots) - controllers are out of scope and remain unfiltered

### 2. Processing Location
- **Stage**: Apply filter immediately after receiving data from VATSIM API
- **Timing**: Before any database operations or further processing
- **Purpose**: Early filtering to reduce processing load and storage requirements
- **Architecture**: Separate pre-processor component, not integrated with existing services

### 3. Flight Analysis
The system should consider:
- **Departure Airport**: Check if departure airport code exists in the `australian_airports` database view
- **Arrival Airport**: Check if arrival airport code exists in the `australian_airports` database view
- **Flight Plan Data**: Extract airport codes from flight plan information
- **Database Lookup**: Use the existing `is_australian_airport()` function from the configuration

### 4. Configuration
- **Method**: Environment variables for filter settings
- **Example**: `FLIGHT_FILTER_ENABLED="true"`
- **Validation**: Ensure filter is properly configured and enabled
- **Database Integration**: Use existing Australian airports database functions

### 5. Disposition of Filtered Flights
- **Action**: Completely discard flights where both origin and destination are not in the Australian airports database
- **No Storage**: Do not store filtered-out flights in any database tables
- **No Processing**: Do not apply any further processing to discarded flights
- **Output Format**: Return VATSIM API data with identical structure, just without the filtered flights
- **Data Integrity**: All other VATSIM data (controllers, servers, general info) remains unchanged

## Technical Implementation Considerations

### Architecture Requirements
- **Separation**: Filter should be implemented as a standalone pre-processor component
- **Modularity**: No integration with existing services - operates independently
- **Interface**: Clean API interface for receiving VATSIM data and returning filtered results
- **Deployment**: Can be deployed as separate container/service if needed

### Performance Requirements
- **Speed**: Filtering must be fast enough to not delay data ingestion
- **Memory**: Simple database lookup for airport code validation
- **Scalability**: Handle high volume of flight data efficiently

### Algorithm Requirements
- **Database Lookup**: Use existing `is_australian_airport()` function for validation
- **Flight Plan Parsing**: Extract departure and arrival airport codes
- **Logical OR Operation**: Include if either departure OR arrival exists in Australian airports database

### Error Handling
- **Missing Flight Plan**: Handle flights with incomplete flight plan information
- **Invalid Airport Codes**: Handle malformed or missing airport codes
- **Database Connection**: Handle database connectivity issues gracefully
- **Configuration Errors**: Validate filter configuration on startup

## Environment Variables Structure

```bash
# Enable/disable the filter
FLIGHT_FILTER_ENABLED="true"

# Logging level for filter operations
FLIGHT_FILTER_LOG_LEVEL="INFO"
```

## Success Criteria
1. Flights with Australian origin OR destination (from database) are retained for processing
2. Flights with non-Australian origin AND destination (from database) are completely discarded
3. Filtering occurs before any database operations
4. Configuration can be changed via environment variables
5. System performance is not significantly impacted by filtering
6. Proper logging of filtering decisions for monitoring
7. Output data structure is identical to input structure (same JSON format, field names, etc.)
8. Only filtered flights are removed - all other data (controllers, servers, etc.) remains unchanged

## Implementation Structure

### Component Design
- **Filter Service**: Standalone service with clear input/output interface
- **Configuration Module**: Separate configuration management for filter settings
- **Database Integration**: Use existing Australian airports database functions
- **Logging Module**: Independent logging for filter operations and decisions

### Integration Points
- **Input**: Receives raw VATSIM API data
- **Output**: Returns filtered VATSIM API data with identical structure, just without filtered flights
- **Data Structure**: Output maintains exact same format as input (JSON structure, field names, etc.)
- **Configuration**: Environment variables for filter settings
- **Database**: Use existing `australian_airports` view and `is_australian_airport()` function
- **Monitoring**: Separate metrics and health checks

## Database Integration

### Australian Airports Database View
The filter will use the existing `australian_airports` database view:

```sql
CREATE OR REPLACE VIEW australian_airports AS
SELECT 
    icao_code,
    name,
    latitude,
    longitude,
    country,
    region
FROM airports 
WHERE icao_code LIKE 'Y%' AND is_active = true;
```

### Configuration Functions
The filter will leverage existing configuration functions:
- `is_australian_airport(airport_code: str) -> bool`: Check if airport code is Australian
- `get_australian_airports() -> list`: Get all Australian airport codes from database
- `get_major_australian_airports() -> list`: Get major Australian airport codes from database

### Database Schema
The filter relies on the existing `airports` table structure:
- `icao_code`: Airport ICAO code (e.g., 'YMML', 'YSSY')
- `name`: Airport name
- `latitude`: Airport latitude
- `longitude`: Airport longitude
- `country`: Country code
- `region`: Region information
- `is_active`: Whether the airport is active

## Australian Airport Coverage
The filter will include flights where either the departure or arrival airport code exists in the `australian_airports` database view, which includes:
- **Major Airports**: YMML (Melbourne), YSSY (Sydney), YBBN (Brisbane), YPPH (Perth)
- **Regional Airports**: YSCB (Canberra), YMHB (Hobart), YPDN (Darwin), YBCS (Cairns)
- **All Australian Airports**: Any airport code starting with 'Y' that exists in the database and is marked as active

## Future Enhancements
- Support for additional regions using similar airport code patterns
- Dynamic filter updates without restart
- More sophisticated airport code validation
- Integration with additional airport database tables for enhanced filtering 