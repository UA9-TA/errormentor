import pytest
from datetime import datetime, timezone
from errormentor.git_correlator import GitCorrelator, CommitInfo

def test_correlate(mocker):
    correlator = GitCorrelator()

    # Mock get_recent_commits
    mocker.patch.object(correlator, 'get_recent_commits', return_value=[
        {
            'hash': 'abc1234',
            'timestamp': datetime(2026, 5, 15, 14, 31, tzinfo=timezone.utc),
            'message': 'feat: migrate auth',
            'author': 'dev@test.com'
        },
        {
            'hash': 'def5678',
            'timestamp': datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc),
            'message': 'fix typo',
            'author': 'docs@test.com'
        }
    ])

    # Mock get_files_touched
    mocker.patch.object(correlator, 'get_files_touched', return_value=['auth/validators.py'])

    # Spike at 14:32, the 14:31 commit should be selected (delta = 60s)
    spike_time = datetime(2026, 5, 15, 14, 32, tzinfo=timezone.utc)

    info = correlator.correlate(spike_time)

    assert info is not None
    assert info.hash == 'abc1234'
    assert info.delta_seconds == 60
    assert info.files_touched == ['auth/validators.py']
