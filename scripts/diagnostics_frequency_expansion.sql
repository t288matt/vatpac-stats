-- diagnostics_frequency_expansion.sql
-- Expand frequencies_used and convert to Hz (robustly) for inspection
SELECT
    cs.id,
    cs.callsign,
    cs.session_start_time,
    cs.session_end_time,
    fq_elem AS original_freq_elem,
    regexp_replace(fq_elem, '[^0-9\.]', '', 'g') AS raw_freq,
    CASE
        WHEN regexp_replace(fq_elem, '[^0-9\.]', '', 'g') = '' THEN NULL
        WHEN POSITION('.' IN regexp_replace(fq_elem, '[^0-9\.]', '', 'g')) > 0 THEN (round((regexp_replace(fq_elem, '[^0-9\.]', '', 'g'))::numeric,3) * 1000000)::bigint
        ELSE (regexp_replace(fq_elem, '[^0-9\.]', '', 'g'))::bigint
    END AS freq_hz
FROM controller_summaries cs
CROSS JOIN LATERAL jsonb_array_elements_text(cs.frequencies_used) AS fq(fq_elem)
WHERE cs.callsign = 'ML-BLA_CTR'
ORDER BY cs.session_start_time DESC;
