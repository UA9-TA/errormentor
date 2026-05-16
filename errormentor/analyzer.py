import json
from typing import Any

from anthropic import Anthropic

from .spike_detector import SpikeReport
from .git_correlator import CommitInfo


class Analyzer:
    def __init__(self, api_key: str):
        # We assume anthropic is installed and will pick up ANTHROPIC_API_KEY
        # from env if api_key is not explicitly passed.
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model = "claude-3-7-sonnet-20250219"

    def analyze(self,
                spike: SpikeReport,
                commit: CommitInfo,
                top_error_message: str,
                source_context: str,
                git_context: str) -> dict[str, Any]:

        prompt = self._build_prompt(
            spike=spike,
            commit=commit,
            top_error_message=top_error_message,
            source_context=source_context,
            git_context=git_context
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        text = response.content[0].text

        return self._parse_json(text)

    def _build_prompt(self, spike: SpikeReport, commit: CommitInfo, top_error_message: str, source_context: str, git_context: str) -> str:
        return f"""You are a production incident analyst.

## Error Log Summary
Error type: {spike.error_type}
Frequency spike: {spike.baseline_rate}/min → {spike.peak_rate}/min at {spike.spike_started_at.isoformat()}
Most common message: {top_error_message}

## Most Likely Culprit Commit
{commit.hash}: {commit.message}
Files changed: {', '.join(commit.files_touched)}
Time before spike: {commit.delta_seconds}s

## Source Code at Error Location
{source_context}

## Recent Git Changes to These Files
{git_context}

Analyze the information above and determine the root cause of the error spike.

Respond with ONLY valid JSON:
{{
  "root_cause": "one sentence",
  "location": "file.py:line",
  "explanation": "2-4 sentences",
  "fix": "exact code change",
  "also_found": [],
  "confidence": 94,
  "fix_diff": "unified diff or null"
}}"""

    def _parse_json(self, text: str) -> dict[str, Any]:
        # Try to find json block if they wrapped it
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            return {
                "root_cause": "Failed to parse API response",
                "location": "unknown",
                "explanation": f"The API returned invalid JSON: {e}\n\nRaw response:\n{text}",
                "fix": "none",
                "also_found": [],
                "confidence": 0,
                "fix_diff": None
            }
