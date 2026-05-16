import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CommitInfo:
    hash: str
    timestamp: datetime
    message: str
    author: str
    files_touched: list[str]
    delta_seconds: int

class GitCorrelator:
    def __init__(self, search_window_minutes: int = 10):
        self.search_window_minutes = search_window_minutes

    def _run_cmd(self, cmd: list[str]) -> str:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""
        except FileNotFoundError:
             return ""

    def get_recent_commits(self, limit: int = 20) -> list[dict]:
        output = self._run_cmd(['git', 'log', '--format=%H|%ai|%s|%ae', f'-n{limit}'])
        if not output:
            return []

        commits = []
        for line in output.split('\n'):
            if not line:
                continue
            parts = line.split('|', 3)
            if len(parts) == 4:
                try:
                    # %ai looks like '2026-05-15 14:31:00 +0000'
                    ts = datetime.strptime(parts[1].strip(), '%Y-%m-%d %H:%M:%S %z')
                except ValueError:
                    ts = datetime.now(timezone.utc)

                commits.append({
                    'hash': parts[0],
                    'timestamp': ts,
                    'message': parts[2],
                    'author': parts[3]
                })
        return commits

    def get_files_touched(self, commit_hash: str) -> list[str]:
        output = self._run_cmd(['git', 'show', '--name-only', '--format=', commit_hash])
        return [line for line in output.split('\n') if line]

    def correlate(self, spike_started_at: datetime) -> Optional[CommitInfo]:
        commits = self.get_recent_commits()
        if not commits:
            return None

        candidates = []
        for c in commits:
            # We want commits BEFORE the spike, or exactly at the spike
            delta = (spike_started_at - c['timestamp']).total_seconds()

            # If delta is negative, commit is AFTER spike (not the cause)
            # If delta is too large, commit is too old
            if 0 <= delta <= (self.search_window_minutes * 60):
                candidates.append((delta, c))

        if not candidates:
            return None

        # Sort by delta (smallest positive delta first)
        candidates.sort(key=lambda x: x[0])
        best_delta, best_commit = candidates[0]

        files_touched = self.get_files_touched(best_commit['hash'])

        return CommitInfo(
            hash=best_commit['hash'],
            timestamp=best_commit['timestamp'],
            message=best_commit['message'],
            author=best_commit['author'],
            files_touched=files_touched,
            delta_seconds=int(best_delta)
        )
