from datetime import datetime, timezone

import pytest

from app.services.detection_common import compute_detection_window, compute_prefilter_windows


def test_compute_detection_window_basic():
    rt = datetime(2025, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    w = compute_detection_window(rt, 180, 60)
    assert w["start"] == datetime(2025, 9, 2, 11, 57, 0, tzinfo=timezone.utc)
    # end = reference + time_window_seconds + polling_interval_seconds => 12:00 + 3min + 1min = 12:04
    assert w["end"] == datetime(2025, 9, 2, 12, 4, 0, tzinfo=timezone.utc)


def test_compute_prefilter_windows():
    rt = datetime(2025, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    p = compute_prefilter_windows(rt, 180)
    assert p["flight_start_time"].hour == 11
    assert p["flight_end_time"].hour == 12

