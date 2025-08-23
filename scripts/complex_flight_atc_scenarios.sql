-- Complex Flight ATC Frequency Scenarios
-- 
-- This file contains 40 different complex flight scenarios with calculated
-- ATC frequency coverage percentages across various sectors and operational patterns.
--
-- These scenarios represent real-world VATSIM operations including:
-- - Military flights with multiple frequency handoffs
-- - Long-haul operations with controller shift changes
-- - Emergency operations and priority handling
-- - Formation flights and complex coordination
-- - Weather diversions and instrument approaches
--
-- Usage: Reference for testing and validating ATC frequency analysis queries
-- Created: 2025-01-27
--

-- ============================================================================
-- SCENARIO 1-20: BASIC TO MODERATE COMPLEXITY
-- ============================================================================

/*
Scenario 1: Simple Two-Sector Flight
- Sector A: 30 min total, 0-15 min no ATC, 15-30 min on ATC
- Sector B: 20 min total, 0-10 min on ATC, 10-20 min no ATC
- Result: Sector A = 50%, Sector B = 50%, Overall = 50%

Scenario 2: Early ATC Contact
- Sector A: 45 min total, 0-5 min no ATC, 5-45 min on ATC
- Result: Overall = 89%

Scenario 3: Late ATC Contact
- Sector A: 60 min total, 0-50 min no ATC, 50-60 min on ATC
- Result: Overall = 17%

Scenario 4: Mid-Sector Frequency Change
- Sector A: 40 min total, 0-10 min no ATC, 10-25 min on ATC, 25-40 min no ATC
- Result: Overall = 37.5%

Scenario 5: Multiple Frequency Switches
- Sector A: 90 min total, 0-15 no ATC, 15-30 on ATC, 30-45 no ATC, 45-75 on ATC, 75-90 no ATC
- Result: Overall = 50%

Scenario 6: High-Frequency Sector
- Sector A: 120 min total, 0-10 no ATC, 10-120 on ATC
- Result: Overall = 92%

Scenario 7: Low-Frequency Sector
- Sector A: 180 min total, 0-150 no ATC, 150-180 on ATC
- Result: Overall = 17%

Scenario 8: Alternating Pattern
- Sector A: 100 min total, 0-10 on ATC, 10-20 no ATC, 20-30 on ATC, 30-40 no ATC, 40-50 on ATC, 50-100 no ATC
- Result: Overall = 30%

Scenario 9: Three-Sector Increasing Coverage
- Sector A: 30 min total, 0-20 no ATC, 20-30 on ATC (33%)
- Sector B: 45 min total, 0-15 no ATC, 15-45 on ATC (67%)
- Sector C: 60 min total, 0-10 no ATC, 10-60 on ATC (83%)
- Result: Overall = 67%

Scenario 10: Three-Sector Decreasing Coverage
- Sector A: 60 min total, 0-50 on ATC, 50-60 no ATC (83%)
- Sector B: 45 min total, 0-30 on ATC, 30-45 no ATC (67%)
- Sector C: 30 min total, 0-10 on ATC, 10-30 no ATC (33%)
- Result: Overall = 64%

Scenario 11: Very Short Sectors
- Sector A: 5 min total, 0-2 no ATC, 2-5 on ATC (60%)
- Sector B: 8 min total, 0-8 on ATC (100%)
- Sector C: 3 min total, 0-3 no ATC (0%)
- Result: Overall = 69%

Scenario 12: Very Long Sectors
- Sector A: 300 min total, 0-50 no ATC, 50-300 on ATC (83%)
- Sector B: 240 min total, 0-200 no ATC, 200-240 on ATC (17%)
- Result: Overall = 56%

Scenario 13: No ATC Contact
- Sector A: 60 min total, 0-60 no ATC
- Sector B: 45 min total, 0-45 no ATC
- Result: Overall = 0%

Scenario 14: Full ATC Contact
- Sector A: 90 min total, 0-90 on ATC
- Sector B: 75 min total, 0-75 on ATC
- Result: Overall = 100%

Scenario 15: Erratic Pattern
- Sector A: 120 min total, 0-10 on ATC, 10-20 no ATC, 20-25 on ATC, 25-35 no ATC, 35-40 on ATC, 40-120 no ATC
- Result: Overall = 25%

Scenario 16: Consistent Partial Coverage
- Sector A: 60 min total, 0-30 on ATC, 30-60 no ATC (50%)
- Sector B: 60 min total, 0-30 on ATC, 30-60 no ATC (50%)
- Sector C: 60 min total, 0-30 on ATC, 30-60 no ATC (50%)
- Result: Overall = 50%

Scenario 17: One-Sector Flight
- Sector A: 180 min total, 0-60 no ATC, 60-180 on ATC
- Result: Overall = 67%

Scenario 18: Many Small Sectors
- Sector A: 10 min total, 0-5 on ATC, 5-10 no ATC (50%)
- Sector B: 12 min total, 0-12 on ATC (100%)
- Sector C: 8 min total, 0-8 no ATC (0%)
- Sector D: 15 min total, 0-10 on ATC, 10-15 no ATC (67%)
- Sector E: 20 min total, 0-20 no ATC (0%)
- Result: Overall = 52%

Scenario 19: Sector Boundary Frequency Changes
- Sector A: 45 min total, 0-40 no ATC, 40-45 on ATC (11%)
- Sector B: 30 min total, 0-5 on ATC, 5-30 no ATC (17%)
- Result: Overall = 13%

Scenario 20: Complex Multi-Pattern
- Sector A: 90 min total, 0-15 no ATC, 15-30 on ATC, 30-45 no ATC, 45-75 on ATC, 75-90 no ATC (50%)
- Sector B: 60 min total, 0-10 on ATC, 10-20 no ATC, 20-40 on ATC, 40-50 no ATC, 50-60 on ATC (67%)
- Sector C: 45 min total, 0-45 no ATC (0%)
- Result: Overall = 44%
*/

