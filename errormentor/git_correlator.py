import re
import subprocess
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GitCommit:
    hash: str
    timestamp: datetime
    message: str
    author: str
    files_touched: list[str]

class GitCorrelator:
    def get_commits_around(self, spike_time: datetime) -> list[GitCommit]:
        # get last 20 commits
        try:
            result = subprocess.run(
                ["git", "log", "--format=%H %aI %s %ae", "-n", "20"],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            # Example format: hash ISO8601 message author
            # e.g., abc1234 2026-05-15T14:31:00Z feat: migrate auth dev@company.com
            # Since message can contain spaces, we need to extract correctly
            match = re.match(r"^([a-f0-9]+)\s+(\S+)\s+(.*?)\s+(\S+@[^\s]+)$", line)
            if not match:
                # Try simpler approach if regex fails
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    hash_val = parts[0]
                    ts_str = parts[1]
                    rest = parts[2]

                    author_match = re.search(r'\s+(\S+@[^\s]+)$', rest)
                    if author_match:
                        author = author_match.group(1)
                        message = rest[:author_match.start()]
                    else:
                        author = "unknown"
                        message = rest
                else:
                    continue
            else:
                hash_val = match.group(1)
                ts_str = match.group(2)
                message = match.group(3)
                author = match.group(4)

            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            except ValueError:
                continue

            # Fetch files touched
            files_touched = self.get_files_touched(hash_val)

            commits.append(GitCommit(
                hash=hash_val,
                timestamp=ts,
                message=message,
                author=author,
                files_touched=files_touched
            ))

        # Find commits within 10 minutes before spike start
        # Sort them: closest in time to spike start = highest probability
        relevant_commits = []
        for c in commits:
            delta = (spike_time - c.timestamp).total_seconds()
            if 0 <= delta <= 600:  # 10 minutes
                relevant_commits.append((delta, c))

        relevant_commits.sort(key=lambda x: x[0])  # Sort by delta ascending
        return [c for _, c in relevant_commits]

    def get_files_touched(self, commit_hash: str) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "show", "--name-only", "--format=", commit_hash],
                capture_output=True,
                text=True,
                check=True
            )
            return [line.strip() for line in result.stdout.split("\n") if line.strip()]
        except subprocess.CalledProcessError:
            return []
