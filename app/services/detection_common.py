#!/usr/bin/env python3
"""Shared detection helpers (window math and transceiver load strategy).

This module implements the canonical contract described in DETECTION_CONTRACT_AND_FIX_PLAN.md
so both ATC and Flight detection services compute identical windows and loading behaviour.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any


def compute_detection_window(reference_time: datetime, time_window_seconds: int, polling_interval_seconds: int) -> Dict[str, datetime]:
    """Compute canonical detection window.

    start = reference_time - time_window_seconds
    end = reference_time + time_window_seconds + polling_interval_seconds
    Returns UTC datetimes truncated to seconds.
    """
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    start = (reference_time - timedelta(seconds=time_window_seconds)).replace(microsecond=0)
    end = (reference_time + timedelta(seconds=time_window_seconds + polling_interval_seconds)).replace(microsecond=0)
    return {"start": start, "end": end}


def build_prefilter_and_loader(reference_time: datetime, time_window_seconds: int, polling_interval_seconds: int = 60, page_size: int = 10000) -> Dict[str, Any]:
    """Return commonly used prefilter timestamps and a loader strategy.

    - flight_start_time / flight_end_time: window used when loading flight transceivers
    - atc_start_time / atc_end_time: window used when loading ATC transceivers
    - loader: {'page_size': int, 'force_on_demand': bool}
    """
    # Use symmetric windows centered on reference_time
    win = compute_detection_window(reference_time, time_window_seconds, polling_interval_seconds)

    # For controller sessions we may want to expand to the full session later; caller may override
    return {
        "flight_start_time": win["start"],
        "flight_end_time": win["end"],
        "atc_start_time": win["start"],
        "atc_end_time": win["end"],
        "loader": {
            "page_size": page_size,
            "force_on_demand": False
        }
    }


def transceiver_load_strategy(window_start: datetime, window_end: datetime, last_cache_fetch: datetime = None, ttl_seconds: int = 120, page_size_default: int = 10000) -> Dict[str, Any]:
    """Decide whether to use cache or force on-demand loading and page size.

    Simple heuristic: if cache is stale compared to window_end - ttl_seconds then force on-demand.
    """
    strategy = {"force_on_demand": False, "page_size": page_size_default}
    if last_cache_fetch is None:
        strategy["force_on_demand"] = True
        return strategy

    # If window_end is newer than last_cache_fetch + ttl, force on-demand
    if window_end and last_cache_fetch and (window_end - last_cache_fetch).total_seconds() > ttl_seconds:
        strategy["force_on_demand"] = True

    return strategy

"""Shared detection helpers used by ATC and Flight detection services.

Provides canonical window math and simple transceiver loading strategy helpers so
both detection directions use identical semantics.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def compute_detection_window(reference_time: datetime, time_window_seconds: int, polling_interval_seconds: int = 0) -> Dict[str, datetime]:
    """Compute a canonical detection window centered on a reference time.

    Returns a dict with keys: start, end. Times are timezone-aware (UTC) and
    truncated to seconds.
    """
    rt = _ensure_utc(reference_time)
    # round to second precision
    rt = rt.replace(microsecond=0)

    start = rt - timedelta(seconds=time_window_seconds)
    end = rt + timedelta(seconds=time_window_seconds + polling_interval_seconds)

    return {"start": start, "end": end}


def compute_prefilter_windows(anchor_time: datetime, time_window_seconds: int) -> Dict[str, datetime]:
    """Compute the pre-filter windows used by SQL CTEs for detection queries.

    Returns a dict with keys: flight_start_time, flight_end_time, atc_start_time, atc_end_time.
    These are intended to be used directly in SQL pre-filter clauses.
    """
    at = _ensure_utc(anchor_time).replace(microsecond=0)

    flight_start_time = at - timedelta(seconds=time_window_seconds)
    flight_end_time = at + timedelta(seconds=time_window_seconds)

    # Expand ATC window by the same time_window on each side (matches existing approach)
    atc_start_time = flight_start_time - timedelta(seconds=time_window_seconds)
    atc_end_time = flight_end_time + timedelta(seconds=time_window_seconds)

    return {
        "flight_start_time": flight_start_time,
        "flight_end_time": flight_end_time,
        "atc_start_time": atc_start_time,
        "atc_end_time": atc_end_time,
    }



def transceiver_load_strategy(window_start: datetime | None, window_end: datetime | None, last_cache_fetch: datetime | None, ttl_seconds: int = 120, default_page_size: int = 10000) -> Dict[str, Any]:
    """Decide whether to use the cache or force an on-demand fetch and provide a page size.

    - If there is no cached snapshot (last_cache_fetch is None) force on-demand.
    - If cache is older than ttl_seconds force on-demand.
    - Otherwise prefer the cache and return a deterministic page size for any on-demand fallback.

    Returns: {"force_on_demand": bool, "page_size": int}
    """
    now = datetime.now(timezone.utc)
    if last_cache_fetch is None:
        return {"force_on_demand": True, "page_size": default_page_size}

    age = (now - last_cache_fetch).total_seconds()
    if age > ttl_seconds:
        return {"force_on_demand": True, "page_size": default_page_size}

    return {"force_on_demand": False, "page_size": default_page_size}


def build_prefilter_and_loader(anchor_time: datetime, time_window_seconds: int, polling_interval_seconds: int = 0, last_cache_fetch: datetime | None = None, ttl_seconds: int = 120, default_page_size: int = 10000) -> Dict[str, Any]:
    """Build canonical prefilter windows and a transceiver load strategy.

    Returns a dict with keys:
      - flight_start_time, flight_end_time
      - atc_start_time, atc_end_time
      - loader: {force_on_demand, page_size}

    Both detection services should use this to ensure identical prefilter
    windows and loader decisions.
    """
    # canonical windows
    windows = compute_prefilter_windows(anchor_time, time_window_seconds)

    # decide loader strategy based on windows and cache age
    loader = transceiver_load_strategy(windows.get("flight_start_time"), windows.get("flight_end_time"), last_cache_fetch, ttl_seconds=ttl_seconds, default_page_size=default_page_size)

    return {
        "flight_start_time": windows["flight_start_time"],
        "flight_end_time": windows["flight_end_time"],
        "atc_start_time": windows["atc_start_time"],
        "atc_end_time": windows["atc_end_time"],
        "loader": loader,
    }



