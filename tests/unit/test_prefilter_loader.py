import pytest
from datetime import datetime, timezone, timedelta
from app.services.detection_common import compute_detection_window, build_prefilter_and_loader, transceiver_load_strategy


def test_compute_detection_window_truncation():
    ref = datetime(2025, 9, 4, 12, 0, 30, 123456, tzinfo=timezone.utc)
    win = compute_detection_window(ref, 180, 60)
    assert win["start"].microsecond == 0
    assert win["end"].microsecond == 0
    assert (win["end"] - win["start"]).total_seconds() == 180 + 180 + 60


def test_build_prefilter_and_loader_defaults():
    ref = datetime(2025, 9, 4, 12, 0, tzinfo=timezone.utc)
    pre = build_prefilter_and_loader(ref, 180, 60, page_size=5000)
    assert "flight_start_time" in pre and "atc_start_time" in pre
    assert pre["loader"]["page_size"] == 5000


def test_transceiver_load_strategy_force_on_demand():
    start = datetime(2025,9,4,10,0,tzinfo=timezone.utc)
    end = datetime(2025,9,4,11,0,tzinfo=timezone.utc)
    # no cache fetch => force on demand
    strat = transceiver_load_strategy(start, end, None, ttl_seconds=120, page_size_default=1000)
    assert strat["force_on_demand"]

    # stale cache
    last_fetch = datetime(2025,9,4,9,0,tzinfo=timezone.utc)
    strat2 = transceiver_load_strategy(start, end, last_fetch, ttl_seconds=120)
    assert strat2["force_on_demand"]

from datetime import datetime, timezone
from app.services.detection_common import build_prefilter_and_loader, compute_prefilter_windows


def test_build_prefilter_and_loader_consistency():
    anchor = datetime(2025, 9, 4, 12, 0, 0, tzinfo=timezone.utc)
    pre = build_prefilter_and_loader(anchor, 180, polling_interval_seconds=60)
    windows = compute_prefilter_windows(anchor, 180)

    assert pre["flight_start_time"] == windows["flight_start_time"]
    assert pre["flight_end_time"] == windows["flight_end_time"]
    assert pre["atc_start_time"] == windows["atc_start_time"]
    assert pre["atc_end_time"] == windows["atc_end_time"]
    assert "loader" in pre and "page_size" in pre["loader"]



