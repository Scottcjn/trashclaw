import sys
from pathlib import Path
import json

# Ensure the repository root is on sys.path so trashclaw can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trashclaw import tool_word_count, tool_json_format, tool_timestamp

def test_tool_word_count_basic():
    # Test typical paragraph
    text = "Hello world.\nThis is a test."
    resp = tool_word_count(text)
    data = json.loads(resp)
    assert data["lines"] == 2
    assert data["words"] == 6
    assert data["chars"] == 28

def test_tool_json_format_valid():
    # Test valid messy json
    raw = '{"name":"test",  "value"  : 123}'
    formatted = tool_json_format(raw)
    assert '{\n  "name": "test",\n  "value": 123\n}' in formatted

def test_tool_json_format_invalid():
    # Test invalid json
    raw = '{"name": "test", "value": }'
    formatted = tool_json_format(raw)
    assert "Error formatting JSON" in formatted

def test_tool_timestamp_from_ts():
    # Test conversion from timestamp to string
    ts = 1672531200 # 2023-01-01 00:00:00 UTC
    res = tool_timestamp(ts=ts)
    assert res == "2023-01-01 00:00:00 UTC"

def test_tool_timestamp_from_date():
    # Test conversion from date string to timestamp
    res = tool_timestamp(date="2023-01-01 00:00:00")
    assert res == "1672531200"
