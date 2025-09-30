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
    s.table_name,
    s.column_name,
    s.sequence_name,
    (SELECT last_value FROM pg_sequences WHERE sequencename = split_part(s.sequence_name, '.', 2)) as sequence_value,
    (SELECT MAX(CAST(a.attname AS text)::int) FROM pg_attribute a WHERE a.attrelid = s.table_name::regclass) as max_id,
    CASE WHEN 
        (SELECT MAX(CAST(a.attname AS text)::int) FROM pg_attribute a WHERE a.attrelid = s.table_name::regclass) >
        (SELECT last_value FROM pg_sequences WHERE sequencename = split_part(s.sequence_name, '.', 2))
    THEN 'OUT OF SYNC'
    ELSE 'OK'
    END as status
FROM 
    sequence_info s
WHERE 
    NOT s.table_name LIKE 'pg_%' AND
    NOT s.table_name LIKE 'sql_%'
ORDER BY 
    s.table_name;
