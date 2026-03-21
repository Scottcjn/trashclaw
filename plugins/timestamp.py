"""
Timestamp converter for TrashClaw
"""

import datetime

TOOL_DEF = {
    "name": "timestamp",
    "description": "Convert between Unix timestamps and human-readable dates.",
    "parameters": {
        "type": "object",
        "properties": {
            "value": {
                "type": "string",
                "description": "The value to convert (either a unix timestamp like '1609459200' or an ISO date like '2021-01-01T00:00:00')"
            }
        },
        "required": ["value"]
    }
}

def run(value: str = "", **kwargs) -> str:
    if not value:
        now = datetime.datetime.now(datetime.timezone.utc)
        return f"Current time:\nTimestamp: {now.timestamp()}\nISO Date: {now.isoformat()}"
    
    value = value.strip()
    # Try parsing as timestamp (float or int)
    try:
        ts = float(value)
        dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
        return f"Input Timestamp: {ts}\nISO Date: {dt.isoformat()}"
    except ValueError:
        # Try parsing as datetime
        try:
            # simple fromisoformat
            dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
            return f"Input Date: {dt.isoformat()}\nTimestamp: {dt.timestamp()}"
        except Exception as e:
            return f"Error: Could not parse '{value}' as timestamp or ISO date format ({e})"
