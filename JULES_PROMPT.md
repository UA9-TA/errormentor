# Jules Build Prompt — ErrorMentor v1.0

## What You Are Building

**ErrorMentor** is an open-source CLI tool that auto-diagnoses production errors by correlating error logs with recent git commits and suggesting exact fixes using Claude AI. It is RootCause for production — where RootCause analyzes failing tests, ErrorMentor analyzes live error streams.

The core problem: When a 500 error spikes in production, on-call engineers spend 56% of their time *triaging* (which commit caused this? which service? which line?) and only 44% actually fixing. No tool automatically answers "this error appeared 47 minutes after commit `abc1234` which touched `payment/processor.py` — here's the probable cause and the fix." ErrorMentor does exactly that.

**Target:** Top GitHub trending. On-call is every engineer's nightmare. This makes it survivable.

---

## Core User Flow

```bash
# Install
pip install errormentor

# Analyze a log file or error stream
errormentor analyze error.log
errormentor analyze --tail /var/log/app/error.log   # live tail mode

# Correlate with recent git commits (run from repo root)
errormentor analyze error.log --correlate

# Connect to log aggregators
errormentor analyze --datadog "service:api status:error last:1h"
errormentor analyze --file error.log --since "30 minutes ago"

# Show the diagnosis
errormentor diagnose error.log

# Auto-generate a fix suggestion
errormentor fix error.log
```

**Output:**
```
ErrorMentor — Production Error Analysis
──────────────────────────────────────────────────
✦ Errors analyzed     847 log lines, 3 unique error types
✦ Spike detected      AuthTokenError  ↑ 340% at 14:32 UTC

  ── Root Cause ────────────────────────────────────
  Error         AuthTokenError: Token expired: local_now=..., exp=...
  Location      auth/validators.py:147
  Frequency     3.2/min → 18.7/min (spike started 14:32)

  ── Git Correlation ───────────────────────────────
  Most likely commit:
  abc1234  14:31 UTC  feat: migrate auth to new token service
  Author: dev@company.com
  Files touched: auth/validators.py, auth/session.py

  Time delta: error spike began 47 seconds after deploy

  ── AI Analysis ───────────────────────────────────
  Root cause    datetime.now() uses local time (IST) to compare
                against UTC JWT exp field — all tokens appear expired
                on non-UTC servers

  Fix           auth/validators.py line 147:
                - if datetime.now().timestamp() > token_payload["exp"]:
                + if datetime.now(timezone.utc).timestamp() > token_payload["exp"]:

  Also found    Same pattern at auth/session.py:89

  Confidence    96%
──────────────────────────────────────────────────
Apply fix automatically? [y/N]
```

---

## Tech Stack

- **Language:** Python 3.10+
- **CLI framework:** Typer + Rich
- **AI:** Anthropic Claude API (`claude-sonnet-4-6`) via `anthropic` Python SDK
- **Log parsing:** regex-based structured log parser (handles JSON logs, logfmt, and plain text)
- **Git integration:** `subprocess` + `git log`
- **Time-series spike detection:** simple sliding window algorithm (no ML needed)
- **Optional integrations:** Datadog API (`httpx`), file tail mode
- **Packaging:** `pyproject.toml` (hatchling), entry point `errormentor`
- **Config:** `~/.errormentor/config.toml`

---

## Project Structure

```
errormentor/
├── errormentor/
│   ├── __init__.py
│   ├── cli.py              # Typer app — analyze, diagnose, fix, config
│   ├── log_parser.py       # Parses log files into structured ErrorEvent list
│   ├── spike_detector.py   # Detects error rate spikes using sliding window
│   ├── git_correlator.py   # Matches spike timestamp to recent git commits
│   ├── context_builder.py  # Gathers source code context around error locations
│   ├── analyzer.py         # Sends everything to Claude, parses response
│   ├── patcher.py          # Applies the suggested fix (reused from RootCause pattern)
│   ├── display.py          # Rich terminal output
│   └── config.py           # Config reader/writer
├── tests/
│   ├── test_log_parser.py
│   ├── test_spike_detector.py
│   ├── test_git_correlator.py
│   ├── test_analyzer.py
│   └── fixtures/
│       ├── sample_error.log      # 80-line production log with clear spike
│       └── sample_git_log.txt    # git log output — culprit commit just before spike
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
└── README.md
```

---

## Detailed Module Specs

### `log_parser.py` — Log parsing
Support three log formats:

**JSON logs:**
```json
{"timestamp": "2026-05-15T14:32:01Z", "level": "ERROR", "service": "auth", "message": "AuthTokenError", "trace": "..."}
```

**Logfmt:**
```
time=2026-05-15T14:32:01Z level=error service=auth msg="AuthTokenError"
```

**Plain text (with timestamp prefix):**
```
2026-05-15T14:32:01Z [ERROR] auth_service  AuthTokenError: Token expired
```

Return list of `ErrorEvent` dataclasses:
```python
@dataclass
class ErrorEvent:
    timestamp: datetime
    level: str
    service: str
    message: str
    error_type: Optional[str]      # e.g. "AuthTokenError"
    traceback: Optional[str]
    file_locations: list[dict]     # [{file, line}] extracted from traceback
```

### `spike_detector.py` — Spike detection
Sliding window algorithm:
- Bucket errors by 1-minute windows
- Baseline: average rate over preceding 30 minutes
- Spike threshold: current minute rate > 3× baseline
- Return `SpikeReport`: `{error_type, spike_started_at, baseline_rate, peak_rate, acceleration_factor}`

### `git_correlator.py` — Commit correlation
- `git log --format="%H %ai %s %ae" -n 20`
- Find commits within 10 minutes before spike start
- Return ranked list: commits closest in time to spike start = highest probability
- Include `files_touched` via `git show --stat {hash}`

