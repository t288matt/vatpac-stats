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


