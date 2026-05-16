
from errormentor.log_parser import LogParser


def test_parse_json():
    parser = LogParser()
    line = '{"timestamp": "2026-05-15T14:32:01Z", "level": "ERROR", "service": "auth", "message": "AuthTokenError: Token expired", "trace": "File \\"auth/validators.py\\", line 147"}'
    event = parser.parse_line(line)

    assert event is not None
    assert event.timestamp.year == 2026
    assert event.level == "ERROR"
    assert event.service == "auth"
    assert event.error_type == "AuthTokenError"
    assert event.file_locations == [{'file': 'auth/validators.py', 'line': 147}]

def test_parse_logfmt():
    parser = LogParser()
    line = 'time=2026-05-15T14:32:01Z level=error service=auth msg="AuthTokenError"'
    event = parser.parse_line(line)

    assert event is not None
    assert event.level == "ERROR"
    assert event.error_type == "AuthTokenError"

def test_parse_plain_text():
    parser = LogParser()
    line = '2026-05-15T14:32:01Z [ERROR] auth_service  AuthTokenError: Token expired'
    event = parser.parse_line(line)

    assert event is not None
    assert event.level == "ERROR"
    assert event.service == "auth_service"
    assert event.error_type == "AuthTokenError"