-- ============================================================================
-- SCENARIO 21-40: HIGH COMPLEXITY REAL-WORLD OPERATIONS
-- ============================================================================

/*
Scenario 21: Military Flight with Multiple Frequency Handoffs
- Sector A: 45 min total, 0-5 no ATC, 5-15 on ATC freq 1, 15-25 no ATC, 25-35 on ATC freq 2, 35-45 no ATC
- Sector B: 60 min total, 0-10 on ATC freq 2, 10-20 no ATC, 20-30 on ATC freq 3, 30-40 no ATC, 40-50 on ATC freq 4, 50-60 no ATC
- Sector C: 30 min total, 0-5 on ATC freq 4, 5-15 no ATC, 15-25 on ATC freq 5, 25-30 no ATC
- Result: Overall = 47% (Complex frequency switching across sectors)

Scenario 22: Long-Haul with Controller Shift Changes
- Sector A: 180 min total, 0-30 no ATC, 30-60 on ATC freq 1, 60-90 no ATC, 90-120 on ATC freq 1, 120-150 no ATC, 150-180 on ATC freq 2
- Sector B: 240 min total, 0-60 on ATC freq 2, 60-120 no ATC, 120-180 on ATC freq 3, 180-240 no ATC
- Sector C: 120 min total, 0-30 no ATC, 30-60 on ATC freq 3, 60-90 no ATC, 90-120 on ATC freq 4
- Result: Overall = 38% (Controller handoffs and shift changes)

Scenario 23: VFR Flight with Multiple Approach Frequencies
- Sector A: 25 min total, 0-5 no ATC, 5-15 on ATC freq 1, 15-25 no ATC
- Sector B: 20 min total, 0-5 on ATC freq 1, 5-10 no ATC, 10-15 on ATC freq 2, 15-20 no ATC
- Sector C: 15 min total, 0-5 no ATC, 5-10 on ATC freq 2, 10-15 on ATC freq 3
- Sector D: 10 min total, 0-5 on ATC freq 3, 5-10 no ATC
- Result: Overall = 57% (Multiple approach frequency handoffs)

Scenario 24: Emergency Flight with Priority Handling
- Sector A: 15 min total, 0-2 no ATC, 2-15 on ATC freq 1 (emergency)
- Sector B: 20 min total, 0-20 on ATC freq 1 (emergency)
- Sector C: 25 min total, 0-5 on ATC freq 1, 5-15 no ATC, 15-25 on ATC freq 2
- Result: Overall = 75% (Emergency priority handling)

Scenario 25: Training Flight with Instructor
- Sector A: 90 min total, 0-10 no ATC, 10-25 on ATC freq 1, 25-35 no ATC, 35-50 on ATC freq 1, 50-65 no ATC, 65-80 on ATC freq 2, 80-90 no ATC
- Sector B: 60 min total, 0-15 on ATC freq 2, 15-30 no ATC, 30-45 on ATC freq 3, 45-60 no ATC
- Result: Overall = 42% (Training pattern with breaks)

Scenario 26: Cargo Flight with Multiple Stops
- Sector A: 120 min total, 0-20 no ATC, 20-40 on ATC freq 1, 40-60 no ATC, 60-80 on ATC freq 2, 80-100 no ATC, 100-120 on ATC freq 3
- Sector B: 90 min total, 0-15 on ATC freq 3, 15-30 no ATC, 30-45 on ATC freq 4, 45-60 no ATC, 60-75 on ATC freq 5, 75-90 no ATC
- Sector C: 75 min total, 0-10 no ATC, 10-25 on ATC freq 5, 25-40 no ATC, 40-55 on ATC freq 6, 55-75 no ATC
- Result: Overall = 44% (Multiple cargo stops with frequency changes)

Scenario 27: Helicopter Flight with Low-Level Operations
- Sector A: 30 min total, 0-5 no ATC, 5-15 on ATC freq 1, 15-25 no ATC, 25-30 on ATC freq 2
- Sector B: 45 min total, 0-10 on ATC freq 2, 10-20 no ATC, 20-30 on ATC freq 3, 30-40 no ATC, 40-45 on ATC freq 4
- Sector C: 20 min total, 0-5 no ATC, 5-15 on ATC freq 4, 15-20 no ATC
- Result: Overall = 53% (Low-level helicopter operations)

Scenario 28: Formation Flight with Lead Aircraft
- Sector A: 60 min total, 0-10 no ATC, 10-25 on ATC freq 1, 25-35 no ATC, 35-50 on ATC freq 2, 50-60 no ATC
- Sector B: 40 min total, 0-5 on ATC freq 2, 5-15 no ATC, 15-25 on ATC freq 3, 25-35 no ATC, 35-40 on ATC freq 4
- Result: Overall = 50% (Formation flight coordination)

Scenario 29: Air Ambulance with Priority Routing
- Sector A: 20 min total, 0-3 no ATC, 3-20 on ATC freq 1 (priority)
- Sector B: 25 min total, 0-25 on ATC freq 1 (priority)
- Sector C: 15 min total, 0-5 on ATC freq 1, 5-10 no ATC, 10-15 on ATC freq 2
- Result: Overall = 83% (Air ambulance priority handling)

Scenario 30: Test Flight with Multiple Systems
- Sector A: 75 min total, 0-10 no ATC, 10-20 on ATC freq 1, 20-30 no ATC, 30-40 on ATC freq 2, 40-50 no ATC, 50-60 on ATC freq 3, 60-75 no ATC
- Sector B: 60 min total, 0-15 on ATC freq 3, 15-25 no ATC, 25-35 on ATC freq 4, 35-45 no ATC, 45-55 on ATC freq 5, 55-60 no ATC
- Result: Overall = 42% (Test flight with multiple system checks)

Scenario 31: Weather Diversion with Multiple Approaches
- Sector A: 45 min total, 0-10 no ATC, 10-25 on ATC freq 1, 25-35 no ATC, 35-45 on ATC freq 2
- Sector B: 30 min total, 0-5 on ATC freq 2, 5-15 no ATC, 15-25 on ATC freq 3, 25-30 no ATC
- Sector C: 20 min total, 0-5 no ATC, 5-15 on ATC freq 3, 15-20 no ATC
- Result: Overall = 53% (Weather diversion routing)

Scenario 32: VIP Flight with Escort
- Sector A: 90 min total, 0-15 no ATC, 15-30 on ATC freq 1, 30-45 no ATC, 45-60 on ATC freq 2, 60-75 no ATC, 75-90 on ATC freq 3
- Sector B: 60 min total, 0-10 on ATC freq 3, 10-20 no ATC, 20-30 on ATC freq 4, 30-40 no ATC, 40-50 on ATC freq 5, 50-60 no ATC
- Result: Overall = 50% (VIP flight with escort coordination)

Scenario 33: Search and Rescue Mission
- Sector A: 120 min total, 0-20 no ATC, 20-40 on ATC freq 1, 40-60 no ATC, 60-80 on ATC freq 2, 80-100 no ATC, 100-120 on ATC freq 3
- Sector B: 90 min total, 0-15 on ATC freq 3, 15-30 no ATC, 30-45 on ATC freq 4, 45-60 no ATC, 60-75 on ATC freq 5, 75-90 no ATC
- Result: Overall = 44% (Search and rescue pattern)

Scenario 34: Aerial Survey Flight
- Sector A: 180 min total, 0-30 no ATC, 30-45 on ATC freq 1, 45-60 no ATC, 60-75 on ATC freq 2, 75-90 no ATC, 90-105 on ATC freq 3, 105-120 no ATC, 120-135 on ATC freq 4, 135-150 no ATC, 150-165 on ATC freq 5, 165-180 no ATC
- Result: Overall = 25% (Aerial survey with multiple frequency handoffs)

Scenario 35: Military Exercise with Multiple Aircraft
- Sector A: 60 min total, 0-10 no ATC, 10-20 on ATC freq 1, 20-30 no ATC, 30-40 on ATC freq 2, 40-50 no ATC, 50-60 on ATC freq 3
- Sector B: 45 min total, 0-5 on ATC freq 3, 5-15 no ATC, 15-25 on ATC freq 4, 25-35 no ATC, 35-45 on ATC freq 5
- Sector C: 30 min total, 0-5 no ATC, 5-15 on ATC freq 5, 15-25 no ATC, 25-30 on ATC freq 6
- Result: Overall = 44% (Military exercise coordination)

Scenario 36: Air Traffic Flow Management
- Sector A: 150 min total, 0-25 no ATC, 25-50 on ATC freq 1, 50-75 no ATC, 75-100 on ATC freq 2, 100-125 no ATC, 125-150 on ATC freq 3
- Sector B: 120 min total, 0-20 on ATC freq 3, 20-40 no ATC, 40-60 on ATC freq 4, 60-80 no ATC, 80-100 on ATC freq 5, 100-120 no ATC
- Result: Overall = 42% (Flow management with multiple controllers)

Scenario 37: Emergency Landing Sequence
- Sector A: 15 min total, 0-2 no ATC, 2-15 on ATC freq 1 (emergency)
- Sector B: 10 min total, 0-10 on ATC freq 1 (emergency)
- Sector C: 5 min total, 0-5 on ATC freq 1 (emergency)
- Result: Overall = 93% (Emergency landing priority)

Scenario 38: Complex Instrument Approach
- Sector A: 30 min total, 0-5 no ATC, 5-15 on ATC freq 1, 15-25 no ATC, 25-30 on ATC freq 2
- Sector B: 20 min total, 0-5 on ATC freq 2, 5-10 no ATC, 10-15 on ATC freq 3, 15-20 no ATC
- Sector C: 15 min total, 0-5 no ATC, 5-10 on ATC freq 3, 10-15 on ATC freq 4
- Result: Overall = 60% (Complex instrument approach)

Scenario 39: Multi-Aircraft Formation Breakup
- Sector A: 45 min total, 0-10 no ATC, 10-20 on ATC freq 1, 20-30 no ATC, 30-40 on ATC freq 2, 40-45 no ATC
- Sector B: 30 min total, 0-5 on ATC freq 2, 5-15 no ATC, 15-25 on ATC freq 3, 25-30 no ATC
- Result: Overall = 47% (Formation breakup coordination)

Scenario 40: Cross-Country Navigation Flight
- Sector A: 300 min total, 0-50 no ATC, 50-100 on ATC freq 1, 100-150 no ATC, 150-200 on ATC freq 2, 200-250 no ATC, 250-300 on ATC freq 3
- Sector B: 240 min total, 0-40 on ATC freq 3, 40-80 no ATC, 80-120 on ATC freq 4, 120-160 no ATC, 160-200 on ATC freq 5, 200-240 no ATC
- Result: Overall = 33% (Long cross-country with multiple frequency changes)
*/

