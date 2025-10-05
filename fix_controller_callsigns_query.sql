-- Fix for the failing query that's trying to use jsonb_array_length on non-array values
-- Original query:
--
-- SELECT
--   callsign,
--   departure,
--   arrival,
--   logon_time,
--   completion_time,
--   controller_callsigns,
--   controller_time_percentage,
--   airborne_controller_time_percentage,
--   time_online_minutes
-- FROM flight_summaries
-- WHERE DATE(completion_time) = '2025-09-27'
-- AND controller_callsigns IS NOT NULL
-- AND jsonb_array_length(controller_callsigns) > 1
-- ORDER BY jsonb_array_length(controller_callsigns) DESC
-- LIMIT 10;

-- Modified query that checks if controller_callsigns is an array before using jsonb_array_length:
SELECT
  callsign,
  departure,
  arrival,
  logon_time,
  completion_time,
  controller_callsigns,
  controller_time_percentage,
  airborne_controller_time_percentage,
  time_online_minutes
FROM flight_summaries
WHERE DATE(completion_time) = '2025-09-27'
AND controller_callsigns IS NOT NULL
AND jsonb_typeof(controller_callsigns) = 'object'  -- Check if it's an object (dictionary)
AND jsonb_object_keys(controller_callsigns) != ''  -- Ensure the object has at least one key
ORDER BY jsonb_object_length(controller_callsigns) DESC  -- Order by number of keys in the object
LIMIT 10;

-- Alternative if we want to include both objects and arrays (objects being controller_callsigns dictionaries
-- and arrays being actual arrays of controller callsigns):
-- 
-- SELECT
--   callsign,
--   departure,
--   arrival,
--   logon_time,
--   completion_time,
--   controller_callsigns,
--   controller_time_percentage,
--   airborne_controller_time_percentage,
--   time_online_minutes
-- FROM flight_summaries
-- WHERE DATE(completion_time) = '2025-09-27'
-- AND controller_callsigns IS NOT NULL
-- AND (
--   (jsonb_typeof(controller_callsigns) = 'array' AND jsonb_array_length(controller_callsigns) > 1)
--   OR
--   (jsonb_typeof(controller_callsigns) = 'object' AND jsonb_object_length(controller_callsigns) > 1)
-- )
-- ORDER BY 
--   CASE
--     WHEN jsonb_typeof(controller_callsigns) = 'array' THEN jsonb_array_length(controller_callsigns)
--     WHEN jsonb_typeof(controller_callsigns) = 'object' THEN jsonb_object_length(controller_callsigns)
--     ELSE 0
--   END DESC
-- LIMIT 10;

-- Long-term fix options:
-- 
-- 1. Modify the ATC detection service to always return an array for controller_callsigns, even when empty:
--    In app/services/atc_detection_service.py, change:
--    "controller_callsigns": {} to "controller_callsigns": []
--
-- 2. Add a database migration to fix existing data:
--    UPDATE flight_summaries
--    SET controller_callsigns = '[]'::jsonb
--    WHERE controller_callsigns = '{}'::jsonb OR jsonb_typeof(controller_callsigns) != 'array';
--
-- 3. Fix ENABLE_ENRICHMENT setting in docker-compose.yml (currently set to "false")
--    This might help ensure proper formatting of controller_callsigns in future records

