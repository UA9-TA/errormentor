import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ErrorEvent:
    timestamp: datetime
    level: str
    service: str
    message: str
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    file_locations: list[dict] = field(default_factory=list)

class LogParser:
    def __init__(self):
        self.plain_text_pattern = re.compile(
            r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) \[(?P<level>[A-Z]+)\] (?P<service>\S+)\s+(?P<message>.*)$"
        )

    def parse_line(self, line: str) -> Optional[ErrorEvent]:
        line = line.strip()
        if not line:
            return None

        # Try JSON
        try:
            data = json.loads(line)
            return self._parse_json(data)
        except json.JSONDecodeError:
            pass

        # Try logfmt
        if "=" in line and ("time=" in line or "msg=" in line):
            parsed = self._parse_logfmt(line)
            if parsed:
                return parsed

        # Try plain text
        match = self.plain_text_pattern.match(line)
        if match:
            return self._parse_plain_text(match.groupdict())

        return None

    def parse_file(self, filepath: str) -> list[ErrorEvent]:
        events = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                event = self.parse_line(line)
                if event:
                    events.append(event)
        return events

    def _parse_timestamp(self, ts_str: str) -> datetime:
        # Simplistic parsing for ISO 8601 UTC
        try:
            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            return dt
        except ValueError:
            return datetime.now(timezone.utc)

    def _extract_error_type(self, message: str) -> Optional[str]:
        # e.g., "AuthTokenError: Token expired"
        if ":" in message:
            parts = message.split(":", 1)
            possible_type = parts[0].strip()
            if possible_type and " " not in possible_type:
                return possible_type
        return None

    def _parse_json(self, data: dict) -> Optional[ErrorEvent]:
        if "timestamp" not in data or "level" not in data:
            return None

        message = data.get("message", "")
        error_type = self._extract_error_type(message)

        return ErrorEvent(
            timestamp=self._parse_timestamp(data["timestamp"]),
            level=data["level"].upper(),
            service=data.get("service", "unknown"),
            message=message,
            error_type=error_type,
            traceback=data.get("trace"),
            file_locations=[] # TODO: extract from traceback if needed
        )

    def _parse_logfmt(self, line: str) -> Optional[ErrorEvent]:
        parts = {}
        # Simple logfmt parser
        # time=2026-05-15T14:32:01Z level=error service=auth msg="AuthTokenError"
        # Regex could be better but let's use a simple split for now
        matches = re.finditer(r'([a-zA-Z0-9_]+)=(?:"([^"]*)"|(\S+))', line)
        for match in matches:
            key = match.group(1)
            val = match.group(2) if match.group(2) is not None else match.group(3)
            parts[key] = val

        if "time" not in parts or "level" not in parts:
            return None

        message = parts.get("msg", "")
        error_type = self._extract_error_type(message)

        return ErrorEvent(
            timestamp=self._parse_timestamp(parts["time"]),
            level=parts["level"].upper(),
            service=parts.get("service", "unknown"),
            message=message,
            error_type=error_type
        )

    def _parse_plain_text(self, data: dict) -> ErrorEvent:
        message = data.get("message", "")
        error_type = self._extract_error_type(message)

        return ErrorEvent(
            timestamp=self._parse_timestamp(data["timestamp"]),
            level=data["level"].upper(),
            service=data.get("service", "unknown"),
            message=message,
            error_type=error_type
        )
