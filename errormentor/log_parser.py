import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ErrorEvent:
    timestamp: datetime
    level: str
    service: str
    message: str
    error_type: Optional[str]
    traceback: Optional[str]
    file_locations: list[dict]


class LogParser:
    def __init__(self):
        # Match iso8601-like timestamps
        self.timestamp_regex = re.compile(
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)'
        )
        self.plain_text_regex = re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)\s+'
            r'\[(?P<level>\w+)\]\s+'
            r'(?P<service>\w+)\s+'
            r'(?:(?P<error_type>\w+):\s+)?(?P<message>.*)'
        )
        self.traceback_regex = re.compile(
            r'File "(?P<file>[^"]+)", line (?P<line>\d+)'
        )

    def parse_line(self, line: str) -> Optional[ErrorEvent]:
        line = line.strip()
        if not line:
            return None

        # Try JSON
        if line.startswith('{') and line.endswith('}'):
            try:
                data = json.loads(line)
                return self._parse_json(data)
            except json.JSONDecodeError:
                pass

        # Try logfmt
        if 'time=' in line and 'level=' in line:
            return self._parse_logfmt(line)

        # Try plain text
        match = self.plain_text_regex.search(line)
        if match:
            return self._parse_plain_text(match.groupdict(), line)

        return None

    def _parse_timestamp(self, ts_str: str) -> datetime:
        if ts_str.endswith('Z'):
            ts_str = ts_str[:-1] + '+00:00'
        try:
            return datetime.fromisoformat(ts_str)
        except ValueError:
            return datetime.now(timezone.utc)

    def _parse_json(self, data: dict) -> ErrorEvent:
        timestamp_str = data.get('timestamp', '')
        timestamp = self._parse_timestamp(timestamp_str) if timestamp_str else datetime.now(timezone.utc)

        message = data.get('message', '')
        error_type = data.get('error_type')
        if not error_type and ':' in message:
            error_type = message.split(':')[0].strip()
            if ' ' in error_type:  # basic check to see if it's really an error type
                error_type = None

        traceback_str = data.get('trace', '')
        file_locations = self._extract_locations(traceback_str)

        return ErrorEvent(
            timestamp=timestamp,
            level=data.get('level', 'ERROR').upper(),
            service=data.get('service', 'unknown'),
            message=message,
            error_type=error_type,
            traceback=traceback_str,
            file_locations=file_locations
        )

    def _parse_logfmt(self, line: str) -> ErrorEvent:
        parts = {}
        # Simple kv extraction
        for kv in re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', line):
            key = kv[0]
            val = kv[1] if kv[1] else kv[2]
            parts[key] = val

        timestamp_str = parts.get('time', '')
        timestamp = self._parse_timestamp(timestamp_str) if timestamp_str else datetime.now(timezone.utc)

        message = parts.get('msg', parts.get('message', ''))
        error_type = None
        if ':' in message:
             error_type = message.split(':')[0].strip()
             if ' ' in error_type:
                error_type = None
        elif message and ' ' not in message:
            # If the entire message is a single word, it might be the error type itself
            error_type = message

        return ErrorEvent(
            timestamp=timestamp,
            level=parts.get('level', 'ERROR').upper(),
            service=parts.get('service', 'unknown'),
            message=message,
            error_type=error_type,
            traceback=None,
            file_locations=[]
        )

    def _parse_plain_text(self, groups: dict, raw_line: str) -> ErrorEvent:
        timestamp = self._parse_timestamp(groups['timestamp'])

        message = groups['message']
        error_type = groups.get('error_type')

        if not error_type and ':' in message:
            error_type = message.split(':')[0].strip()
            if ' ' in error_type:
                error_type = None

        return ErrorEvent(
            timestamp=timestamp,
            level=groups['level'].upper(),
            service=groups['service'],
            message=message,
            error_type=error_type,
            traceback=None,
            file_locations=[]
        )

    def _extract_locations(self, traceback_str: str) -> list[dict]:
        locations = []
        if not traceback_str:
            return locations

        for match in self.traceback_regex.finditer(traceback_str):
            locations.append({
                'file': match.group('file'),
                'line': int(match.group('line'))
            })
        return locations

    def parse_file(self, filepath: str) -> list[ErrorEvent]:
        events = []
        with open(filepath, 'r') as f:
            for line in f:
                event = self.parse_line(line)
                if event:
                    events.append(event)
        return events
