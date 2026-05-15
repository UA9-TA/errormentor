from datetime import datetime, timedelta, timezone

from errormentor.log_parser import ErrorEvent
from errormentor.spike_detector import SpikeDetector


def test_detect_spike():
    detector = SpikeDetector()

    events = []
    base_time = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)

    # Baseline: 1 error per minute for 30 minutes
    for i in range(30):
        events.append(ErrorEvent(
            timestamp=base_time + timedelta(minutes=i),
            level="ERROR",
            service="auth",
            message="AuthTokenError: token expired",
            error_type="AuthTokenError"
        ))

    # Spike: 10 errors in 1 minute
    spike_time = base_time + timedelta(minutes=31)
    for _ in range(10):
        events.append(ErrorEvent(
            timestamp=spike_time,
            level="ERROR",
            service="auth",
            message="AuthTokenError: token expired",
            error_type="AuthTokenError"
        ))

    report = detector.detect(events)

    assert report is not None
    assert report.error_type == "AuthTokenError"
    assert report.spike_started_at == spike_time
    assert report.peak_rate == 10
    # Baseline was 30 errors in 30 minutes -> 1 per minute
    assert report.baseline_rate == 1.0
