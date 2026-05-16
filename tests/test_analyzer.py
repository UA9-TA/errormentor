import pytest
from datetime import datetime, timezone
from errormentor.analyzer import Analyzer
from errormentor.spike_detector import SpikeReport
from errormentor.git_correlator import CommitInfo

def test_build_prompt():
    analyzer = Analyzer(api_key="test_key")

    spike = SpikeReport(
        error_type="TestError",
        spike_started_at=datetime(2026, 5, 15, 14, 32, tzinfo=timezone.utc),
        baseline_rate=1.0,
        peak_rate=5.0,
        acceleration_factor=5.0
    )

    commit = CommitInfo(
        hash="abc1234",
        timestamp=datetime(2026, 5, 15, 14, 31, tzinfo=timezone.utc),
        message="Test commit",
        author="dev@test.com",
        files_touched=["test.py"],
        delta_seconds=60
    )

    prompt = analyzer._build_prompt(spike, commit, "Test error happened", "source code here", "git diff here")

    assert "TestError" in prompt
    assert "1.0/min → 5.0/min" in prompt
    assert "abc1234" in prompt
    assert "test.py" in prompt
    assert "source code here" in prompt
    assert "git diff here" in prompt

def test_parse_json():
    analyzer = Analyzer(api_key="test_key")

    # Valid JSON
    text1 = '{"root_cause": "test", "location": "test.py:1", "explanation": "test", "fix": "test", "also_found": [], "confidence": 100, "fix_diff": null}'
    res1 = analyzer._parse_json(text1)
    assert res1["root_cause"] == "test"

    # JSON with markdown block
    text2 = '```json\n{"root_cause": "test2"}\n```'
    res2 = analyzer._parse_json(text2)
    assert res2["root_cause"] == "test2"

    # Invalid JSON
    text3 = "This is not JSON"
    res3 = analyzer._parse_json(text3)
    assert res3["confidence"] == 0
    assert "Failed to parse API response" in res3["root_cause"]
