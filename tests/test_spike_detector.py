from datetime import datetime, timedelta, timezone

from errormentor.log_parser import ErrorEvent
from errormentor.spike_detector import SpikeDetector


def test_detect_spike():
    detector = SpikeDetector(window_size_minutes=1, baseline_minutes=30, threshold=3.0)

    events = []
    base_time = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)

    # Baseline: 1 error per minute for 30 mins
    for i in range(30):
        events.append(ErrorEvent(
            timestamp=base_time + timedelta(minutes=i),
            level="ERROR",
            service="test",
            message="TestError",
            error_type="TestError",
            traceback=None,
            file_locations=[]
        ))

    # Spike: 5 errors in the 31st minute
    spike_time = base_time + timedelta(minutes=30)
    for i in range(5):
        events.append(ErrorEvent(
            timestamp=spike_time + timedelta(seconds=i*10),
            level="ERROR",
            service="test",
            message="TestError",
            error_type="TestError",
            traceback=None,
            file_locations=[]
        ))

    report = detector.detect(events)

    assert report is not None
    assert report.error_type == "TestError"
    assert report.baseline_rate == 1.0
    assert report.peak_rate == 5.0
    assert report.acceleration_factor == 5.0
    assert report.spike_started_at == spike_time
