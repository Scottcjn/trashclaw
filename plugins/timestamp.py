"""
Timestamp Plugin for TrashClaw

Convert between Unix timestamps and human-readable dates. Show current time.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str
"""

import time
from datetime import datetime, timezone

TOOL_DEF = {
    "name": "timestamp",
    "description": "Convert between Unix timestamps and human-readable dates, or show current time.",
    "parameters": {
        "type": "object",
        "properties": {
            "unix": {
                "type": "number",
                "description": "Unix timestamp (seconds) to convert to human date"
            },
            "date": {
                "type": "string",
                "description": "Human date string (ISO 8601, e.g. '2026-03-25T12:00:00') to convert to Unix"
            },
            "now": {
                "type": "boolean",
                "description": "If true, show current time in multiple formats"
            }
        },
        "required": []
    }
}


def run(unix: float = None, date: str = "", now: bool = False, **kwargs) -> str:
    results = []

    if now or (unix is None and not date):
        ts = time.time()
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        local_dt = datetime.fromtimestamp(ts)
        results.append(
            f"Current Time:\n"
            f"  Unix:  {int(ts)}\n"
            f"  UTC:   {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"  Local: {local_dt.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    if unix is not None:
        try:
            dt_utc = datetime.fromtimestamp(float(unix), tz=timezone.utc)
            dt_local = datetime.fromtimestamp(float(unix))
            results.append(
                f"Unix {int(unix)} =\n"
                f"  UTC:   {dt_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                f"  Local: {dt_local.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"  ISO:   {dt_utc.isoformat()}"
            )
        except (ValueError, OSError, OverflowError) as e:
            results.append(f"Error converting unix timestamp: {e}")

    if date:
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]
        parsed = None
        for fmt in formats:
            try:
                parsed = datetime.strptime(date.strip(), fmt)
                break
            except ValueError:
                continue

        if parsed:
            ts = int(parsed.timestamp())
            results.append(
                f"'{date}' =\n"
                f"  Unix:    {ts}\n"
                f"  Parsed:  {parsed.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"  ISO:     {parsed.isoformat()}"
            )
        else:
            results.append(
                f"Error: could not parse '{date}'. "
                f"Supported formats: ISO 8601, YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY"
            )

    return "\n\n".join(results) if results else "Error: provide 'unix', 'date', or set 'now' to true."
