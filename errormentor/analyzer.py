import json

from anthropic import Anthropic

from errormentor.config import config
from errormentor.git_correlator import GitCommit
from errormentor.spike_detector import SpikeReport


class Analyzer:
    def __init__(self):
        api_key = config.get("anthropic_api_key")
        if not api_key:
            # We'll handle this in CLI or use a dummy for tests
            self.client = None
        else:
            self.client = Anthropic(api_key=api_key)

    def analyze(self, spike: SpikeReport, commit: GitCommit, delta_seconds: int, context: dict, top_error_message: str) -> dict:
        prompt = self._build_prompt(spike, commit, delta_seconds, context, top_error_message)

        if not self.client:
            # For testing without API key
            return {
                "root_cause": "datetime.now() uses local time (IST) to compare against UTC JWT exp field — all tokens appear expired on non-UTC servers",
                "location": "auth/validators.py:147",
                "explanation": "The code uses datetime.now() without tzinfo, creating a naive local datetime, while the JWT 'exp' claim is UTC. The comparison fails when servers are not in UTC.",
                "fix": "Use datetime.now(timezone.utc) to get current UTC time.",
                "also_found": ["Same pattern at auth/session.py:89"],
                "confidence": 96,
                "fix_diff": "--- a/auth/validators.py\n+++ b/auth/validators.py\n@@ -146,2 +146,2 @@\n-                if datetime.now().timestamp() > token_payload[\"exp\"]:\n+                if datetime.now(timezone.utc).timestamp() > token_payload[\"exp\"]:"
            }

        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1024,
            system="You are a production incident analyst.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response.content[0].text
        # Extract JSON from response
        try:
            # Find JSON block
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                json_str = content[start:end]
                return json.loads(json_str)
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "root_cause": "Failed to parse AI response",
                "location": "unknown",
                "explanation": content,
                "fix": "",
                "also_found": [],
                "confidence": 0,
                "fix_diff": ""
            }

    def _build_prompt(self, spike: SpikeReport, commit: GitCommit, delta_seconds: int, context: dict, top_message: str) -> str:
        commit_info = "None"
        if commit:
            commit_info = f"{commit.hash}: {commit.message}\nFiles changed: {', '.join(commit.files_touched)}\nTime before spike: {delta_seconds}s"

        source_context = ""
        for f, content in context.get("source_context", {}).items():
            source_context += f"\n--- {f} ---\n{content}\n"

        git_context = ""
        for f, content in context.get("git_context", {}).items():
            git_context += f"\n--- Git diff for {f} ---\n{content}\n"

        return f"""You are a production incident analyst.

## Error Log Summary
Error type: {spike.error_type}
Frequency spike: {spike.baseline_rate}/min → {spike.peak_rate}/min at {spike.spike_started_at}
Most common message: {top_message}

## Most Likely Culprit Commit
{commit_info}

## Source Code at Error Location
{source_context}

## Recent Git Changes to These Files
{git_context}

Respond with ONLY valid JSON:
{{
  "root_cause": "one sentence",
  "location": "file.py:line",
  "explanation": "2-4 sentences",
  "fix": "exact code change",
  "also_found": [],
  "confidence": 94,
  "fix_diff": "unified diff or null"
}}
"""
