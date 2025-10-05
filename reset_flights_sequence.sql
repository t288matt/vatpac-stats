-- Reset the flights_id_seq sequence to prevent primary key conflicts
-- This fixes the critical issue where PostgreSQL sequence is out of sync
-- with the actual data in the flights table, causing primary key constraint violations

-- Get the current sequence value and max ID for diagnosis
SELECT 
    'Current State' as description,
    (SELECT last_value FROM flights_id_seq) as sequence_value,
    (SELECT MAX(id) FROM flights) as max_id,
    (SELECT MIN(id) FROM flights) as min_id,
    (SELECT COUNT(*) FROM flights) as total_records;

-- Reset the sequence to max ID + 1
SELECT setval('flights_id_seq', (SELECT MAX(id) FROM flights) + 1, false);

-- Verify the change
SELECT 
    'After Reset' as description,
    (SELECT last_value FROM flights_id_seq) as sequence_value,
    (SELECT MAX(id) FROM flights) as max_id;

-- Check other sequences for similar issues (diagnostic only)
WITH sequence_info AS (
    SELECT 
        c.relname as table_name,
        a.attname as column_name,
        pg_get_serial_sequence(c.relname, a.attname) as sequence_name
    FROM 
        pg_class c
    JOIN 
        pg_attribute a ON a.attrelid = c.oid
    WHERE 
        c.relkind = 'r' AND
        a.attnum > 0 AND 
        NOT a.attisdropped AND
        pg_get_serial_sequence(c.relname, a.attname) IS NOT NULL
)
SELECT 
    table_name,
    column_name,
    sequence_name,
    (SELECT last_value FROM pg_sequences WHERE sequencename = (SELECT regexp_replace(sequence_name, '^.*\.', ''))) as sequence_value,
    (SELECT MAX(c.column_name::integer) FROM information_schema.columns ic
     JOIN sequence_info si ON ic.table_name = si.table_name AND ic.column_name = si.column_name
     JOIN ONLY si.table_name c ON 1=1) as max_value,
    CASE 
        WHEN (SELECT last_value FROM pg_sequences WHERE sequencename = (SELECT regexp_replace(sequence_name, '^.*\.', ''))) < 
             (SELECT MAX(c.column_name::integer) FROM information_schema.columns ic
              JOIN sequence_info si ON ic.table_name = si.table_name AND ic.column_name = si.column_name
              JOIN ONLY si.table_name c ON 1=1)
        THEN 'OUT OF SYNC'
        ELSE 'OK'
    END as status
FROM sequence_info
WHERE sequence_name IS NOT NULL;