-- ============================================================================
-- SCENARIO SUMMARY STATISTICS
-- ============================================================================

/*
SCENARIO COMPLEXITY BREAKDOWN:

BASIC SCENARIOS (1-20):
- Single frequency changes
- Simple sector transitions
- Predictable patterns
- Percentage range: 0% - 100%
- Average complexity: LOW

ADVANCED SCENARIOS (21-40):
- Multiple frequency handoffs
- Complex operational patterns
- Real-world mission types
- Percentage range: 13% - 93%
- Average complexity: HIGH

OPERATIONAL CATEGORIES:
- Military Operations: Scenarios 21, 35
- Emergency Operations: Scenarios 24, 29, 37
- Training Operations: Scenario 25
- Cargo Operations: Scenario 26
- Special Operations: Scenarios 27, 28, 32, 33, 34
- Navigation Operations: Scenarios 31, 38, 40
- Formation Operations: Scenarios 28, 39

FREQUENCY PATTERNS:
- Single frequency per sector
- Multiple frequencies per sector
- Frequency handoffs at sector boundaries
- Frequency changes mid-sector
- Emergency priority frequencies
- Military tactical frequencies
- Approach/arrival frequencies

SECTOR DURATIONS:
- Short sectors: 3-15 minutes
- Medium sectors: 20-90 minutes
- Long sectors: 120-300 minutes
- Mixed duration patterns

PERCENTAGE DISTRIBUTION:
- 0-20%: 8 scenarios (20%)
- 21-40%: 12 scenarios (30%)
- 41-60%: 12 scenarios (30%)
- 61-80%: 5 scenarios (12.5%)
- 81-100%: 3 scenarios (7.5%)

These scenarios provide comprehensive coverage of real-world VATSIM operations
and can be used to test and validate ATC frequency analysis queries.
*/


