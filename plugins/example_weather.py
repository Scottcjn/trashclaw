"""
Example TrashClaw Plugin — Weather Lookup

Drop this file in ~/.trashclaw/plugins/ to add a weather tool.
Demonstrates the plugin API. Modify or use as a template.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import urllib.request
import json

TOOL_DEF = {
    "name": "weather",
    "description": "Get current weather for a city using wttr.in (no API key needed).",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City name (e.g. 'London', 'New York', 'Tokyo')"
            }
        },
        "required": ["city"]
    }
}


def run(city: str = "London", **kwargs) -> str:
    """Fetch weather from wttr.in — free, no auth, returns plain text."""
    try:
        url = f"https://wttr.in/{city.replace(' ', '+')}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "TrashClaw"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception as e:
        return f"Weather lookup failed: {e}"