### `context_builder.py` — Source context
Reuse RootCause's approach:
- For each `file_location` in error events: read ±30 lines around error line
- Get recent git diff for those files (`git log -n5 -p -- {file}`)
- Return structured context dict

### `analyzer.py` — Claude API integration
Build prompt:
```
You are a production incident analyst.

## Error Log Summary
Error type: {error_type}
Frequency spike: {baseline_rate}/min → {peak_rate}/min at {spike_time}
Most common message: {top_error_message}

## Most Likely Culprit Commit
{commit_hash}: {commit_message}
Files changed: {files_touched}
Time before spike: {delta_seconds}s

## Source Code at Error Location
{source_context}

## Recent Git Changes to These Files
{git_context}

Respond with ONLY valid JSON:
{
  "root_cause": "one sentence",
  "location": "file.py:line",
  "explanation": "2-4 sentences",
  "fix": "exact code change",
  "also_found": [],
  "confidence": 94,
  "fix_diff": "unified diff or null"
}
```

---

## README Spec

1. **Hero** — badges + one-liner: *"56% of on-call time is triage. ErrorMentor cuts that to zero."*
2. **The problem** — production spike at 2 AM, 18 errors/min, no idea which of 12 recent commits caused it
3. **Demo** — `<!-- Add demo.gif here -->`
4. **Install** — `pip install errormentor`
5. **Quick start** — `errormentor analyze error.log --correlate`
6. **Sample output** — exact Rich output from above
7. **How it works** — 4-step: parse logs → detect spike → correlate with git → Claude analysis
8. **Log format support** — table: JSON ✅, logfmt ✅, plain text ✅, Datadog 🔜
9. **RootCause vs ErrorMentor** — RootCause = failing tests (dev time). ErrorMentor = production errors (on-call time). Both use the same approach.
10. **CI integration** — `errormentor analyze --file staging.log --since "1h"` as post-deploy health check
11. **Configuration** — API key, Datadog/Grafana integration
12. **Contributing / License**

---

## `pyproject.toml`

```toml
[project]
name = "errormentor"
version = "0.1.0"
description = "Auto-diagnose production errors by correlating logs with recent commits and AI analysis"
authors = [{name = "UA9-TA", email = "vkrmsatsangi@gmail.com"}]
keywords = ["debugging", "production", "logs", "on-call", "developer-tools", "cli", "ai", "incident"]
dependencies = [
    "typer>=0.12", "rich>=13", "anthropic>=0.25",
    "tomli>=2.0; python_version < '3.11'",
]
[project.optional-dependencies]
dev = ["pytest", "ruff", "pytest-mock", "pytest-cov"]
datadog = ["httpx>=0.27"]
[project.scripts]
errormentor = "errormentor.cli:app"
[project.urls]
Homepage = "https://github.com/UA9-TA/errormentor"
Changelog = "https://github.com/UA9-TA/errormentor/blob/main/CHANGELOG.md"
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--ignore=tests/fixtures"
[tool.ruff]
line-length = 100
target-version = "py310"
[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]
```

---

## Fixtures

### `tests/fixtures/sample_error.log`
The 80-line production log already built for RootCause (the auth service JWT timezone bug). Reuse the same realistic multi-service log format with the AuthTokenError spike at 14:32 — ErrorMentor should detect the spike and point to `auth/validators.py:147`.

### `tests/fixtures/sample_git_log.txt`
`git log` output (10 commits) where `abc1234 feat: migrate auth to new token service` is timestamped at 14:31 — 47 seconds before the spike. This is the culprit commit ErrorMentor should surface.

---

## Definition of Done

- [ ] `errormentor analyze tests/fixtures/sample_error.log` parses all 80 lines
- [ ] Spike detected correctly at 14:32 for AuthTokenError
- [ ] `--correlate` flag reads `sample_git_log.txt` and surfaces the 14:31 commit as culprit
- [ ] Claude analysis returns root cause pointing to `auth/validators.py:147`
- [ ] Fix suggestion matches the datetime.now() → datetime.now(timezone.utc) change
- [ ] `Apply fix automatically?` prompt works
- [ ] CI passes on Python 3.10, 3.11, 3.12
- [ ] ruff passes


## The Developer Toolkit Ecosystem

This tool is part of a suite of open-source AI-powered developer tools built by the same team:

| Tool | What it does |
|---|---|
| **[RootCause](https://github.com/UA9-TA/rootcause)** | Auto-diagnose failing tests — AI root cause + fix |
| **[ErrorMentor](https://github.com/UA9-TA/errormentor)** | Auto-diagnose production errors — correlate logs with git commits |
| **[TestGap](https://github.com/UA9-TA/testgap)** | Find untested code paths after every commit |
| **[HalluCheck](https://github.com/UA9-TA/hallucheck)** | Catch AI hallucinations in code diffs |
| **[IntentDiff](https://github.com/UA9-TA/intentdiff)** | Understand what a diff *actually* does semantically |
| **[DepSecure](https://github.com/UA9-TA/depsecure)** | Block vulnerable dependencies at commit time |
| **[ArchGuard](https://github.com/UA9-TA/archguard)** | Enforce microservice architecture rules across repos |
| **[SpendSentry](https://github.com/UA9-TA/spendsentry)** | Monitor cloud spend in real time — alert before costs spiral |
| **[ContextKit](https://github.com/UA9-TA/contextkit)** | Build minimal AI context bundles — 88% fewer tokens |

## Repo Details
- GitHub: https://github.com/UA9-TA/errormentor
- Local path: /Users/chitra/Documents/Projects/errormentor
- Branch: main — License: MIT
