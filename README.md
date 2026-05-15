# ErrorMentor

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/errormentor)
![License](https://img.shields.io/badge/license-MIT-blue)

*56% of on-call time is triage. ErrorMentor cuts that to zero.*

**ErrorMentor** is an open-source CLI tool that auto-diagnoses production errors by correlating error logs with recent git commits and suggesting exact fixes using Claude AI.

When a 500 error spikes in production, on-call engineers spend most of their time triaging (which commit caused this? which service? which line?). ErrorMentor automatically answers "this error appeared 47 minutes after commit `abc1234` which touched `payment/processor.py` — here's the probable cause and the fix."

## Demo

*(Add demo.gif here)*

## Installation

```bash
pip install errormentor
```

## Quick Start

```bash
# Analyze a log file and correlate with git commits
errormentor analyze error.log --correlate
```

## Sample Output

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

## How It Works

1. **Parse Logs**: Structured regex-based parsing (JSON, logfmt, plain text).
2. **Detect Spike**: Sliding window algorithm to identify sudden error rate increases.
3. **Correlate Git**: Matches spike timestamp to recent git commits.
4. **AI Analysis**: Claude AI analyzes source context, git diffs, and the error to suggest a fix.

## Log Format Support

| Format | Support |
| --- | --- |
| JSON | ✅ |
| logfmt | ✅ |
| Plain Text | ✅ |
| Datadog | 🔜 |

## RootCause vs ErrorMentor

- **RootCause** = failing tests (dev time).
- **ErrorMentor** = production errors (on-call time).

Both use the same AI diagnosis approach.

## CI Integration

```bash
errormentor analyze --file staging.log --since "1h"
```

## License
MIT
