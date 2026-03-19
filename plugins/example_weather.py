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
                "description": "The city and state, e.g. San Francisco, CA or London"
            }
        },
        "required": ["location"]
    }
}

def execute(kwargs):
    location = kwargs.get("location", "")
    if not location:
        return "Please provide a valid location."
    
    try:
        # Using wttr.in to get simple text-based weather forecast
        url = "https://wttr.in/{}?format=3".format(urllib.parse.quote(location))
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
        with urllib.request.urlopen(req) as response:
            weather = response.read().decode('utf-8').strip()
        return weather if weather else "Could not retrieve weather data."
    except Exception as e:
        return f"Error fetching weather: {e}"
