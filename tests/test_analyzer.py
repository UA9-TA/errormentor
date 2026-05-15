from datetime import datetime, timezone

from errormentor.analyzer import Analyzer
from errormentor.git_correlator import GitCommit
from errormentor.spike_detector import SpikeReport


def test_analyzer_dummy():
    analyzer = Analyzer()
    analyzer.client = None # Force dummy mode

    spike = SpikeReport(
        error_type="AuthTokenError",
        spike_started_at=datetime(2026, 5, 15, 14, 32, tzinfo=timezone.utc),
        baseline_rate=1.0,
        peak_rate=10.0,
        acceleration_factor=10.0
    )

    commit = GitCommit(
        hash="abc1234",
        timestamp=datetime(2026, 5, 15, 14, 31, tzinfo=timezone.utc),
        message="feat: migrate auth",
        author="dev@company.com",
        files_touched=["auth/validators.py"]
    )

    result = analyzer.analyze(spike, commit, 60, {}, "AuthTokenError: Token expired")

    assert result["location"] == "auth/validators.py:147"
    assert "datetime.now(timezone.utc)" in result["fix"]
