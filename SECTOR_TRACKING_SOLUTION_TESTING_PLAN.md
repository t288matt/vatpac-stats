# Sector Tracking Solution Testing Plan

**Date**: October 14, 2025  
**Purpose**: Validate the sector tracking bug fix before production deployment  
**Approach**: Data-driven testing with existing problematic scenarios  

---

## Testing Strategy Overview

### **Phase 1: Unit Testing**
Test the new `_close_open_sector_for_flight_and_sector()` method in isolation

### **Phase 2: Integration Testing** 
Test the complete sector tracking flow with known problematic scenarios

### **Phase 3: Data Validation Testing**
Verify the fix resolves existing corrupted data patterns

### **Phase 4: Regression Testing**
Ensure the fix doesn't break existing working functionality

---

## Phase 1: Unit Testing

### **Test 1: Basic Close Functionality**
```python
async def test_close_open_sector_for_flight_and_sector():
    """Test that the method correctly closes an open sector entry."""
    
    # Setup: Create a flight with an open sector entry
    callsign = "TEST001"
    sector_name = "IND"
    entry_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    # Insert open sector entry
    await session.execute(text("""
        INSERT INTO flight_sector_occupancy 
        (callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds)
        VALUES (:callsign, :sector_name, :entry_time, NULL, 0)
    """), {"callsign": callsign, "sector_name": sector_name, "entry_time": entry_time})
    
    # Execute: Call the fix method
    exit_time = datetime.now(timezone.utc)
    await data_service._close_open_sector_for_flight_and_sector(
        callsign, sector_name, session, exit_time, -33.0, 151.0, 3000
    )
    
    # Verify: Entry should now be closed with correct duration
    result = await session.execute(text("""
        SELECT exit_timestamp, duration_seconds 
        FROM flight_sector_occupancy 
        WHERE callsign = :callsign AND sector_name = :sector_name
    """), {"callsign": callsign, "sector_name": sector_name})
    
    row = result.fetchone()
    assert row.exit_timestamp == exit_time
    assert row.duration_seconds == 600  # 10 minutes
```

### **Test 2: No Open Entry (Safe Operation)**
```python
async def test_close_open_sector_no_existing_entry():
    """Test that the method safely handles case with no open entry."""
    
    # Setup: No existing entries
    callsign = "TEST002"
    sector_name = "SYA"
    
    # Execute: Call the fix method
    await data_service._close_open_sector_for_flight_and_sector(
        callsign, sector_name, session, datetime.now(timezone.utc)
    )
    
    # Verify: No database changes (no exceptions thrown)
    result = await session.execute(text("""
        SELECT COUNT(*) FROM flight_sector_occupancy 
        WHERE callsign = :callsign AND sector_name = :sector_name
    """), {"callsign": callsign, "sector_name": sector_name})
    
    assert result.scalar() == 0
```

### **Test 3: Multiple Open Entries (Edge Case)**
```python
async def test_close_open_sector_multiple_entries():
    """Test that the method closes ALL open entries for the flight-sector combination."""
    
    # Setup: Create multiple open entries (shouldn't happen but test anyway)
    callsign = "TEST003"
    sector_name = "WOL"
    
    # Insert multiple open entries
    for i in range(3):
        await session.execute(text("""
            INSERT INTO flight_sector_occupancy 
            (callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds)
            VALUES (:callsign, :sector_name, :entry_time, NULL, 0)
        """), {
            "callsign": callsign, 
            "sector_name": sector_name, 
            "entry_time": datetime.now(timezone.utc) - timedelta(minutes=5+i)
        })
    
    # Execute: Call the fix method
    await data_service._close_open_sector_for_flight_and_sector(
        callsign, sector_name, session, datetime.now(timezone.utc)
    )
    
    # Verify: All entries should be closed
    result = await session.execute(text("""
        SELECT COUNT(*) FROM flight_sector_occupancy 
        WHERE callsign = :callsign AND sector_name = :sector_name AND exit_timestamp IS NULL
    """), {"callsign": callsign, "sector_name": sector_name})
    
    assert result.scalar() == 0
```

---

## Phase 2: Integration Testing

