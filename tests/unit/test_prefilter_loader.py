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



