"""
TrashClaw Plugin — Timer

Measure elapsed time for operations. Start, check, and stop timers
to benchmark how long tasks take.
"""

import time
import json

# Simple in-memory timer storage
_timers = {}

TOOL_DEF = {
    "name": "timer",
    "description": "Start, check, or stop a named timer. Useful for benchmarking operations, measuring how long tasks take, or setting reminders.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Action: 'start', 'check', 'stop', or 'list'"
            },
            "name": {
                "type": "string",
                "description": "Timer name (default: 'default')"
            }
        },
        "required": ["action"]
    }
}


def run(action: str = "start", name: str = "default", **kwargs) -> str:
    """Manage named timers for benchmarking."""
    try:
        if action == "start":
            _timers[name] = time.time()
            return f"Timer '{name}' started."

        elif action == "check":
            if name not in _timers:
                return f"Timer '{name}' not found. Start it first."
            elapsed = time.time() - _timers[name]
            return f"Timer '{name}': {elapsed:.2f}s elapsed (still running)"

        elif action == "stop":
            if name not in _timers:
                return f"Timer '{name}' not found. Start it first."
            elapsed = time.time() - _timers.pop(name)
            if elapsed < 60:
                return f"Timer '{name}' stopped: {elapsed:.2f} seconds"
            elif elapsed < 3600:
                return f"Timer '{name}' stopped: {elapsed / 60:.1f} minutes ({elapsed:.1f}s)"
            else:
                return f"Timer '{name}' stopped: {elapsed / 3600:.1f} hours ({elapsed:.0f}s)"

        elif action == "list":
            if not _timers:
                return "No active timers."
            now = time.time()
            lines = []
            for n, t in _timers.items():
                elapsed = now - t
                lines.append(f"  {n}: {elapsed:.1f}s running")
            return "Active timers:\n" + "\n".join(lines)

        else:
            return f"Unknown action '{action}'. Use: start, check, stop, list"
    except Exception as e:
        return f"Timer error: {e}"