### **Test 4: Same-Sector Re-entry Scenario (Core Bug)**
```python
async def test_same_sector_reentry_fix():
    """Test the core bug fix: same-sector re-entry without overlapping entries."""
    
    # Setup: Simulate UAE414 scenario
    callsign = "TEST_UAE414"
    sector_name = "IND"
    
    # Initial entry
    flight_data_1 = {
        "callsign": callsign,
        "latitude": -33.0,
        "longitude": 151.0,
        "altitude": 3000,
        "groundspeed": 120  # Above 60 knots - should enter
    }
    
    # First entry
    await data_service._track_sector_occupancy(flight_data_1, session)
    
    # Simulate brief exit (speed drops below 60)
    flight_data_2 = {
        "callsign": callsign,
        "latitude": -33.0,
        "longitude": 151.0,
        "altitude": 3000,
        "groundspeed": 45  # Below 60 knots - should exit
    }
    
    await data_service._track_sector_occupancy(flight_data_2, session)
    
    # Simulate re-entry to same sector (speed back above 60)
    flight_data_3 = {
        "callsign": callsign,
        "latitude": -33.0,
        "longitude": 151.0,
        "altitude": 3000,
        "groundspeed": 120  # Above 60 knots - should re-enter
    }
    
    await data_service._track_sector_occupancy(flight_data_3, session)
    
    # Verify: Should have exactly 2 entries (not 1 with overlap)
    result = await session.execute(text("""
        SELECT COUNT(*) FROM flight_sector_occupancy 
        WHERE callsign = :callsign AND sector_name = :sector_name
    """), {"callsign": callsign, "sector_name": sector_name})
    
    assert result.scalar() == 2
    
    # Verify: No overlapping entries
    result = await session.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT fso1.id 
            FROM flight_sector_occupancy fso1
            JOIN flight_sector_occupancy fso2 
                ON fso1.callsign = fso2.callsign 
                AND fso1.sector_name = fso2.sector_name
                AND fso1.id < fso2.id
            WHERE fso1.entry_timestamp < fso2.exit_timestamp 
                AND fso1.exit_timestamp > fso2.entry_timestamp
        ) overlaps
    """), {"callsign": callsign, "sector_name": sector_name})
    
    assert result.scalar() == 0
```

### **Test 5: Speed-Based Exit Logic (Regression Test)**
```python
async def test_speed_based_exit_logic_unchanged():
    """Ensure the fix doesn't break existing speed-based exit logic."""
    
    callsign = "TEST_SPEED"
    sector_name = "SYA"
    
    # Enter sector
    flight_data_1 = {
        "callsign": callsign,
        "latitude": -33.0,
        "longitude": 151.0,
        "altitude": 3000,
        "groundspeed": 120
    }
    await data_service._track_sector_occupancy(flight_data_1, session)
    
    # First low speed poll (should increment exit counter)
    flight_data_2 = {
        "callsign": callsign,
        "latitude": -33.0,
        "longitude": 151.0,
        "altitude": 3000,
        "groundspeed": 25  # Below 30 knots
    }
    await data_service._track_sector_occupancy(flight_data_2, session)
    
    # Second low speed poll (should force exit)
    await data_service._track_sector_occupancy(flight_data_2, session)
    
    # Verify: Should have exited due to 2 consecutive low-speed polls
    result = await session.execute(text("""
        SELECT exit_timestamp IS NOT NULL FROM flight_sector_occupancy 
        WHERE callsign = :callsign AND sector_name = :sector_name
    """), {"callsign": callsign, "sector_name": sector_name})
    
    assert result.scalar() == True
```

---

## Phase 3: Data Validation Testing

