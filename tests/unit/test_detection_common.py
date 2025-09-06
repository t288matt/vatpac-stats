import pytest
from datetime import datetime, timezone
from app.services.detection_common import compute_detection_window, compute_prefilter_windows


def test_compute_detection_window_truncation_and_bounds():
    rt = datetime(2025, 9, 4, 12, 0, 30, 123456, tzinfo=timezone.utc)
    w = compute_detection_window(rt, 180, 60)
    # truncated to seconds
    assert w["start"].microsecond == 0
    assert w["end"].microsecond == 0
    assert (w["end"] - w["start"]).total_seconds() == 420  # 180 + 180 + 60


def test_compute_prefilter_windows_symmetry():
    anchor = datetime(2025, 9, 4, 12, 0, 0, tzinfo=timezone.utc)
    p = compute_prefilter_windows(anchor, 180)
    assert p["flight_start_time"] < p["flight_end_time"]
    assert p["atc_start_time"] < p["atc_end_time"]
    # ATC window should be expanded by time_window on both sides
    assert (p["flight_start_time"] - p["atc_start_time"]).total_seconds() == 180
    assert (p["atc_end_time"] - p["flight_end_time"]).total_seconds() == 180

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

