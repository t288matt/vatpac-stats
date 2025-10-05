# Flight Time Calculation Improvement Proposal

## Current Issue

The VATPAC data system currently calculates two important flight time metrics:

1. **Time Online Minutes**: Total time the pilot was connected to the network (works well)
2. **Total Enroute Time Minutes**: Currently calculated based on time spent in defined airspace sectors

The problem with the second metric is that it shows 0 minutes for many valid flights because:
- The flight never entered any defined sectors
- The flight was outside of monitored airspace
- The flight was on the ground/parked
- The flight flew through areas not covered by sector definitions

This leads to inaccurate statistics for many flights, as seen with flight ACA34 which showed 68 minutes online but 0 minutes enroute.

## Proposed Solution

Replace the sector-based calculation with an altitude-based calculation that measures actual time in the air.

### Implementation Details

1. **Create a new function** to calculate airborne time:

```python
async def _get_total_airborne_time(self, flight_callsign: str, logon_time: datetime, completion_time: datetime) -> int:
    """Calculate total time spent above 1500ft"""
    try:
        async with get_database_session() as session:
            result = await session.execute(text("""
                SELECT COUNT(*) as airborne_count
                FROM flights
                WHERE callsign = :callsign
                  AND last_updated BETWEEN :start AND :end
                  AND altitude > 1500
            """), {
                "callsign": flight_callsign,
                "start": logon_time,
                "end": completion_time
            })
            
            airborne_count = result.scalar() or 0
            polling_interval_minutes = self.polling_interval_seconds / 60.0
            return int(airborne_count * polling_interval_minutes)
    except Exception as e:
        self.logger.error(f"Error calculating airborne time: {e}")
        return 0
```

2. **Update the canonical processing** to use this method instead of sector-based calculations for `total_enroute_time_minutes`

3. **Where to implement**: Replace the sector-based calculation in `data_service.py` around line 2468:
```python
# Current implementation:
total_enroute_time = sum(sector_breakdown.values())

# New implementation:
total_enroute_time = await self._get_total_airborne_time(callsign, fl_row.first_updated, fl_row.last_updated)
```

## Benefits

1. **Universal coverage**: Works for all flights regardless of location

2. **True airborne measurement**: Properly distinguishes between ground time and air time

3. **Independence from sectors**: No reliance on whether the aircraft entered defined sectors

4. **More accurate statistics**: Better data for flight analysis and reporting

## Example Calculation

For a typical flight:
- Takes off from Sydney (YSSY)
- Taxis and ground operations: 20 minutes
- Climbs and flies at altitude: 2 hours
- Descends and lands at Melbourne (YMML)
- Final taxi and shutdown: 15 minutes

**Current calculation might show**:
- Time online: 2 hours 35 minutes (correct)
- Enroute time: 0 minutes (if no sector data available)

**New calculation would show**:
- Time online: 2 hours 35 minutes (unchanged)
- Enroute time: approximately 2 hours (time spent above 1,500 feet)

This provides a more accurate representation of the flight's airborne phase for statistics and analysis.