### **Test 6: Fix Existing Corrupted Data**
```python
async def test_fix_existing_corrupted_data():
    """Test that the fix can resolve existing corrupted data patterns."""
    
    # Setup: Create corrupted data similar to UAE414
    callsign = "TEST_CORRUPTED"
    sector_name = "IND"
    
    # Create overlapping entries (simulating the bug)
    base_time = datetime.now(timezone.utc)
    
    # First entry
    await session.execute(text("""
        INSERT INTO flight_sector_occupancy 
        (callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds)
        VALUES (:callsign, :sector_name, :entry_time, :exit_time, :duration)
    """), {
        "callsign": callsign,
        "sector_name": sector_name,
        "entry_time": base_time,
        "exit_time": base_time + timedelta(minutes=2),
        "duration": 120
    })
    
    # Overlapping entry (the bug)
    await session.execute(text("""
        INSERT INTO flight_sector_occupancy 
        (callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds)
        VALUES (:callsign, :sector_name, :entry_time, :exit_time, :duration)
    """), {
        "callsign": callsign,
        "sector_name": sector_name,
        "entry_time": base_time + timedelta(minutes=1, seconds=30),  # Overlaps!
        "exit_time": base_time + timedelta(minutes=5),
        "duration": 210
    })
    
    # Execute: Apply the fix by calling the new method
    await data_service._close_open_sector_for_flight_and_sector(
        callsign, sector_name, session, base_time + timedelta(minutes=6)
    )
    
    # Verify: No more overlapping entries
    result = await session.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT fso1.id 
            FROM flight_sector_occupancy fso1
            JOIN flight_sector_occupancy fso2 
                ON fso1.callsign = fso2.callsign 
                AND fso1.sector_name = fso2.sector_name
                AND fso1.id < fso2.id
            WHERE fso1.entry_timestamp < fso2.exit_timestamp 
                AND fso1.exit_timestamp > fso2.entry_timestamp
        ) overlaps
    """), {"callsign": callsign, "sector_name": sector_name})
    
    assert result.scalar() == 0
```

### **Test 7: Validate Against Real UAE414 Data**
```python
async def test_validate_against_real_uae414_data():
    """Test the fix against actual UAE414 data patterns."""
    
    # Query real UAE414 data
    result = await session.execute(text("""
        SELECT entry_timestamp, exit_timestamp, duration_seconds
        FROM flight_sector_occupancy 
        WHERE callsign = 'UAE414' AND sector_name = 'IND'
        ORDER BY entry_timestamp
    """))
    
    uae414_entries = result.fetchall()
    
    # Simulate the same pattern with the fix
    callsign = "TEST_UAE414_PATTERN"
    sector_name = "IND"
    
    for i, entry in enumerate(uae414_entries):
        # Simulate the flight data that would have caused this entry
        flight_data = {
            "callsign": callsign,
            "latitude": -33.0,
            "longitude": 151.0,
            "altitude": 3000,
            "groundspeed": 120 if i % 2 == 0 else 45  # Alternate speed
        }
        
        await data_service._track_sector_occupancy(flight_data, session)
    
    # Verify: No overlapping entries in the simulated data
    result = await session.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT fso1.id 
            FROM flight_sector_occupancy fso1
            JOIN flight_sector_occupancy fso2 
                ON fso1.callsign = fso2.callsign 
                AND fso1.sector_name = fso2.sector_name
                AND fso1.id < fso2.id
            WHERE fso1.entry_timestamp < fso2.exit_timestamp 
                AND fso1.exit_timestamp > fso2.entry_timestamp
        ) overlaps
    """), {"callsign": callsign, "sector_name": sector_name})
    
    assert result.scalar() == 0
```

---

## Phase 4: Regression Testing

### **Test 8: Normal Sector Transitions (Should Still Work)**
```python
async def test_normal_sector_transitions_unchanged():
    """Ensure normal sector transitions still work correctly."""
    
    callsign = "TEST_TRANSITION"
    
    # Enter first sector
    flight_data_1 = {
        "callsign": callsign,
        "latitude": -33.0,  # SYA sector
        "longitude": 151.0,
        "altitude": 3000,
        "groundspeed": 120
    }
    await data_service._track_sector_occupancy(flight_data_1, session)
    
    # Transition to different sector
    flight_data_2 = {
        "callsign": callsign,
        "latitude": -34.0,  # Different sector
        "longitude": 152.0,
        "altitude": 3000,
        "groundspeed": 120
    }
    await data_service._track_sector_occupancy(flight_data_2, session)
    
    # Verify: Should have entries in both sectors
    result = await session.execute(text("""
        SELECT COUNT(DISTINCT sector_name) FROM flight_sector_occupancy 
        WHERE callsign = :callsign
    """), {"callsign": callsign})
    
    assert result.scalar() == 2
```

### **Test 9: Performance Impact**
```python
async def test_performance_impact():
    """Ensure the fix doesn't significantly impact performance."""
    
    import time
    
    callsign = "TEST_PERFORMANCE"
    sector_name = "IND"
    
    # Measure time for 100 sector entries
    start_time = time.time()
    
    for i in range(100):
        flight_data = {
            "callsign": callsign,
            "latitude": -33.0,
            "longitude": 151.0,
            "altitude": 3000,
            "groundspeed": 120 if i % 2 == 0 else 45
        }
        await data_service._track_sector_occupancy(flight_data, session)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Should complete within reasonable time (adjust threshold as needed)
    assert duration < 10.0  # 10 seconds for 100 operations
    
    print(f"Performance test: 100 operations in {duration:.2f} seconds")
```

