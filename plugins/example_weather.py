import urllib.request
import urllib.parse

TOOL_DEF = {
    "name": "get_weather",
    "description": "Get the current weather for a specific location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name, e.g. San Francisco",
            }
        },
        "required": ["location"],
    },
}

def execute(kwargs):
    location = kwargs.get("location", "")
    if not location:
        return "Please provide a location."
    try:
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=%l:+%C+%t,+wind+%w,+humidity+%h"
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
        with urllib.request.urlopen(req) as response:
            weather = response.read().decode('utf-8').strip()
        return weather
    except Exception as e:
        return f"Error fetching weather: {e}"
