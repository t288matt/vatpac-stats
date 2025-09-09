-- diagnostics_transceivers_search.sql
-- Search transceivers during ML-BLA_CTR session windows within +/-50kHz of session frequencies
WITH sessions AS (
    SELECT id, callsign, session_start_time, session_end_time, jsonb_array_elements_text(frequencies_used) AS fq_elem
    FROM controller_summaries
    WHERE callsign = 'ML-BLA_CTR'
)
SELECT s.id AS session_id, s.callsign, s.session_start_time, s.session_end_time, s.fq_elem,
       regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g') AS raw_freq,
       CASE WHEN POSITION('.' IN regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g')) > 0 THEN (round((regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g'))::numeric,3) * 1000000)::bigint ELSE (regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g'))::bigint END AS freq_hz,
       t.id AS transceiver_id, t.callsign AS flight_callsign, t.frequency AS tx_frequency, t.timestamp, t.entity_type
FROM sessions s
LEFT JOIN transceivers t
  ON t.timestamp >= s.session_start_time - INTERVAL '3 minutes'
 AND t.timestamp <= COALESCE(s.session_end_time, s.session_start_time) + INTERVAL '3 minutes'
 AND t.frequency BETWEEN (CASE WHEN POSITION('.' IN regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g')) > 0 THEN (round((regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g'))::numeric,3) * 1000000)::bigint ELSE (regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g'))::bigint END) - 50000
                     AND (CASE WHEN POSITION('.' IN regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g')) > 0 THEN (round((regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g'))::numeric,3) * 1000000)::bigint ELSE (regexp_replace(s.fq_elem, '[^0-9\.]', '', 'g'))::bigint END) + 50000
ORDER BY s.session_start_time DESC, t.timestamp DESC;
