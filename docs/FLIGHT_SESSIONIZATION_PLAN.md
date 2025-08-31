## Flight Sessionization: Unified Processing Plan

### Overview
- Unify flight processing behind one canonical session selector.
- A session is computed by merging segments for the same (callsign, cid, departure) using an inactivity gap.
- All downstream steps (summary upsert, archive, delete, ATC detection) consume this single selector.

### Configuration (Decided)
- Inactivity gap (merge threshold): 2 hours (120 minutes)
- Maximum session span: 8 hours (from FLIGHT_COMPLETION_HOURS)
- Same‑day repeats: allowed (no auto‑reject rule)
- Grouping/signature includes arrival
- JSON merge policy for controller_callsigns: key‑wise union; prefer latest timestamps and max counters; recompute percentages from base counts/time
- Rollout: staged (selector → archive/delete refactor → upsert wiring → sweep/monitoring)

### Implementation Plan
1) Build canonical session selector
   - Input: `flights` within completion horizon
   - Group by (callsign, cid, departure, arrival); merge segments by 2‑hour inactivity gap (cross‑midnight safe)
   - Output per session: session_start (earliest logon_time), session_end (latest last_updated), latest_deptime, arrival, route snapshot

2) Refactor completed‑flight selection to use the selector output
   - Replace DISTINCT deptime grouping and callsign‑only exclusion
   - Drive processing solely from canonical sessions

3) Upsert `flight_summaries` by session signature
   - Signature: (callsign, cid, departure, arrival, session_start)
   - On conflict: completion_time = GREATEST(existing, incoming); deptime = latest; JSON merges per policy

4) Archive/delete by session time window
   - Archive all `flights` rows for (callsign, cid, departure, arrival) where last_updated ∈ [session_start, session_end]
   - Delete the same rows (table remains only unprocessed)

5) Indexes
   - `flights`: (callsign, cid, departure, arrival, last_updated), optional (callsign, cid, departure, arrival, logon_time)
   - `flight_summaries`: (callsign, cid, departure, arrival, logon_time)

6) Concurrency control
   - Advisory lock on hash(callsign, cid, departure, arrival) around per‑session work; scope only the critical section (upsert → archive → delete)
   - Rationale: prevents concurrent processors from acting on the same session while allowing parallelism across different sessions
   - Transaction‑level lock: use pg_advisory_xact_lock(key) so the lock is released automatically on commit/rollback (avoids leaks with pooled async connections)
   - Pattern:
     - BEGIN;
     - SET LOCAL lock_timeout = '50ms';
     - SELECT pg_advisory_xact_lock(hashtextextended(concat_ws('|', callsign,cid,departure,arrival), 0));  -- retry with jitter if timeout
     - Critical section: upsert summary → archive window (≤ HWM) → delete window
     - COMMIT;  -- auto‑unlock
   - On contention: retry with jitter/backoff; keep critical section minimal; ensure idempotency so retries are safe

7) Post‑summary straggler sweep
   - Capture high‑water mark (max last_updated) at start
   - After upsert, sweep and archive/delete stragglers ≤ HWM in [session_start, session_end]

8) ATC detection window
   - Call detection with canonical [session_start, session_end]
   - Keep controller proximity logic unchanged

9) Monitoring & integrity
   - Log merges/splits and reasons; daily duplicate check stays 0
   - Alert on overlaps, cap breaches

10) Tests (staged rollout)
   - Unit: merge logic, upsert behavior, archive windowing
   - Integration: end‑to‑end sessionization → summary → archive/delete → idempotency
   - Phase order: (1) selector tests, (2) archive/delete window tests, (3) summary upsert tests, (4) full e2e
   - Seeded data scope: rehydrate at least 50 real sessions from `flights_archive` into a test schema to simulate unprocessed flows; cover reconnects (≤2h, >2h), cross‑midnight, near 8h cap, multiple callsigns/cids/departure/arrival combinations; include minimal matching `transceivers` where ATC detection is exercised

### Known Flaw You Approved to Address (7) and Policy
7) JSON merge semantics
   - Policy: key‑wise union for `controller_callsigns` with conflict resolution (prefer latest timestamps, max counters). Recompute percentages from base counts/time, not simple max.

### Open Questions
6) Advisory lock scope: using (callsign, cid, departure, arrival). If you prefer a different scope (e.g., omit arrival), confirm.


