# ErrorMentor

![PyPI](https://img.shields.io/pypi/v/errormentor)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

> **56% of on-call time is triage. ErrorMentor cuts that to zero.**

ErrorMentor is an open-source CLI tool that auto-diagnoses production errors by correlating error logs with recent git commits and suggesting exact fixes using Claude AI.

## The Problem

It's 2 AM. A production spike hits 18 errors/min. You have no idea which of the 12 recent commits caused it, or where the bug is. On-call engineers spend the majority of their time just finding the root cause. ErrorMentor automatically analyzes your log stream, finds the spike, correlates it with the exact git commit that deployed right before it, and uses AI to pinpoint the exact line of code to fix.

## Install

```bash
pip install errormentor
```

## Quick Start

```bash
# Analyze a log file and correlate with git history
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

1. **Parse logs:** Reads JSON, logfmt, or plain text logs to find errors.
2. **Detect spike:** Uses a sliding window algorithm to detect sudden increases in error rates.
3. **Correlate with git:** Finds the commit deployed right before the spike started.
4. **Claude analysis:** Packages the error context, git diffs, and source code and sends it to Claude for a definitive diagnosis and fix.

## Log Format Support

| Format | Support |
|---|---|
| JSON | ✅ |
| Logfmt | ✅ |
| Plain Text | ✅ |
| Datadog | 🔜 |

## RootCause vs ErrorMentor

- **RootCause:** For failing tests (dev time).
- **ErrorMentor:** For production errors (on-call time).
Both use the same AI-powered approach to find exactly what went wrong and how to fix it.

## CI Integration

You can use ErrorMentor as a post-deploy health check in CI:
```bash
errormentor analyze --file staging.log --since "1h"
```

## Configuration

ErrorMentor reads `ANTHROPIC_API_KEY` from your environment. You can also configure it via `~/.errormentor/config.toml`.

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

## Contributing / License

MIT License. Issues and PRs welcome!
