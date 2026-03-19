import urllib.request
import urllib.parse

TOOL_DEF = {
    "name": "get_weather",
    "description": "Get the real current weather for a specific location using wttr.in.",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name, e.g., San Francisco, CA"
            }
        },
        "required": ["location"]
    }
}

def execute(args):
    location = args.get("location", "")
    if not location:
        return "Error: Please provide a location."
    
    try:
        # Fetch weather data from wttr.in (format=3 gives a nice short format)
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=3"
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
        with urllib.request.urlopen(req) as response:
            weather = response.read().decode('utf-8').strip()
        return weather if weather else f"No weather data found for {location}."
    except Exception as e:
        return f"Could not fetch weather data: {str(e)}"
