# Decision Log

## Overview

This document records the key decisions made during the development of the VATSIM data collection and analysis system. Each decision includes the context, options considered, the chosen approach, and the rationale behind it.

**Last Updated**: January 2025  
**Project**: VATSIM Data Collection System  
**Status**: Active Development

---

## 📊 **Data Processing Decisions**

### DP-004: Flight Plan Data Quality
**Date**: January 2025  
**Status**: ✅ Implemented  
**Context**: Need to handle flights that connect to VATSIM without filing flight plans.

**Options Considered**:
- Filter out all flights without flight plans
- Keep all flights regardless of flight plan status
- Filter only flights that never depart (no position updates)
- Hybrid approach with different handling for different scenarios

**Decision**: Keep all flights without flight plans, but consider removing those that never depart.

**Rationale**:
- Many legitimate flights connect without filing flight plans
- Some pilots file plans after connecting
- Flights without position updates are likely abandoned connections
- Maintains data completeness while filtering obvious noise

**Implementation**:
- All flights tracked regardless of flight plan presence
- Position updates determine if flight is active
- Flights without position updates after connection are candidates for cleanup
- Flight plan fields remain nullable in database schema

**Consequences**:
- Higher data volume but more complete coverage
- Need to handle flights with missing departure/arrival information
- Analytics must account for incomplete flight plan data
- Real-time tracking works for all connected aircraft

---

## 📝 **Decision Log Maintenance**

### How to Use This Log

1. **For New Decisions**: Add entries following the established format
2. **For Updates**: Mark decisions as superseded and add new entries
3. **For Reviews**: Regularly review decisions for relevance and accuracy

### Entry Format

```
### [Category]-[Number]: [Decision Title]
**Date**: [Date]
**Status**: [Implemented/Pending/Superseded]
**Context**: [What led to this decision]
**Options Considered**: [List of alternatives]
**Decision**: [What was chosen]
**Rationale**: [Why this was chosen]
**Consequences**: [What this decision means]
```

### Review Schedule

- **Monthly**: Review all pending decisions
- **Quarterly**: Review all decisions for relevance
- **Before Major Changes**: Review related decisions

---

---

## 📊 **ATC Detection Decisions**

### DP-005: Airborne Controller Time Percentage Field
**Date**: January 2025  
**Status**: ✅ Implemented  
**Context**: Need to distinguish between total ATC coverage and airborne ATC coverage for more accurate operational analysis.

**Options Considered**:
- Modify existing `controller_time_percentage` to only count airborne contacts
- Add new field for airborne coverage while keeping existing field unchanged
- Use altitude-based filtering in existing calculations
- Create separate airborne metrics table

**Decision**: Add new `airborne_controller_time_percentage` field alongside existing `controller_time_percentage`.

**Rationale**:
- Preserves existing functionality that may be used by other systems
- Provides more accurate metrics for operational decisions
- Ground operations (taxi, takeoff, landing) have different ATC requirements than enroute
- Allows comparison between total and airborne coverage patterns

**Implementation**:
- New field: `airborne_controller_time_percentage` (DECIMAL(5,2))
- Only counts ATC contacts when aircraft altitude > 1500ft
- Denominator is total enroute time (time above 1500ft)
- Uses same VATSIM polling interval logic for consistency
- Added to `flight_summaries` table with proper indexing

**Consequences**:
- More accurate representation of enroute ATC coverage
- Better data for staffing decisions and capacity planning
- Maintains backward compatibility with existing metrics
- Requires altitude data to be available for accurate calculations

---

**Last Updated**: January 2025  
**Next Review**: February 2025