---

## Production Validation Testing

### **Test 10: Live Data Monitoring**
```python
async def test_live_data_monitoring():
    """Monitor live data for data quality improvements."""
    
    # Before fix metrics
    before_fix = await session.execute(text("""
        SELECT 
            COUNT(*) as total_flights,
            COUNT(*) FILTER (WHERE callsign IN (
                SELECT callsign FROM (
                    SELECT callsign, sector_name, COUNT(*) as entry_count
                    FROM flight_sector_occupancy 
                    WHERE exit_timestamp IS NOT NULL
                    GROUP BY callsign, sector_name
                    HAVING COUNT(*) > 1
                ) multiple_entries
            )) as flights_with_multiple_entries,
            COUNT(*) FILTER (WHERE exit_timestamp < entry_timestamp) as impossible_timestamps
        FROM flight_sector_occupancy 
        WHERE exit_timestamp IS NOT NULL
    """)).fetchone()
    
    print(f"Before fix: {before_fix.total_flights} flights, "
          f"{before_fix.flights_with_multiple_entries} with multiple entries, "
          f"{before_fix.impossible_timestamps} impossible timestamps")
    
    # Deploy fix and monitor for 24 hours
    
    # After fix metrics
    after_fix = await session.execute(text("""
        SELECT 
            COUNT(*) as total_flights,
            COUNT(*) FILTER (WHERE callsign IN (
                SELECT callsign FROM (
                    SELECT callsign, sector_name, COUNT(*) as entry_count
                    FROM flight_sector_occupancy 
                    WHERE exit_timestamp IS NOT NULL
                    GROUP BY callsign, sector_name
                    HAVING COUNT(*) > 1
                ) multiple_entries
            )) as flights_with_multiple_entries,
            COUNT(*) FILTER (WHERE exit_timestamp < entry_timestamp) as impossible_timestamps
        FROM flight_sector_occupancy 
        WHERE exit_timestamp IS NOT NULL
        AND entry_timestamp > NOW() - INTERVAL '24 hours'
    """)).fetchone()
    
    print(f"After fix: {after_fix.total_flights} flights, "
          f"{after_fix.flights_with_multiple_entries} with multiple entries, "
          f"{after_fix.impossible_timestamps} impossible timestamps")
    
    # Validate improvement
    assert after_fix.flights_with_multiple_entries < before_fix.flights_with_multiple_entries
    assert after_fix.impossible_timestamps == 0
```

---

## Test Execution Plan

### **Development Environment**
1. Run all unit tests (Tests 1-3)
2. Run integration tests (Tests 4-5)
3. Run data validation tests (Tests 6-7)
4. Run regression tests (Tests 8-9)

### **Staging Environment**
1. Deploy fix to staging
2. Run live data monitoring (Test 10)
3. Monitor for 48 hours
4. Validate metrics improvement

### **Production Deployment**
1. Deploy to production during low-traffic window
2. Monitor real-time metrics
3. Run validation queries every hour for first 24 hours
4. Full validation after 1 week

---

## Success Criteria

### **Immediate (Within 24 hours)**
- ✅ Zero new impossible timestamps
- ✅ Zero new overlapping entries
- ✅ <10% of flights with multiple sector entries (vs current 69%)

### **Short-term (Within 1 week)**
- ✅ <5% of flights with multiple sector entries
- ✅ Stable sector tracking metrics
- ✅ No performance degradation

### **Long-term (Within 1 month)**
- ✅ <2% of flights with multiple sector entries
- ✅ Consistent data quality metrics
- ✅ Reliable analytics and reporting

---

## Rollback Plan

If issues arise:
1. **Immediate**: Disable sector tracking temporarily
2. **Short-term**: Revert to previous code version
3. **Data cleanup**: Fix any new corrupted records
4. **Investigation**: Analyze what went wrong
5. **Re-deploy**: Apply corrected fix

This comprehensive testing plan ensures the fix works correctly and doesn't introduce new issues while resolving the existing data corruption problems.



