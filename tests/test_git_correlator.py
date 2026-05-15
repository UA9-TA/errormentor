from datetime import datetime, timezone
from unittest.mock import patch

from errormentor.git_correlator import GitCorrelator


@patch("errormentor.git_correlator.subprocess.run")
def test_git_correlator(mock_run):
    # Mock for `git log`
    mock_run.return_value.stdout = "abc1234 2026-05-15T14:31:00Z feat: migrate auth to new token service dev@company.com"

    correlator = GitCorrelator()

    # We also mock get_files_touched since it calls subprocess
    with patch.object(correlator, 'get_files_touched', return_value=["auth/validators.py"]):
        spike_time = datetime(2026, 5, 15, 14, 32, 0, tzinfo=timezone.utc)
        commits = correlator.get_commits_around(spike_time)

        assert len(commits) == 1
        assert commits[0].hash == "abc1234"
        assert commits[0].author == "dev@company.com"
        assert "auth/validators.py" in commits[0].files_touched
