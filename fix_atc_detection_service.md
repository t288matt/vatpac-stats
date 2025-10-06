# Fix for ATC Detection Service JSON Format Issue

This document outlines the root cause and fix for the PostgreSQL error:
```
ERROR: cannot get array length of a non-array
```

## Root Cause

The issue is caused by inconsistency in how controller interaction data is formatted:

1. In `app/services/atc_detection_service.py`, when no controllers are detected, an empty dictionary `{}` is returned:
   ```python
   def _create_empty_atc_data(self) -> Dict[str, Any]:
       """Create empty ATC data structure."""
       return {
           "controller_callsigns": {},  # Should be [] instead of {}
           # Other fields...
       }
   ```

2. The `controller_callsigns` field is defined as JSONB in the database schema, which can store any valid JSON.

3. When SQL queries use `jsonb_array_length(controller_callsigns)`, they expect controller_callsigns to be an array, not an object.

## Fix Required

1. **Modify ATC Detection Service Code:**
   
   Change in `app/services/atc_detection_service.py`:
   ```python
   def _create_empty_atc_data(self) -> Dict[str, Any]:
       """Create empty ATC data structure."""
       return {
           "controller_callsigns": [],  # Changed from {} to []
           # Other fields...
       }
   ```

2. **Add Database Migration:**
   
   A SQL migration has been created (`migrations/fix_controller_callsigns_format.sql`) to fix existing data by:
   - Converting empty objects `{}` to empty arrays `[]`
   - Converting non-empty objects (dictionaries) to arrays of their values
   - Setting any other non-array values to empty arrays

3. **Update Queries:**
   
   Queries that use `jsonb_array_length(controller_callsigns)` can be modified to handle both array and object types:
   ```sql
   -- Check if it's an array before using array functions
   AND jsonb_typeof(controller_callsigns) = 'array'
   AND jsonb_array_length(controller_callsigns) > 1
   ```

## Implementation Plan

1. Apply the database migration to fix existing data
2. Fix the ATC detection service code to return arrays instead of objects
3. Update any queries that rely on controller_callsigns being an array

## Additional Notes

- The `ENABLE_ENRICHMENT` setting in docker-compose.yml is currently set to "false" which might be contributing to this issue. Consider enabling it in development environments.
- Consider adding validation in the data insertion process to ensure controller_callsigns is always stored as an array.

