-- Migration: Convert primary key id columns (integer/serial) to BIGINT and adjust referencing foreign keys
-- Save as migrations/20250905_migrate_ids_to_bigint.sql
-- Run first on a test database, verify, then run in production.
-- NOTE: This will DROP and RECREATE foreign-key constraints referencing the listed tables.
-- Reviewed tables: controllers, flights, transceivers, flight_summaries, flights_archive,
--                  controller_summaries, controllers_archive, flight_sector_occupancy

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    'controllers',
    'flights',
    'transceivers',
    'flight_summaries',
    'flights_archive',
    'controller_summaries',
    'controllers_archive',
    'flight_sector_occupancy'
  ];

  fk record;
  col_names text[];
  tbl_col text;
  seq_name text;
  seq_parts text[];
  constraint_def text;
BEGIN
  RAISE NOTICE 'Starting BIGINT migration for % rows', array_length(tbls,1);

  FOREACH tbl IN ARRAY tbls LOOP
    RAISE NOTICE '--- Processing table: %', tbl;

    -- Find all foreign-key constraints that reference this table and capture their definitions
    FOR fk IN
      SELECT
        c.oid AS constraint_oid,
        c.conname AS constraint_name,
        (c.conrelid::regclass)::text AS referencing_table,
        pg_get_constraintdef(c.oid) AS constraint_def,
        c.conkey AS referencing_col_nums
      FROM pg_constraint c
      WHERE c.contype = 'f'
        AND c.confrelid = format('%I.%I','public', tbl)::regclass
    LOOP
      -- Build array of column names in the referencing table for this constraint
      SELECT array_agg(att.attname ORDER BY u.idx) INTO col_names
      FROM (
        SELECT fk.referencing_col_nums[i] AS attnum, i AS idx
        FROM generate_series(1, COALESCE(array_length(fk.referencing_col_nums,1),0)) AS s(i)
      ) AS u
      JOIN pg_attribute att ON att.attrelid = fk.referencing_table::regclass AND att.attnum = u.attnum;

      -- Drop the FK constraint so we can change column types
      EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', fk.referencing_table, fk.constraint_name);
      RAISE NOTICE 'Dropped constraint % on %', fk.constraint_name, fk.referencing_table;

      -- After dropping, store the constraint definition for recreation later
      constraint_def := fk.constraint_def;

      -- Alter referencing columns to BIGINT (if they are integer-like)
      IF col_names IS NOT NULL THEN
        FOREACH tbl_col IN ARRAY col_names LOOP
          -- Only alter if current type is integer (int4) or smallint; skip if already bigint
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = split_part(fk.referencing_table, '.', 2) AND column_name = tbl_col
              AND data_type IN ('integer','smallint')
          ) THEN
            EXECUTE format('ALTER TABLE %s ALTER COLUMN %I TYPE BIGINT USING %I::bigint', fk.referencing_table, tbl_col, tbl_col);
            RAISE NOTICE 'Altered referencing column %s.%s -> BIGINT', fk.referencing_table, tbl_col;
          ELSE
            RAISE NOTICE 'Skipping alter of %s.%s (not integer type)', fk.referencing_table, tbl_col;
          END IF;
        END LOOP;
      END IF;

      -- Recreate the original FK constraint (using saved definition)
      EXECUTE format('ALTER TABLE %s ADD CONSTRAINT %I %s', fk.referencing_table, fk.constraint_name, constraint_def);
      RAISE NOTICE 'Recreated constraint % on %', fk.constraint_name, fk.referencing_table;
    END LOOP;

    -- Alter the table's own primary key column 'id' to BIGINT if it is integer
    IF EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = tbl AND column_name = 'id' AND data_type = 'integer'
    ) THEN
      EXECUTE format('ALTER TABLE public.%I ALTER COLUMN id TYPE BIGINT USING id::bigint', tbl);
      RAISE NOTICE 'Altered public.% id -> BIGINT', tbl;
    ELSE
      RAISE NOTICE 'public.% does not have integer id (skipping)', tbl;
    END IF;

    -- If a serial sequence exists for this table.id, set it to match the max(id) and OWN it
    SELECT pg_get_serial_sequence(format('public.%I', tbl), 'id') INTO seq_name;
    IF seq_name IS NOT NULL THEN
      -- Ensure sequence ownership points to the correct column
      seq_parts := regexp_split_to_array(seq_name, '\.');
      IF array_length(seq_parts,1) = 2 THEN
        EXECUTE format('ALTER SEQUENCE %I.%I OWNED BY public.%I.id', seq_parts[1], seq_parts[2], tbl);
      ELSE
        EXECUTE format('ALTER SEQUENCE %I OWNED BY public.%I.id', seq_name, tbl);
      END IF;

      -- Set sequence value to max(id) to avoid nextval collisions
      EXECUTE 'SELECT setval(' || quote_literal(seq_name) || '::regclass, COALESCE((SELECT MAX(id) FROM public.' || quote_ident(tbl) || '), 1), true)';
      RAISE NOTICE 'Adjusted sequence % to MAX(id) for %', seq_name, tbl;
    ELSE
      RAISE NOTICE 'No serial sequence found for public.%', tbl;
    END IF;

  END LOOP; -- tables

  RAISE NOTICE 'BIGINT migration completed for declared tables.';
END;
$$;


